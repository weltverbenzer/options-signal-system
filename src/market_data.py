"""
Marktdaten-Modul
================
Ruft Marktdaten von Yahoo Finance ab:
- Aktueller SPY-Kurs
- VIX (Volatilitaetsindex)
- Optionskette mit Greeks
- Wirtschaftskalender-Check
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import requests
from dataclasses import dataclass


@dataclass
class MarketSnapshot:
    """Snapshot der aktuellen Marktlage"""
    symbol: str
    price: float
    vix: float
    timestamp: datetime

    # Optionsketten-Daten
    options_expiry: str
    calls: pd.DataFrame
    puts: pd.DataFrame

    # Berechnete Werte
    iv_percentile: float
    expected_move: float

    # Marktbedingungen
    has_earnings_today: bool
    has_fed_event: bool
    has_economic_data: bool
    is_trading_day: bool

    def is_suitable_for_iron_condor(self, max_vix: float = 25, min_vix: float = 12) -> Tuple[bool, str]:
        """
        Prueft ob die Marktbedingungen fuer einen Iron Condor geeignet sind.

        Returns:
            Tuple[bool, str]: (geeignet, Grund falls nicht geeignet)
        """
        # HINWEIS: Wir generieren auch am Wochenende Signale fuer den naechsten Handelstag!
        # Die is_trading_day Pruefung wurde entfernt.

        if self.vix > max_vix:
            return False, f"VIX zu hoch ({self.vix:.1f} > {max_vix})"

        if self.vix < min_vix:
            return False, f"VIX zu niedrig ({self.vix:.1f} < {min_vix}) - zu wenig Premium"

        if self.has_earnings_today:
            return False, "SPY/SPX Earnings-bezogene Volatilitaet erwartet"

        if self.has_fed_event:
            return False, "Fed-Entscheidung heute - erhoehte Volatilitaet erwartet"

        if self.has_economic_data:
            return False, "Wichtige Wirtschaftsdaten heute (CPI, Jobs, etc.)"

        return True, "Bedingungen erfuellt"


class MarketDataFetcher:
    """Holt Marktdaten von Yahoo Finance"""

    def __init__(self, symbol: str = "SPY"):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.vix_ticker = yf.Ticker("^VIX")

    def get_current_price(self) -> float:
        """Aktueller Kurs des Symbols"""
        data = self.ticker.history(period="1d")
        if data.empty:
            raise ValueError(f"Keine Kursdaten fuer {self.symbol} verfuegbar")
        return float(data['Close'].iloc[-1])

    def get_vix(self) -> float:
        """Aktueller VIX-Wert"""
        data = self.vix_ticker.history(period="1d")
        if data.empty:
            raise ValueError("Keine VIX-Daten verfuegbar")
        return float(data['Close'].iloc[-1])

    def get_iv_percentile(self, lookback_days: int = 252) -> float:
        """
        Berechnet IV Percentile basierend auf historischer Volatilitaet.

        Args:
            lookback_days: Anzahl Tage fuer historischen Vergleich (252 = 1 Jahr)

        Returns:
            IV Percentile (0-100)
        """
        vix_history = self.vix_ticker.history(period="1y")
        if vix_history.empty or len(vix_history) < 20:
            return 50.0  # Default wenn keine Daten

        current_vix = vix_history['Close'].iloc[-1]
        historical_vix = vix_history['Close'].values

        # Percentile: Wie viel % der historischen Werte sind niedriger
        percentile = (historical_vix < current_vix).sum() / len(historical_vix) * 100
        return float(percentile)

    def get_0dte_expiry(self) -> Optional[str]:
        """
        Findet das naechste 0DTE Verfallsdatum.
        SPY hat taeglich Optionen (Mo-Fr).

        Returns:
            Verfallsdatum im Format 'YYYY-MM-DD' oder None
        """
        try:
            expirations = self.ticker.options
            if not expirations:
                return None

            today = datetime.now().strftime('%Y-%m-%d')

            # Suche heutiges Datum in Verfallsdaten
            for exp in expirations:
                if exp == today:
                    return exp

            # Falls kein exaktes Match, nimm naechstes Datum
            for exp in expirations:
                if exp >= today:
                    return exp

            return expirations[0] if expirations else None

        except Exception as e:
            print(f"Fehler beim Abrufen der Verfallsdaten: {e}")
            return None

    def get_option_chain(self, expiry: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Holt die Optionskette fuer ein bestimmtes Verfallsdatum.

        Args:
            expiry: Verfallsdatum im Format 'YYYY-MM-DD'

        Returns:
            Tuple[calls DataFrame, puts DataFrame]
        """
        try:
            chain = self.ticker.option_chain(expiry)
            return chain.calls, chain.puts
        except Exception as e:
            print(f"Fehler beim Abrufen der Optionskette: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def calculate_expected_move(self, calls: pd.DataFrame, puts: pd.DataFrame,
                                current_price: float) -> float:
        """
        Berechnet den Expected Move basierend auf ATM Straddle-Preis.

        Der Expected Move zeigt, wie viel Bewegung der Markt erwartet.

        Args:
            calls: Calls DataFrame
            puts: Puts DataFrame
            current_price: Aktueller Kurs

        Returns:
            Expected Move in Prozent
        """
        if calls.empty or puts.empty:
            return 0.0

        # Finde ATM Strikes (naechster Strike zum aktuellen Kurs)
        try:
            call_strikes = calls['strike'].values
            put_strikes = puts['strike'].values

            atm_call_idx = np.abs(call_strikes - current_price).argmin()
            atm_put_idx = np.abs(put_strikes - current_price).argmin()

            # Hole Bid/Ask Midpoint fuer ATM Optionen
            atm_call = calls.iloc[atm_call_idx]
            atm_put = puts.iloc[atm_put_idx]

            call_mid = (atm_call['bid'] + atm_call['ask']) / 2 if 'bid' in atm_call and 'ask' in atm_call else atm_call.get('lastPrice', 0)
            put_mid = (atm_put['bid'] + atm_put['ask']) / 2 if 'bid' in atm_put and 'ask' in atm_put else atm_put.get('lastPrice', 0)

            # Straddle-Preis = Call + Put
            straddle_price = call_mid + put_mid

            # Expected Move in Prozent
            expected_move_pct = (straddle_price / current_price) * 100

            return float(expected_move_pct)

        except Exception as e:
            print(f"Fehler bei Expected Move Berechnung: {e}")
            return 0.0

    def check_economic_events(self) -> Dict[str, bool]:
        """
        Prueft auf wichtige Wirtschaftsereignisse heute.

        Returns:
            Dict mit Event-Flags
        """
        today = datetime.now()

        # Vereinfachte Pruefung - in Produktion wuerde man einen Kalender-API nutzen
        events = {
            'has_earnings_today': False,  # SPY selbst hat keine Earnings
            'has_fed_event': self._is_fomc_day(today),
            'has_economic_data': self._is_major_data_day(today),
            'is_trading_day': self._is_trading_day(today)
        }

        return events

    def _is_fomc_day(self, date: datetime) -> bool:
        """
        Prueft ob heute ein FOMC-Tag ist.
        FOMC trifft sich ca. 8x pro Jahr, meist Mittwoch.

        In Produktion: API oder Kalender-Daten nutzen
        """
        # 2026 FOMC Termine (approximiert - muesste aktualisiert werden)
        fomc_dates_2026 = [
            "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
            "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16"
        ]

        date_str = date.strftime('%Y-%m-%d')
        return date_str in fomc_dates_2026

    def _is_major_data_day(self, date: datetime) -> bool:
        """
        Prueft ob heute wichtige Wirtschaftsdaten veroeffentlicht werden.

        Wichtige Tage:
        - CPI (Consumer Price Index) - meist 2. Woche des Monats
        - Jobs Report (NFP) - erster Freitag des Monats
        - GDP - Ende des Quartals

        In Produktion: Economic Calendar API nutzen
        """
        # Erster Freitag = Jobs Report
        if date.weekday() == 4:  # Freitag
            if date.day <= 7:  # Erste Woche
                return True

        # CPI meist 10.-15. des Monats
        if 10 <= date.day <= 15:
            # CPI kommt normalerweise an einem Dienstag oder Mittwoch
            if date.weekday() in [1, 2]:  # Dienstag oder Mittwoch
                return True

        return False

    def _is_trading_day(self, date: datetime) -> bool:
        """Prueft ob heute ein Handelstag ist (Mo-Fr, keine Feiertage)"""
        # Wochenende
        if date.weekday() >= 5:
            return False

        # US-Feiertage (vereinfacht)
        us_holidays_2026 = [
            "2026-01-01",  # New Year
            "2026-01-19",  # MLK Day
            "2026-02-16",  # Presidents Day
            "2026-04-03",  # Good Friday
            "2026-05-25",  # Memorial Day
            "2026-07-03",  # Independence Day (observed)
            "2026-09-07",  # Labor Day
            "2026-11-26",  # Thanksgiving
            "2026-12-25",  # Christmas
        ]

        date_str = date.strftime('%Y-%m-%d')
        return date_str not in us_holidays_2026

    def get_market_snapshot(self) -> MarketSnapshot:
        """
        Erstellt einen kompletten Snapshot der aktuellen Marktlage.

        Returns:
            MarketSnapshot mit allen relevanten Daten
        """
        # Basis-Daten
        price = self.get_current_price()
        vix = self.get_vix()
        iv_percentile = self.get_iv_percentile()

        # Optionskette
        expiry = self.get_0dte_expiry()
        if expiry:
            calls, puts = self.get_option_chain(expiry)
            expected_move = self.calculate_expected_move(calls, puts, price)
        else:
            calls, puts = pd.DataFrame(), pd.DataFrame()
            expected_move = 0.0

        # Events
        events = self.check_economic_events()

        return MarketSnapshot(
            symbol=self.symbol,
            price=price,
            vix=vix,
            timestamp=datetime.now(),
            options_expiry=expiry or "",
            calls=calls,
            puts=puts,
            iv_percentile=iv_percentile,
            expected_move=expected_move,
            has_earnings_today=events['has_earnings_today'],
            has_fed_event=events['has_fed_event'],
            has_economic_data=events['has_economic_data'],
            is_trading_day=events['is_trading_day']
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Teste Marktdaten-Modul...")
    print("=" * 60)

    fetcher = MarketDataFetcher("SPY")

    try:
        snapshot = fetcher.get_market_snapshot()

        print(f"Symbol:           {snapshot.symbol}")
        print(f"Kurs:             ${snapshot.price:.2f}")
        print(f"VIX:              {snapshot.vix:.2f}")
        print(f"IV Percentile:    {snapshot.iv_percentile:.1f}%")
        print(f"Expected Move:    {snapshot.expected_move:.2f}%")
        print(f"Options Expiry:   {snapshot.options_expiry}")
        print(f"Calls verfuegbar: {len(snapshot.calls)}")
        print(f"Puts verfuegbar:  {len(snapshot.puts)}")
        print()
        print("Events:")
        print(f"  Earnings heute: {snapshot.has_earnings_today}")
        print(f"  Fed Event:      {snapshot.has_fed_event}")
        print(f"  Wirtschaftsdaten: {snapshot.has_economic_data}")
        print(f"  Handelstag:     {snapshot.is_trading_day}")
        print()

        suitable, reason = snapshot.is_suitable_for_iron_condor()
        print(f"Geeignet fuer Iron Condor: {suitable}")
        print(f"Grund: {reason}")

    except Exception as e:
        print(f"Fehler: {e}")
