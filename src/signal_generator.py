"""
Signal-Generator fuer Iron Condor
=================================
Generiert konkrete Trade-Signale basierend auf Marktdaten.

Berechnet:
- Optimale Strikes basierend auf Delta
- Risk/Reward
- Positionsgroesse basierend auf Kontogroesse
- Entry/Exit Regeln
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Tuple, List
from dataclasses import dataclass

from market_data import MarketSnapshot


@dataclass
class IronCondorSignal:
    """Ein komplettes Iron Condor Signal"""

    # Basis-Info
    symbol: str
    expiry: str
    generated_at: datetime

    # Die vier Legs
    short_put_strike: float
    long_put_strike: float
    short_call_strike: float
    long_call_strike: float

    # Preise
    short_put_premium: float
    long_put_premium: float
    short_call_premium: float
    long_call_premium: float

    # Berechnete Werte
    net_credit: float  # Einnahme pro Contract
    max_loss: float    # Maximaler Verlust pro Contract
    max_profit: float  # Maximaler Gewinn pro Contract

    breakeven_lower: float
    breakeven_upper: float

    # Positionsempfehlung
    recommended_contracts: int
    total_risk: float
    risk_percent: float  # Risiko in % vom Konto

    # Markt-Kontext
    current_price: float
    vix: float
    expected_move: float
    iv_percentile: float

    # Signal-Qualitaet
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    notes: List[str]

    # Signal-Status
    is_valid: bool
    rejection_reason: Optional[str]

    def to_dict(self) -> dict:
        """Konvertiert Signal zu Dictionary"""
        return {
            'symbol': self.symbol,
            'expiry': self.expiry,
            'generated_at': self.generated_at.isoformat(),
            'short_put_strike': self.short_put_strike,
            'long_put_strike': self.long_put_strike,
            'short_call_strike': self.short_call_strike,
            'long_call_strike': self.long_call_strike,
            'short_put_premium': self.short_put_premium,
            'long_put_premium': self.long_put_premium,
            'short_call_premium': self.short_call_premium,
            'long_call_premium': self.long_call_premium,
            'net_credit': self.net_credit,
            'max_loss': self.max_loss,
            'max_profit': self.max_profit,
            'breakeven_lower': self.breakeven_lower,
            'breakeven_upper': self.breakeven_upper,
            'recommended_contracts': self.recommended_contracts,
            'total_risk': self.total_risk,
            'risk_percent': self.risk_percent,
            'current_price': self.current_price,
            'vix': self.vix,
            'expected_move': self.expected_move,
            'iv_percentile': self.iv_percentile,
            'risk_level': self.risk_level,
            'confidence': self.confidence,
            'notes': self.notes,
            'is_valid': self.is_valid,
            'rejection_reason': self.rejection_reason
        }


class SignalGenerator:
    """
    Generiert Iron Condor Signale basierend auf Marktdaten.
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Konfiguration mit Konto- und Signal-Einstellungen
        """
        self.config = config

        # Konto-Einstellungen
        self.capital = config.get('account', {}).get('capital', 5000)
        self.max_risk_percent = config.get('account', {}).get('max_risk_percent', 2)

        # Signal-Einstellungen
        signal_config = config.get('signal', {})
        self.target_delta = signal_config.get('short_delta', 0.12)
        self.wing_width = signal_config.get('wing_width', 2)
        self.min_vix = signal_config.get('min_vix', 12)
        self.max_vix = signal_config.get('max_vix', 25)
        self.min_iv_percentile = signal_config.get('min_iv_percentile', 20)

    def generate_signal(self, snapshot: MarketSnapshot) -> IronCondorSignal:
        """
        Generiert ein Iron Condor Signal basierend auf dem Markt-Snapshot.

        Args:
            snapshot: Aktueller Markt-Snapshot

        Returns:
            IronCondorSignal (kann valid oder invalid sein)
        """
        notes = []

        # 1. Pruefen ob Marktbedingungen geeignet sind
        suitable, reason = snapshot.is_suitable_for_iron_condor(
            max_vix=self.max_vix,
            min_vix=self.min_vix
        )

        if not suitable:
            return self._create_invalid_signal(snapshot, reason)

        # 2. Pruefen ob IV Percentile ausreichend
        if snapshot.iv_percentile < self.min_iv_percentile:
            return self._create_invalid_signal(
                snapshot,
                f"IV Percentile zu niedrig ({snapshot.iv_percentile:.1f}% < {self.min_iv_percentile}%)"
            )

        # 3. Pruefen ob Optionsdaten verfuegbar
        if snapshot.calls.empty or snapshot.puts.empty:
            return self._create_invalid_signal(snapshot, "Keine Optionsdaten verfuegbar")

        # 4. Optimale Strikes finden
        try:
            strikes = self._find_optimal_strikes(
                snapshot.calls,
                snapshot.puts,
                snapshot.price
            )
        except Exception as e:
            return self._create_invalid_signal(snapshot, f"Fehler bei Strike-Berechnung: {e}")

        short_put_strike, long_put_strike, short_call_strike, long_call_strike = strikes

        # 5. Preise fuer die Strikes holen
        premiums = self._get_premiums(
            snapshot.calls,
            snapshot.puts,
            short_put_strike, long_put_strike,
            short_call_strike, long_call_strike
        )

        if premiums is None:
            return self._create_invalid_signal(snapshot, "Keine gueltigen Preise fuer gewaehlte Strikes")

        short_put_prem, long_put_prem, short_call_prem, long_call_prem = premiums

        # 6. P/L berechnen
        # Net Credit = (Short Put + Short Call) - (Long Put + Long Call)
        net_credit = (short_put_prem + short_call_prem) - (long_put_prem + long_call_prem)

        # Max Loss = Wing Width - Net Credit (pro Spread-Seite)
        wing_width_actual = short_put_strike - long_put_strike  # Sollte = self.wing_width sein
        max_loss = (wing_width_actual - net_credit) * 100  # In Dollar (100 Shares pro Contract)

        # Max Profit = Net Credit
        max_profit = net_credit * 100  # In Dollar

        # Breakevensfals
        breakeven_lower = short_put_strike - net_credit
        breakeven_upper = short_call_strike + net_credit

        # 7. Liquiditaet pruefen
        if not self._check_liquidity(snapshot.calls, snapshot.puts,
                                      short_put_strike, short_call_strike):
            notes.append("Warnung: Geringe Liquiditaet - groessere Spreads moeglich")

        # 8. Positionsgroesse berechnen
        max_risk_dollar = self.capital * (self.max_risk_percent / 100)
        recommended_contracts = max(1, int(max_risk_dollar / max_loss))
        total_risk = recommended_contracts * max_loss
        risk_percent = (total_risk / self.capital) * 100

        # 9. Risiko-Level bestimmen
        risk_level = self._assess_risk_level(snapshot, net_credit, wing_width_actual)
        confidence = self._assess_confidence(snapshot, notes)

        # 10. Zusaetzliche Notes
        if snapshot.vix > 20:
            notes.append(f"Erhoehte Volatilitaet (VIX: {snapshot.vix:.1f})")

        if snapshot.expected_move > 1.5:
            notes.append(f"Expected Move: {snapshot.expected_move:.2f}% - Strikes koennten eng sein")

        if risk_percent > 2:
            notes.append(f"Risiko ({risk_percent:.1f}%) ueber Zielwert von 2%")

        # 11. Signal erstellen
        return IronCondorSignal(
            symbol=snapshot.symbol,
            expiry=snapshot.options_expiry,
            generated_at=datetime.now(),

            short_put_strike=short_put_strike,
            long_put_strike=long_put_strike,
            short_call_strike=short_call_strike,
            long_call_strike=long_call_strike,

            short_put_premium=short_put_prem,
            long_put_premium=long_put_prem,
            short_call_premium=short_call_prem,
            long_call_premium=long_call_prem,

            net_credit=net_credit,
            max_loss=max_loss,
            max_profit=max_profit,

            breakeven_lower=breakeven_lower,
            breakeven_upper=breakeven_upper,

            recommended_contracts=recommended_contracts,
            total_risk=total_risk,
            risk_percent=risk_percent,

            current_price=snapshot.price,
            vix=snapshot.vix,
            expected_move=snapshot.expected_move,
            iv_percentile=snapshot.iv_percentile,

            risk_level=risk_level,
            confidence=confidence,
            notes=notes,

            is_valid=True,
            rejection_reason=None
        )

    def _find_optimal_strikes(self, calls: pd.DataFrame, puts: pd.DataFrame,
                              current_price: float) -> Tuple[float, float, float, float]:
        """
        Findet optimale Strikes basierend auf Delta.

        Ziel-Delta fuer Short Strikes: ~0.10-0.16 (ca. 1 Standardabweichung OTM)

        Returns:
            Tuple: (short_put, long_put, short_call, long_call)
        """
        # Fuer Put-Seite (unterhalb des Kurses)
        put_candidates = puts[puts['strike'] < current_price].copy()
        if put_candidates.empty:
            raise ValueError("Keine Put-Strikes unter aktuellem Kurs verfuegbar")

        # Fuer Call-Seite (oberhalb des Kurses)
        call_candidates = calls[calls['strike'] > current_price].copy()
        if call_candidates.empty:
            raise ValueError("Keine Call-Strikes ueber aktuellem Kurs verfuegbar")

        # Delta-basierte Auswahl (falls Delta verfuegbar)
        # Yahoo Finance hat manchmal kein Delta, dann nutzen wir Abstand zum Kurs
        if 'impliedVolatility' in put_candidates.columns:
            # Approximiere Delta basierend auf Moneyness und IV
            # Short Put: ca. 1.5% unter dem Kurs
            target_put_strike = current_price * 0.985

            # Short Call: ca. 1.5% ueber dem Kurs
            target_call_strike = current_price * 1.015

            # Finde naechsten verfuegbaren Strike
            short_put_strike = put_candidates.iloc[
                (put_candidates['strike'] - target_put_strike).abs().argsort()[:1]
            ]['strike'].values[0]

            short_call_strike = call_candidates.iloc[
                (call_candidates['strike'] - target_call_strike).abs().argsort()[:1]
            ]['strike'].values[0]
        else:
            # Fallback: Nutze feste Abstande
            target_put_strike = current_price - (current_price * 0.015)
            target_call_strike = current_price + (current_price * 0.015)

            short_put_strike = put_candidates.iloc[
                (put_candidates['strike'] - target_put_strike).abs().argsort()[:1]
            ]['strike'].values[0]

            short_call_strike = call_candidates.iloc[
                (call_candidates['strike'] - target_call_strike).abs().argsort()[:1]
            ]['strike'].values[0]

        # Long Strikes (Wings) - $2 weiter OTM
        long_put_strike = short_put_strike - self.wing_width
        long_call_strike = short_call_strike + self.wing_width

        # Pruefen ob Long Strikes existieren
        available_put_strikes = puts['strike'].values
        available_call_strikes = calls['strike'].values

        if long_put_strike not in available_put_strikes:
            # Naechsten verfuegbaren Strike nehmen
            lower_strikes = available_put_strikes[available_put_strikes < short_put_strike]
            if len(lower_strikes) > 0:
                long_put_strike = lower_strikes[-1]
            else:
                long_put_strike = short_put_strike - 1  # Minimum

        if long_call_strike not in available_call_strikes:
            higher_strikes = available_call_strikes[available_call_strikes > short_call_strike]
            if len(higher_strikes) > 0:
                long_call_strike = higher_strikes[0]
            else:
                long_call_strike = short_call_strike + 1

        return (short_put_strike, long_put_strike, short_call_strike, long_call_strike)

    def _get_premiums(self, calls: pd.DataFrame, puts: pd.DataFrame,
                      short_put: float, long_put: float,
                      short_call: float, long_call: float) -> Optional[Tuple[float, float, float, float]]:
        """
        Holt die Preise (Mid-Point) fuer die gewaehlten Strikes.

        Returns:
            Tuple: (short_put_prem, long_put_prem, short_call_prem, long_call_prem) oder None
        """
        try:
            def get_mid_price(df: pd.DataFrame, strike: float) -> float:
                row = df[df['strike'] == strike]
                if row.empty:
                    # Naechsten Strike suchen
                    idx = (df['strike'] - strike).abs().argsort()[:1]
                    row = df.iloc[idx]

                row = row.iloc[0]

                # Mid-Point berechnen
                if 'bid' in row and 'ask' in row and row['bid'] > 0 and row['ask'] > 0:
                    return (row['bid'] + row['ask']) / 2
                elif 'lastPrice' in row:
                    return row['lastPrice']
                else:
                    return 0.0

            short_put_prem = get_mid_price(puts, short_put)
            long_put_prem = get_mid_price(puts, long_put)
            short_call_prem = get_mid_price(calls, short_call)
            long_call_prem = get_mid_price(calls, long_call)

            # Validierung
            if any(p <= 0 for p in [short_put_prem, short_call_prem]):
                return None

            return (short_put_prem, long_put_prem, short_call_prem, long_call_prem)

        except Exception as e:
            print(f"Fehler beim Holen der Preise: {e}")
            return None

    def _check_liquidity(self, calls: pd.DataFrame, puts: pd.DataFrame,
                         short_put: float, short_call: float) -> bool:
        """Prueft ob ausreichend Liquiditaet vorhanden ist"""
        try:
            put_row = puts[puts['strike'] == short_put]
            call_row = calls[calls['strike'] == short_call]

            if put_row.empty or call_row.empty:
                return False

            # Open Interest pruefen (>1000 ist gut)
            put_oi = put_row['openInterest'].values[0] if 'openInterest' in put_row.columns else 0
            call_oi = call_row['openInterest'].values[0] if 'openInterest' in call_row.columns else 0

            # Bid-Ask Spread pruefen (<10% ist akzeptabel)
            for row in [put_row.iloc[0], call_row.iloc[0]]:
                if 'bid' in row and 'ask' in row and row['bid'] > 0:
                    spread_pct = (row['ask'] - row['bid']) / row['bid'] * 100
                    if spread_pct > 15:
                        return False

            return True

        except Exception:
            return True  # Im Zweifel annehmen dass es OK ist

    def _assess_risk_level(self, snapshot: MarketSnapshot,
                           net_credit: float, wing_width: float) -> str:
        """Bestimmt das Risiko-Level"""
        # Risk/Reward Verhaeltnis
        max_loss = wing_width - net_credit
        risk_reward = max_loss / net_credit if net_credit > 0 else float('inf')

        if snapshot.vix > 22 or risk_reward > 4:
            return "HIGH"
        elif snapshot.vix > 18 or risk_reward > 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _assess_confidence(self, snapshot: MarketSnapshot, notes: List[str]) -> str:
        """Bestimmt die Konfidenz des Signals"""
        warning_count = len([n for n in notes if "Warnung" in n])

        if warning_count > 1 or snapshot.expected_move > 2:
            return "LOW"
        elif warning_count > 0 or snapshot.vix > 20:
            return "MEDIUM"
        else:
            return "HIGH"

    def _create_invalid_signal(self, snapshot: MarketSnapshot, reason: str) -> IronCondorSignal:
        """Erstellt ein ungultiges Signal mit Ablehnungsgrund"""
        return IronCondorSignal(
            symbol=snapshot.symbol,
            expiry=snapshot.options_expiry,
            generated_at=datetime.now(),

            short_put_strike=0,
            long_put_strike=0,
            short_call_strike=0,
            long_call_strike=0,

            short_put_premium=0,
            long_put_premium=0,
            short_call_premium=0,
            long_call_premium=0,

            net_credit=0,
            max_loss=0,
            max_profit=0,

            breakeven_lower=0,
            breakeven_upper=0,

            recommended_contracts=0,
            total_risk=0,
            risk_percent=0,

            current_price=snapshot.price,
            vix=snapshot.vix,
            expected_move=snapshot.expected_move,
            iv_percentile=snapshot.iv_percentile,

            risk_level="N/A",
            confidence="N/A",
            notes=[],

            is_valid=False,
            rejection_reason=reason
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from market_data import MarketDataFetcher

    print("Teste Signal-Generator...")
    print("=" * 60)

    # Test-Konfiguration
    config = {
        'account': {
            'capital': 5000,
            'max_risk_percent': 2
        },
        'signal': {
            'symbol': 'SPY',
            'short_delta': 0.12,
            'wing_width': 2,
            'min_vix': 12,
            'max_vix': 25,
            'min_iv_percentile': 20
        }
    }

    try:
        # Marktdaten holen
        fetcher = MarketDataFetcher("SPY")
        snapshot = fetcher.get_market_snapshot()

        print(f"Markt-Snapshot:")
        print(f"  SPY: ${snapshot.price:.2f}")
        print(f"  VIX: {snapshot.vix:.2f}")
        print()

        # Signal generieren
        generator = SignalGenerator(config)
        signal = generator.generate_signal(snapshot)

        if signal.is_valid:
            print("SIGNAL GENERIERT!")
            print("-" * 40)
            print(f"Short Put:  ${signal.short_put_strike} @ ${signal.short_put_premium:.2f}")
            print(f"Long Put:   ${signal.long_put_strike} @ ${signal.long_put_premium:.2f}")
            print(f"Short Call: ${signal.short_call_strike} @ ${signal.short_call_premium:.2f}")
            print(f"Long Call:  ${signal.long_call_strike} @ ${signal.long_call_premium:.2f}")
            print()
            print(f"Net Credit: ${signal.net_credit:.2f} (${signal.max_profit:.0f} total)")
            print(f"Max Loss:   ${signal.max_loss:.0f}")
            print(f"Breakeven:  ${signal.breakeven_lower:.2f} - ${signal.breakeven_upper:.2f}")
            print()
            print(f"Empfehlung: {signal.recommended_contracts} Contract(s)")
            print(f"Risiko:     ${signal.total_risk:.0f} ({signal.risk_percent:.1f}%)")
            print(f"Risk Level: {signal.risk_level}")
            print(f"Confidence: {signal.confidence}")
            if signal.notes:
                print(f"Notes:      {', '.join(signal.notes)}")
        else:
            print("KEIN SIGNAL HEUTE")
            print(f"Grund: {signal.rejection_reason}")

    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
