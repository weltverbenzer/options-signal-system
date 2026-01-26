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
                if candidate and candidate.movement_score > 20:  # Mindest-Score
                    candidates.append(candidate)
                    print(f"✓ Score: {candidate.movement_score:.0f} ({candidate.news_count} News)")
                else:
                    print("✗ Keine/wenig News")

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

        # Earnings prüfen
        earnings_info = self._check_earnings(ticker)

        # News analysieren
        news_data = self._analyze_news(ticker)

        # Nur behalten wenn News vorhanden
        if news_data['count'] == 0:
            return None

        # Gründe sammeln
        reasons = self._generate_reasons(news_data, earnings_info)

        # Score berechnen
        score = self._calculate_movement_score(news_data, earnings_info)

        return MovementCandidate(
            symbol=symbol,
            company_name=company_name,
            current_price=current_price,
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
            source_url_earnings=f"https://finance.yahoo.com/calendar/earnings?symbol={symbol}"
        )


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

    def _generate_reasons(self, news_data: Dict, earnings_info: Dict) -> List[str]:
        """Generiert Begründungen für Auswahl"""
        reasons = []

        if earnings_info['has_earnings_soon']:
            days = earnings_info['days_to_earnings']
            if days == 0:
                reasons.append("Earnings HEUTE")
            elif days == 1:
                reasons.append("Earnings MORGEN")
            else:
                reasons.append(f"Earnings in {days} Tagen")

        if news_data['count'] >= 8:
            reasons.append(f"Sehr viele News ({news_data['count']})")
        elif news_data['count'] >= 5:
            reasons.append(f"Viele News ({news_data['count']})")

        if news_data['score'] > 3:
            reasons.append(f"Sehr bullisches Sentiment ({news_data['label']})")
        elif news_data['score'] > 1:
            reasons.append(f"Bullisches Sentiment ({news_data['label']})")
        elif news_data['score'] < -3:
            reasons.append(f"Sehr bearisches Sentiment ({news_data['label']})")
        elif news_data['score'] < -1:
            reasons.append(f"Bearisches Sentiment ({news_data['label']})")

        if not reasons:
            reasons.append(f"News-Aktivität ({news_data['count']} Artikel)")

        return reasons

    def _calculate_movement_score(self, news_data: Dict, earnings_info: Dict) -> float:
        """Berechnet Movement-Score (0-100) basierend auf News"""
        score = 0.0

        # News Count (0-50 Punkte) - Hauptkriterium
        score += min(news_data['count'] * 5, 50)

        # News Sentiment Stärke (0-30 Punkte)
        sentiment_strength = abs(news_data['score'])
        score += min(sentiment_strength * 6, 30)

        # Earnings Bonus (0-20 Punkte)
        if earnings_info['has_earnings_soon']:
            days = earnings_info['days_to_earnings']
            if 0 <= days <= 2:
                score += 20
            elif 3 <= days <= 5:
                score += 15
            elif 6 <= days <= 10:
                score += 10

        return min(score, 100)
