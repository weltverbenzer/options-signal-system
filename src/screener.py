"""
Screener-Modul
==============
Durchsucht eine Watchlist nach geeigneten Kandidaten fuer:
- Iron Condor (keine Events, ruhiger Markt)
- Straddle/Strangle (Earnings, Events, erwartete Bewegung)

Liefert Begruendungen fuer jede Empfehlung.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import requests


# Standard-Watchlist: Liquide Aktien und Indizes mit guten Optionsmaerkten
DEFAULT_WATCHLIST = [
    # Indizes/ETFs
    "SPY",   # S&P 500 ETF
    "QQQ",   # Nasdaq 100 ETF
    "IWM",   # Russell 2000 ETF

    # Big Tech
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "GOOGL", # Alphabet
    "AMZN",  # Amazon
    "NVDA",  # Nvidia
    "META",  # Meta
    "TSLA",  # Tesla

    # Weitere liquide Aktien
    "AMD",   # AMD
    "NFLX",  # Netflix
    "JPM",   # JP Morgan
    "BAC",   # Bank of America
    "DIS",   # Disney
    "BA",    # Boeing
    "NKE",   # Nike
    "V",     # Visa
    "MA",    # Mastercard
]


@dataclass
class ScreenerResult:
    """Ergebnis des Screeners fuer ein Symbol"""
    symbol: str
    company_name: str
    current_price: float

    # Strategie-Eignung
    iron_condor_score: float  # 0-100, hoeher = besser geeignet
    straddle_score: float     # 0-100, hoeher = besser geeignet
    recommended_strategy: str  # "IRON_CONDOR", "STRADDLE", "NONE"

    # Begruendung
    reasons: List[str]
    warnings: List[str]

    # Marktdaten
    iv_percentile: float
    expected_move_pct: float
    avg_volume: int

    # Events
    has_earnings_soon: bool
    earnings_date: Optional[str]
    days_to_earnings: Optional[int]

    # Liquiditaet
    options_liquid: bool
    avg_option_volume: int
    bid_ask_spread_pct: float

    # Quellen-Links (fuer Nachpruefbarkeit)
    source_url_quote: str = ""      # Yahoo Finance Quote
    source_url_options: str = ""    # Yahoo Finance Options
    source_url_earnings: str = ""   # Earnings Kalender

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'current_price': self.current_price,
            'iron_condor_score': self.iron_condor_score,
            'straddle_score': self.straddle_score,
            'recommended_strategy': self.recommended_strategy,
            'reasons': self.reasons,
            'warnings': self.warnings,
            'iv_percentile': self.iv_percentile,
            'expected_move_pct': self.expected_move_pct,
            'has_earnings_soon': self.has_earnings_soon,
            'earnings_date': self.earnings_date,
            'days_to_earnings': self.days_to_earnings,
            'options_liquid': self.options_liquid,
            'bid_ask_spread_pct': self.bid_ask_spread_pct,
            'source_url_quote': self.source_url_quote,
            'source_url_options': self.source_url_options,
            'source_url_earnings': self.source_url_earnings
        }


class StockScreener:
    """Screent Aktien fuer Options-Strategien"""

    def __init__(self, watchlist: List[str] = None):
        self.watchlist = watchlist or DEFAULT_WATCHLIST

    def screen_all(self) -> Dict[str, List[ScreenerResult]]:
        """
        Screent alle Symbole in der Watchlist.

        WICHTIG: Jedes Symbol wird NUR EINER Kategorie zugeordnet!
        - Hat Earnings bald? -> Straddle
        - Keine Earnings + niedriger Expected Move? -> Iron Condor

        Returns:
            Dict mit 'iron_condor' und 'straddle' Listen
        """
        results = []

        print(f"Screene {len(self.watchlist)} Symbole...")

        for symbol in self.watchlist:
            try:
                result = self.screen_symbol(symbol)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  Fehler bei {symbol}: {e}")
                continue

        # WICHTIG: Jedes Symbol nur in EINER Kategorie!
        iron_condor_candidates = []
        straddle_candidates = []

        for r in results:
            if not r.options_liquid:
                continue  # Keine illiquiden Optionen

            # Primaere Entscheidung: Earnings?
            if r.has_earnings_soon:
                # Earnings = Straddle Kandidat (NICHT Iron Condor!)
                if r.straddle_score > 40:
                    straddle_candidates.append(r)
            else:
                # Keine Earnings - aber Expected Move pruefen!
                # Iron Condor NUR wenn Expected Move < 2%
                if r.expected_move_pct < 2.0 and r.iron_condor_score > 50:
                    iron_condor_candidates.append(r)
                elif r.expected_move_pct >= 3.0:
                    # Hoher Expected Move OHNE Earnings = auch Straddle moeglich
                    if r.straddle_score > 50:
                        straddle_candidates.append(r)

        # Sortieren und Top 5
        iron_condor_candidates = sorted(
            iron_condor_candidates,
            key=lambda x: x.iron_condor_score,
            reverse=True
        )[:5]

        straddle_candidates = sorted(
            straddle_candidates,
            key=lambda x: x.straddle_score,
            reverse=True
        )[:5]

        return {
            'iron_condor': iron_condor_candidates,
            'straddle': straddle_candidates
        }

    def screen_symbol(self, symbol: str) -> Optional[ScreenerResult]:
        """
        Analysiert ein einzelnes Symbol.

        Returns:
            ScreenerResult oder None bei Fehler
        """
        print(f"  Analysiere {symbol}...")

        ticker = yf.Ticker(symbol)

        # Basis-Infos
        try:
            info = ticker.info
            company_name = info.get('shortName', symbol)
            current_price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
            avg_volume = info.get('averageVolume', 0)
        except:
            return None

        if current_price == 0:
            return None

        # Earnings pruefen
        earnings_info = self._check_earnings(ticker)

        # IV und Expected Move
        iv_info = self._get_iv_info(ticker, current_price)

        # Optionsliquiditaet pruefen
        liquidity_info = self._check_options_liquidity(ticker)

        # Scores berechnen
        iron_condor_score, straddle_score, reasons, warnings = self._calculate_scores(
            earnings_info, iv_info, liquidity_info, avg_volume
        )

        # Empfohlene Strategie
        if iron_condor_score > straddle_score and iron_condor_score > 50:
            recommended = "IRON_CONDOR"
        elif straddle_score > iron_condor_score and straddle_score > 50:
            recommended = "STRADDLE"
        else:
            recommended = "NONE"

        # Quellen-URLs generieren
        source_quote = f"https://finance.yahoo.com/quote/{symbol}"
        source_options = f"https://finance.yahoo.com/quote/{symbol}/options"
        source_earnings = f"https://finance.yahoo.com/quote/{symbol}/analysis"

        return ScreenerResult(
            symbol=symbol,
            company_name=company_name,
            current_price=current_price,
            iron_condor_score=iron_condor_score,
            straddle_score=straddle_score,
            recommended_strategy=recommended,
            reasons=reasons,
            warnings=warnings,
            iv_percentile=iv_info.get('iv_percentile', 0),
            expected_move_pct=iv_info.get('expected_move', 0),
            avg_volume=avg_volume,
            has_earnings_soon=earnings_info.get('has_earnings_soon', False),
            earnings_date=earnings_info.get('earnings_date'),
            days_to_earnings=earnings_info.get('days_to_earnings'),
            options_liquid=liquidity_info.get('is_liquid', False),
            avg_option_volume=liquidity_info.get('avg_volume', 0),
            bid_ask_spread_pct=liquidity_info.get('spread_pct', 0),
            source_url_quote=source_quote,
            source_url_options=source_options,
            source_url_earnings=source_earnings
        )

    def _check_earnings(self, ticker) -> Dict:
        """Prueft Earnings-Termine"""
        result = {
            'has_earnings_soon': False,
            'earnings_date': None,
            'days_to_earnings': None
        }

        try:
            # Earnings-Kalender abrufen
            calendar = ticker.calendar

            if calendar is not None and not calendar.empty:
                # Verschiedene Formate behandeln
                if isinstance(calendar, pd.DataFrame):
                    if 'Earnings Date' in calendar.columns:
                        earnings_date = calendar['Earnings Date'].iloc[0]
                    elif 'earningsDate' in calendar.index:
                        earnings_date = calendar.loc['earningsDate'].iloc[0]
                    else:
                        earnings_date = None
                else:
                    earnings_date = calendar.get('Earnings Date', [None])[0]

                if earnings_date:
                    if isinstance(earnings_date, str):
                        earnings_date = pd.to_datetime(earnings_date)

                    today = datetime.now().date()
                    days_to = (earnings_date.date() - today).days if hasattr(earnings_date, 'date') else 999

                    result['earnings_date'] = str(earnings_date.date()) if hasattr(earnings_date, 'date') else str(earnings_date)
                    result['days_to_earnings'] = days_to
                    result['has_earnings_soon'] = -1 <= days_to <= 3  # Gestern bis in 3 Tagen

        except Exception as e:
            pass

        return result

    def _get_iv_info(self, ticker, current_price: float) -> Dict:
        """Berechnet IV-bezogene Metriken"""
        result = {
            'iv_percentile': 50,
            'expected_move': 0
        }

        try:
            # Optionskette fuer naechstes Verfallsdatum
            expirations = ticker.options
            if not expirations:
                return result

            # Naechstes Verfallsdatum
            expiry = expirations[0]
            chain = ticker.option_chain(expiry)

            if chain.calls.empty or chain.puts.empty:
                return result

            # ATM-Optionen finden
            calls = chain.calls
            puts = chain.puts

            atm_call_idx = (calls['strike'] - current_price).abs().argmin()
            atm_put_idx = (puts['strike'] - current_price).abs().argmin()

            atm_call = calls.iloc[atm_call_idx]
            atm_put = puts.iloc[atm_put_idx]

            # IV aus ATM-Optionen
            call_iv = atm_call.get('impliedVolatility', 0)
            put_iv = atm_put.get('impliedVolatility', 0)
            avg_iv = (call_iv + put_iv) / 2 if call_iv and put_iv else 0

            # Expected Move aus Straddle-Preis
            call_mid = (atm_call.get('bid', 0) + atm_call.get('ask', 0)) / 2
            put_mid = (atm_put.get('bid', 0) + atm_put.get('ask', 0)) / 2
            straddle_price = call_mid + put_mid
            expected_move = (straddle_price / current_price) * 100 if current_price > 0 else 0

            result['expected_move'] = round(expected_move, 2)

            # IV Percentile (vereinfacht - basierend auf VIX-Vergleich)
            if avg_iv > 0:
                # Hoehere IV = hoeherer Percentile
                result['iv_percentile'] = min(100, max(0, avg_iv * 200))

        except Exception as e:
            pass

        return result

    def _check_options_liquidity(self, ticker) -> Dict:
        """Prueft Optionsliquiditaet"""
        result = {
            'is_liquid': False,
            'avg_volume': 0,
            'spread_pct': 100
        }

        try:
            expirations = ticker.options
            if not expirations:
                return result

            chain = ticker.option_chain(expirations[0])

            if chain.calls.empty:
                return result

            # Durchschnittliches Volumen
            avg_volume = chain.calls['volume'].mean() if 'volume' in chain.calls else 0
            avg_oi = chain.calls['openInterest'].mean() if 'openInterest' in chain.calls else 0

            # Bid-Ask Spread bei ATM
            atm_idx = len(chain.calls) // 2
            atm_call = chain.calls.iloc[atm_idx]

            bid = atm_call.get('bid', 0)
            ask = atm_call.get('ask', 0)

            if bid > 0 and ask > 0:
                spread_pct = ((ask - bid) / bid) * 100
            else:
                spread_pct = 100

            result['avg_volume'] = int(avg_volume) if pd.notna(avg_volume) else 0
            result['spread_pct'] = round(spread_pct, 2)

            # Liquid wenn: gutes Volumen UND enger Spread
            result['is_liquid'] = (avg_oi > 100 or avg_volume > 50) and spread_pct < 20

        except Exception as e:
            pass

        return result

    def _calculate_scores(self, earnings: Dict, iv: Dict,
                          liquidity: Dict, avg_volume: int) -> Tuple[float, float, List[str], List[str]]:
        """
        Berechnet Scores fuer Iron Condor und Straddle.

        Returns:
            (iron_condor_score, straddle_score, reasons, warnings)
        """
        ic_score = 50.0  # Basis-Score
        st_score = 50.0
        reasons = []
        warnings = []

        # === EARNINGS-EINFLUSS ===
        if earnings.get('has_earnings_soon'):
            days = earnings.get('days_to_earnings', 999)

            if days == 0:
                # Earnings HEUTE
                st_score += 40
                ic_score -= 40
                reasons.append(f"EARNINGS HEUTE - ideal fuer Straddle")
            elif days == 1:
                # Earnings MORGEN
                st_score += 35
                ic_score -= 35
                reasons.append(f"Earnings morgen - Straddle-Kandidat")
            elif -1 <= days <= 3:
                # Earnings sehr nah
                st_score += 25
                ic_score -= 25
                reasons.append(f"Earnings in {days} Tag(en)")
        else:
            # Keine Earnings = gut fuer Iron Condor
            ic_score += 15
            reasons.append("Keine Earnings in Sicht")

        # === IV-EINFLUSS ===
        iv_pct = iv.get('iv_percentile', 50)
        expected_move = iv.get('expected_move', 0)

        # IV Einfluss
        if iv_pct > 70:
            # Hohe IV: Gut fuer Premium-Verkauf, aber auch riskanter
            if expected_move < 2:
                ic_score += 10
                reasons.append(f"Hohe IV ({iv_pct:.0f}%) bei niedrigem Expected Move - gutes Premium")
            else:
                # Hohe IV + hoher Expected Move = GEFAEHRLICH fuer Iron Condor!
                ic_score -= 20
                st_score += 15
                reasons.append(f"Hohe IV ({iv_pct:.0f}%) mit hohem Expected Move - Vorsicht!")
        elif iv_pct < 30:
            st_score += 10
            reasons.append(f"Niedrige IV ({iv_pct:.0f}%) - guenstiger Straddle-Einstieg")

        # EXPECTED MOVE - KRITISCH fuer Iron Condor!
        if expected_move >= 3:
            # Hoher Expected Move = DISQUALIFIKATION fuer Iron Condor
            ic_score -= 40  # Starke Strafe!
            st_score += 20
            reasons.append(f"HOHER Expected Move ({expected_move:.1f}%) - NUR Straddle!")
        elif expected_move >= 2:
            # Mittlerer Expected Move = Iron Condor riskant
            ic_score -= 20
            st_score += 10
            reasons.append(f"Expected Move ({expected_move:.1f}%) - Iron Condor riskant")
        elif expected_move < 1.5:
            # Niedriger Expected Move = ideal fuer Iron Condor
            ic_score += 15
            reasons.append(f"Niedriger Expected Move ({expected_move:.1f}%) - ideal fuer Iron Condor")

        # === LIQUIDITAET ===
        if not liquidity.get('is_liquid'):
            ic_score -= 20
            st_score -= 20
            warnings.append("Geringe Optionsliquiditaet")

        spread_pct = liquidity.get('spread_pct', 100)
        if spread_pct > 10:
            warnings.append(f"Breiter Bid-Ask Spread ({spread_pct:.1f}%)")

        # === AKTIENVOLUMEN ===
        if avg_volume > 10_000_000:
            ic_score += 5
            st_score += 5
        elif avg_volume < 1_000_000:
            warnings.append("Niedriges Handelsvolumen")

        # Scores begrenzen
        ic_score = max(0, min(100, ic_score))
        st_score = max(0, min(100, st_score))

        return ic_score, st_score, reasons, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("STOCK SCREENER TEST")
    print("=" * 60)

    screener = StockScreener()
    results = screener.screen_all()

    print("\n" + "=" * 60)
    print("IRON CONDOR KANDIDATEN (keine Events, ruhiger Markt)")
    print("=" * 60)
    for r in results['iron_condor']:
        print(f"\n{r.symbol} ({r.company_name}) - Score: {r.iron_condor_score:.0f}")
        print(f"  Preis: ${r.current_price:.2f}")
        print(f"  Gruende: {', '.join(r.reasons)}")
        if r.warnings:
            print(f"  Warnungen: {', '.join(r.warnings)}")

    print("\n" + "=" * 60)
    print("STRADDLE KANDIDATEN (Earnings/Events erwartet)")
    print("=" * 60)
    for r in results['straddle']:
        print(f"\n{r.symbol} ({r.company_name}) - Score: {r.straddle_score:.0f}")
        print(f"  Preis: ${r.current_price:.2f}")
        if r.earnings_date:
            print(f"  Earnings: {r.earnings_date} (in {r.days_to_earnings} Tagen)")
        print(f"  Gruende: {', '.join(r.reasons)}")
        if r.warnings:
            print(f"  Warnungen: {', '.join(r.warnings)}")
