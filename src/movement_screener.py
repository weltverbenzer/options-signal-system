"""
Movement Screener v1
====================
Findet Aktien/Werte mit hohem Bewegungspotential in den nächsten Tagen.
Analysiert News-Sentiment und Expected Move.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class MovementCandidate:
    """Kandidat mit Bewegungspotential"""
    symbol: str
    company_name: str
    current_price: float
    expected_move_pct: float
    iv_percentile: float

    # News-Sentiment
    news_count: int
    sentiment_score: int  # Positiv: +X, Negativ: -X
    sentiment_label: str  # z.B. "+5" oder "-3" oder "0"

    # Earnings
    has_earnings_soon: bool
    earnings_date: Optional[str]
    days_to_earnings: Optional[int]

    # Scoring
    movement_score: float  # 0-100

    # Details
    news: List[Dict]
    reasons: List[str]
    source_url_quote: str
    source_url_options: str
    source_url_earnings: str


# S&P 500 Tickers (Top 100 nach Marktkapitalisierung + aktive Nebenwerte)
DEFAULT_UNIVERSE = [
    # Mega Caps
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JNJ",
    "XOM", "V", "PG", "JPM", "MA", "HD", "CVX", "MRK", "ABBV", "PEP",
    "COST", "AVGO", "KO", "ADBE", "TMO", "MCD", "CSCO", "ACN", "LLY", "NKE",
    "DHR", "ABT", "TXN", "VZ", "NEE", "CMCSA", "ORCL", "WMT", "BMY", "PM",

    # Tech & Growth
    "AMD", "INTC", "NFLX", "CRM", "PYPL", "AMAT", "QCOM", "LRCX", "KLAC", "SNPS",
    "PANW", "CRWD", "NOW", "TEAM", "DDOG", "NET", "SNOW", "ZS", "OKTA",

    # Finanz
    "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "SPGI", "MCO",

    # Konsum & Retail
    "DIS", "NKE", "SBUX", "TGT", "LOW", "TJX", "BKNG", "ABNB", "UBER", "LYFT",

    # Energie & Rohstoffe
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO",

    # Gesundheit & Pharma
    "PFE", "MRNA", "BNTX", "GILD", "BIIB", "REGN", "VRTX", "ISRG",

    # Volatilitäts-Favoriten (oft viel Bewegung)
    "GME", "AMC", "PLTR", "RIVN", "LCID", "SOFI", "NIO", "COIN", "HOOD",

    # Indizes & ETFs
    "SPY", "QQQ", "IWM", "DIA"
]


class MovementScreener:
    """Screent nach Aktien mit hohem Bewegungspotential"""

    def __init__(self, universe: List[str] = None):
        self.universe = universe or DEFAULT_UNIVERSE

        # Sentiment Keywords
        self.bullish_keywords = [
            "beat", "beats", "upgraded", "upgrade", "record", "surge", "surges",
            "growth", "gains", "rallies", "rally", "bullish", "strong", "soars",
            "jumps", "climbs", "positive", "outperform", "buy", "optimistic"
        ]

        self.bearish_keywords = [
            "miss", "misses", "downgraded", "downgrade", "loss", "decline", "falls",
            "drops", "drop", "weak", "disappointing", "bearish", "cuts", "slumps",
            "tumbles", "plunges", "negative", "underperform", "sell", "warning"
        ]

    def screen_all(self) -> List[MovementCandidate]:
        """Screent alle Symbole nach Bewegungspotential"""
        print(f"\n=== MOVEMENT SCREENER v1 ===")
        print(f"Universe: {len(self.universe)} Symbole\n")

        candidates = []

        for i, symbol in enumerate(self.universe, 1):
            print(f"[{i}/{len(self.universe)}] Analysiere {symbol}...", end=" ")

            try:
                candidate = self._analyze_symbol(symbol)
                if candidate and candidate.movement_score > 30:  # Mindest-Score
                    candidates.append(candidate)
                    print(f"✓ Score: {candidate.movement_score:.0f}")
                else:
                    print("✗ Zu niedrig")

            except Exception as e:
                print(f"✗ Fehler: {e}")

            # Rate limiting
            time.sleep(0.3)

        # Sortiere nach Score
        candidates.sort(key=lambda x: x.movement_score, reverse=True)

        print(f"\n=== GEFUNDEN: {len(candidates)} Kandidaten ===\n")
        return candidates

    def _analyze_symbol(self, symbol: str) -> Optional[MovementCandidate]:
        """Analysiert ein einzelnes Symbol"""
        ticker = yf.Ticker(symbol)

        # Basis-Daten
        info = ticker.info
        if not info:
            return None

        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not current_price:
            return None

        company_name = info.get('shortName', symbol)

        # Expected Move berechnen
        expected_move = self._calculate_expected_move(ticker, current_price)
        if expected_move is None:
            return None

        # IV Percentile (approximiert über historische Volatilität)
        iv_percentile = self._get_iv_percentile(ticker)

        # Earnings prüfen
        earnings_info = self._check_earnings(ticker)

        # News analysieren
        news_data = self._analyze_news(ticker)

        # Gründe sammeln
        reasons = self._generate_reasons(expected_move, news_data, earnings_info)

        # Score berechnen
        score = self._calculate_movement_score(
            expected_move, iv_percentile, news_data, earnings_info
        )

        return MovementCandidate(
            symbol=symbol,
            company_name=company_name,
            current_price=current_price,
            expected_move_pct=expected_move,
            iv_percentile=iv_percentile,
            news_count=news_data['count'],
            sentiment_score=news_data['score'],
            sentiment_label=news_data['label'],
            has_earnings_soon=earnings_info['has_earnings_soon'],
            earnings_date=earnings_info['earnings_date'],
            days_to_earnings=earnings_info['days_to_earnings'],
            movement_score=score,
            news=news_data['articles'],
            reasons=reasons,
            source_url_quote=f"https://finance.yahoo.com/quote/{symbol}",
            source_url_options=f"https://finance.yahoo.com/quote/{symbol}/options",
            source_url_earnings=f"https://finance.yahoo.com/calendar/earnings?symbol={symbol}"
        )

    def _calculate_expected_move(self, ticker, current_price: float) -> Optional[float]:
        """Berechnet Expected Move aus nächster Weekly Straddle"""
        try:
            expirations = ticker.options
            if not expirations or len(expirations) == 0:
                return None

            # Nächstes Verfallsdatum
            expiry = expirations[0]
            chain = ticker.option_chain(expiry)

            # ATM Strike
            atm_strike = round(current_price)

            # Nächsten verfügbaren Strike finden
            call_strikes = chain.calls['strike'].values
            put_strikes = chain.puts['strike'].values

            if len(call_strikes) == 0 or len(put_strikes) == 0:
                return None

            atm_call_idx = abs(call_strikes - atm_strike).argmin()
            atm_put_idx = abs(put_strikes - atm_strike).argmin()

            atm_call = chain.calls.iloc[atm_call_idx]
            atm_put = chain.puts.iloc[atm_put_idx]

            # Straddle-Preis
            call_price = (atm_call['bid'] + atm_call['ask']) / 2
            put_price = (atm_put['bid'] + atm_put['ask']) / 2
            straddle_price = call_price + put_price

            # Expected Move = Straddle-Preis in %
            expected_move_pct = (straddle_price / current_price) * 100

            return expected_move_pct

        except:
            return None

    def _get_iv_percentile(self, ticker) -> float:
        """Approximiert IV Percentile über historische Volatilität"""
        try:
            hist = ticker.history(period="1y")
            if len(hist) < 30:
                return 50.0

            # 30-Tage Volatilität
            returns = hist['Close'].pct_change().dropna()
            current_vol = returns.tail(30).std() * (252 ** 0.5) * 100

            # Vergleich mit 1-Jahres-Range
            year_vols = []
            for i in range(0, len(returns) - 30, 5):
                vol = returns.iloc[i:i+30].std() * (252 ** 0.5) * 100
                year_vols.append(vol)

            if len(year_vols) < 10:
                return 50.0

            percentile = sum(1 for v in year_vols if v < current_vol) / len(year_vols) * 100
            return percentile

        except:
            return 50.0

    def _check_earnings(self, ticker) -> Dict:
        """Prüft Earnings-Termine (3 Methoden)"""
        result = {
            'has_earnings_soon': False,
            'earnings_date': None,
            'days_to_earnings': None
        }

        earnings_date = None

        # Methode 1: ticker.info
        try:
            info = ticker.info
            if info and 'earningsDate' in info:
                ed = info['earningsDate']
                if ed:
                    if isinstance(ed, (int, float)):
                        from datetime import datetime
                        earnings_date = datetime.fromtimestamp(ed)
                    elif isinstance(ed, list) and len(ed) > 0:
                        earnings_date = ed[0]
        except:
            pass

        # Methode 2: ticker.calendar
        if not earnings_date:
            try:
                cal = ticker.calendar
                if cal is not None and 'Earnings Date' in cal:
                    ed = cal['Earnings Date']
                    if ed is not None:
                        earnings_date = ed
            except:
                pass

        # Wenn Datum gefunden, Tage berechnen
        if earnings_date:
            try:
                if hasattr(earnings_date, 'date'):
                    ed_date = earnings_date.date()
                else:
                    ed_date = earnings_date

                today = datetime.now().date()
                days_to = (ed_date - today).days

                result['earnings_date'] = ed_date.strftime('%Y-%m-%d')
                result['days_to_earnings'] = days_to

                # Earnings bald = nächste 10 Tage
                if -1 <= days_to <= 10:
                    result['has_earnings_soon'] = True
            except:
                pass

        return result

    def _analyze_news(self, ticker) -> Dict:
        """Analysiert News-Sentiment"""
        result = {
            'count': 0,
            'score': 0,
            'label': '0',
            'articles': []
        }

        try:
            news = ticker.news
            if not news or not isinstance(news, list):
                return result

            bullish_count = 0
            bearish_count = 0

            for item in news[:10]:  # Top 10 News
                title = item.get('title', '').lower()
                if not title:
                    continue

                # Sentiment analysieren
                bull_hits = sum(1 for kw in self.bullish_keywords if kw in title)
                bear_hits = sum(1 for kw in self.bearish_keywords if kw in title)

                if bull_hits > bear_hits:
                    bullish_count += 1
                elif bear_hits > bull_hits:
                    bearish_count += 1

                # News speichern
                result['articles'].append({
                    'title': item.get('title', 'Keine Headline'),
                    'link': item.get('link', '#'),
                    'publisher': item.get('publisher', 'Unbekannt'),
                    'sentiment': 'bullish' if bull_hits > bear_hits else ('bearish' if bear_hits > bull_hits else 'neutral')
                })

            result['count'] = len(result['articles'])
            result['score'] = bullish_count - bearish_count

            if result['score'] > 0:
                result['label'] = f"+{result['score']}"
            elif result['score'] < 0:
                result['label'] = f"{result['score']}"
            else:
                result['label'] = "0"

        except:
            pass

        return result

    def _generate_reasons(self, expected_move: float, news_data: Dict, earnings_info: Dict) -> List[str]:
        """Generiert Begründungen für Auswahl"""
        reasons = []

        if expected_move > 5:
            reasons.append(f"Sehr hoher Expected Move ({expected_move:.1f}%)")
        elif expected_move > 3:
            reasons.append(f"Hoher Expected Move ({expected_move:.1f}%)")

        if earnings_info['has_earnings_soon']:
            days = earnings_info['days_to_earnings']
            if days == 0:
                reasons.append("Earnings HEUTE")
            elif days == 1:
                reasons.append("Earnings MORGEN")
            else:
                reasons.append(f"Earnings in {days} Tagen")

        if news_data['count'] >= 5:
            reasons.append(f"Viele News ({news_data['count']})")

        if news_data['score'] > 2:
            reasons.append(f"Stark bullisches Sentiment ({news_data['label']})")
        elif news_data['score'] < -2:
            reasons.append(f"Stark bearisches Sentiment ({news_data['label']})")

        if not reasons:
            reasons.append("Moderate Bewegung erwartet")

        return reasons

    def _calculate_movement_score(self, expected_move: float, iv_percentile: float,
                                  news_data: Dict, earnings_info: Dict) -> float:
        """Berechnet Movement-Score (0-100)"""
        score = 0.0

        # Expected Move (0-40 Punkte)
        score += min(expected_move * 5, 40)

        # IV Percentile (0-20 Punkte)
        score += (iv_percentile / 100) * 20

        # News Count (0-15 Punkte)
        score += min(news_data['count'] * 2, 15)

        # News Sentiment (0-15 Punkte)
        sentiment_score = abs(news_data['score'])
        score += min(sentiment_score * 3, 15)

        # Earnings Bonus (0-10 Punkte)
        if earnings_info['has_earnings_soon']:
            days = earnings_info['days_to_earnings']
            if 0 <= days <= 3:
                score += 10
            elif 4 <= days <= 7:
                score += 7
            else:
                score += 4

        return min(score, 100)
