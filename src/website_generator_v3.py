"""
Webseiten-Generator v3
=======================
Generiert statische HTML-Seiten für Movement-Kandidaten.
Inkl. News-Sentiment, Charts und Detail-Seiten.
"""

from pathlib import Path
from typing import Dict
from datetime import datetime


class WebsiteGeneratorV3:
    """Generiert statische Webseiten für Movement-Kandidaten"""

    def __init__(self, config: dict):
        website_config = config.get('website', {})
        self.enabled = website_config.get('enabled', True)
        self.title = website_config.get('title', 'Movement Signal System')

        # Output-Verzeichnis relativ zum Projekt-Root
        project_root = Path(__file__).parent.parent
        self.output_dir = project_root / website_config.get('output_dir', 'docs')

    def generate(self, results: Dict) -> bool:
        """Generiert Haupt- und Detail-Seiten"""
        if not self.enabled:
            return False

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Hauptseite generieren
            html = self._generate_main_page(results)
            with open(self.output_dir / 'index.html', 'w', encoding='utf-8') as f:
                f.write(html)

            # Detail-Seiten generieren
            for candidate in results.get('candidates', []):
                detail_html = self._generate_detail_page(candidate)
                detail_path = self.output_dir / f"{candidate.symbol.lower()}.html"
                with open(detail_path, 'w', encoding='utf-8') as f:
                    f.write(detail_html)

            return True

        except Exception as e:
            print(f"Website-Generierung Fehler: {e}")
            return False

    def _generate_main_page(self, results: Dict) -> str:
        """Generiert Hauptseite mit Overview"""
        cards = ""
        for i, c in enumerate(results.get('candidates', []), 1):
            cards += self._create_overview_card(c, i)

        return f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eaeaea;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 30px 20px;
            border-bottom: 2px solid #e94560;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #e94560;
            margin: 0;
            font-size: 36px;
        }}
        .header .subtitle {{
            color: #888;
            margin-top: 10px;
            font-size: 16px;
        }}
        .header .date {{
            color: #666;
            margin-top: 15px;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid #28a745;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(233, 69, 96, 0.3);
        }}
        .card.high-score {{
            border-left-color: #ffc107;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .rank {{
            background: #e94560;
            color: #fff;
            padding: 5px 10px;
            border-radius: 50%;
            font-size: 14px;
            font-weight: bold;
            margin-right: 10px;
        }}
        .symbol {{
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }}
        .score {{
            background: #0f3460;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
        }}
        .company {{
            color: #888;
            font-size: 14px;
            margin-top: 5px;
        }}
        .price {{
            color: #28a745;
            font-size: 20px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }}
        .metric {{
            background: #0a1628;
            padding: 10px;
            border-radius: 5px;
        }}
        .metric-label {{
            color: #888;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .metric-value {{
            color: #fff;
            font-size: 16px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .sentiment {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }}
        .sentiment.positive {{
            background: #28a745;
            color: #fff;
        }}
        .sentiment.negative {{
            background: #dc3545;
            color: #fff;
        }}
        .sentiment.neutral {{
            background: #6c757d;
            color: #fff;
        }}
        .earnings-badge {{
            background: #e94560;
            color: #fff;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-left: 10px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #333;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{self.title}</h1>
            <div class="subtitle">Aktien mit erwarteter Volatilität</div>
            <div class="date">{results['generated_at'].strftime('%d. %B %Y - %H:%M')} Uhr</div>
        </div>

        <div class="grid">
            {cards if cards else '<p style="color:#888;">Keine Kandidaten gefunden</p>'}
        </div>

        <div class="footer">
            Movement Signal System | Automatisch generiert | Klicke auf eine Karte für Details
        </div>
    </div>
</body>
</html>
"""

    def _create_overview_card(self, c, rank: int) -> str:
        """Erstellt Overview-Card für Hauptseite"""
        card_class = "card"
        if c.movement_score >= 70:
            card_class += " high-score"

        earnings_badge = ""
        if c.has_earnings_soon and c.days_to_earnings is not None:
            if c.days_to_earnings == 0:
                earnings_badge = '<span class="earnings-badge">EARNINGS HEUTE</span>'
            elif c.days_to_earnings == 1:
                earnings_badge = '<span class="earnings-badge">Morgen</span>'
            else:
                earnings_badge = f'<span class="earnings-badge">{c.days_to_earnings}T</span>'

        if c.sentiment_score > 0:
            sentiment_class = "positive"
        elif c.sentiment_score < 0:
            sentiment_class = "negative"
        else:
            sentiment_class = "neutral"

        return f"""
        <div class="{card_class}" onclick="window.location.href='{c.symbol.lower()}.html'">
            <div class="card-header">
                <div>
                    <span class="rank">#{rank}</span>
                    <span class="symbol">{c.symbol}</span>
                    {earnings_badge}
                </div>
                <div class="score">{c.movement_score:.0f}/100</div>
            </div>
            <div class="company">{c.company_name}</div>
            <div class="price">${c.current_price:.2f}</div>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">News Anzahl</div>
                    <div class="metric-value">{c.news_count}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Sentiment</div>
                    <div class="metric-value"><span class="sentiment {sentiment_class}">{c.sentiment_label}</span></div>
                </div>
            </div>
        </div>
        """

    def _generate_detail_page(self, c) -> str:
        """Generiert Detail-Seite für einzelnen Kandidaten"""
        earnings_section = ""
        if c.has_earnings_soon:
            earnings_section = f"""
            <div style="background: rgba(233, 69, 96, 0.2); border: 1px solid #e94560; padding: 15px; border-radius: 10px; margin-top: 20px;">
                <h3 style="margin-top: 0; color: #e94560;">📅 Earnings Event</h3>
                <p><strong>Datum:</strong> {c.earnings_date}</p>
                <p><strong>In {c.days_to_earnings} Tagen</strong></p>
            </div>
            """

        news_section = ""
        if hasattr(c, 'news') and c.news:
            news_items = ""
            for news in c.news[:10]:
                sentiment_badge = news.get('sentiment', 'neutral')
                sentiment_color = '#28a745' if sentiment_badge == 'bullish' else ('#dc3545' if sentiment_badge == 'bearish' else '#6c757d')

                news_items += f"""
                <div style="background: #0a1628; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid {sentiment_color};">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <a href="{news.get('link', '#')}" target="_blank" style="color: #4dabf7; text-decoration: none; font-weight: bold; flex: 1;">
                            {news.get('title', 'Keine Headline')}
                        </a>
                        <span style="background: {sentiment_color}; color: #fff; padding: 3px 10px; border-radius: 15px; font-size: 11px; margin-left: 10px;">
                            {sentiment_badge.upper()}
                        </span>
                    </div>
                    <div style="color: #888; font-size: 12px; margin-top: 5px;">{news.get('publisher', 'Unbekannt')}</div>
                </div>
                """

            news_section = f"""
            <div style="margin-top: 30px;">
                <h3 style="color: #e94560; border-bottom: 1px solid #333; padding-bottom: 10px;">📰 Aktuelle News ({c.news_count} Artikel)</h3>
                {news_items}
            </div>
            """
        else:
            news_section = """
            <div style="margin-top: 30px;">
                <h3 style="color: #e94560; border-bottom: 1px solid #333; padding-bottom: 10px;">📰 Aktuelle News</h3>
                <p style="color: #888;">Keine News verfügbar</p>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{c.symbol} - {c.company_name} | {self.title}</title>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eaeaea;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .back-btn {{
            display: inline-block;
            background: #0f3460;
            color: #fff;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            margin-bottom: 20px;
        }}
        .back-btn:hover {{
            background: #1a4d7a;
        }}
        .header {{
            background: #16213e;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .symbol {{
            font-size: 36px;
            font-weight: bold;
            color: #e94560;
        }}
        .company {{
            color: #888;
            font-size: 18px;
            margin-top: 5px;
        }}
        .price {{
            color: #28a745;
            font-size: 32px;
            font-weight: bold;
            margin-top: 15px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .metric {{
            background: #0a1628;
            padding: 15px;
            border-radius: 10px;
        }}
        .metric-label {{
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .metric-value {{
            color: #fff;
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .reasons {{
            background: #0f3460;
            padding: 15px 20px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        .reasons-label {{
            color: #e94560;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        .chart-container {{
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
        }}
        .sentiment {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 14px;
            font-weight: bold;
        }}
        .sentiment.positive {{
            background: #28a745;
            color: #fff;
        }}
        .sentiment.negative {{
            background: #dc3545;
            color: #fff;
        }}
        .sentiment.neutral {{
            background: #6c757d;
            color: #fff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-btn">← Zurück zur Übersicht</a>

        <div class="header">
            <div class="symbol">{c.symbol}</div>
            <div class="company">{c.company_name}</div>
            <div class="price">${c.current_price:.2f}</div>

            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Movement Score</div>
                    <div class="metric-value">{c.movement_score:.0f}/100</div>
                </div>
                <div class="metric">
                    <div class="metric-label">News Anzahl</div>
                    <div class="metric-value">{c.news_count}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">News Sentiment</div>
                    <div class="metric-value">
                        <span class="sentiment {'positive' if c.sentiment_score > 0 else 'negative' if c.sentiment_score < 0 else 'neutral'}">
                            {c.sentiment_label}
                        </span>
                    </div>
                </div>
            </div>

            <div class="reasons">
                <div class="reasons-label">Warum dieser Kandidat?</div>
                {', '.join(c.reasons)}
            </div>

            {earnings_section}
        </div>

        <div class="chart-container">
            <h3 style="color: #e94560; margin-top: 0;">📈 Chart</h3>
            <div id="tradingview_chart"></div>
            <script type="text/javascript">
                new TradingView.widget({{
                    "width": "100%",
                    "height": 500,
                    "symbol": "{c.symbol}",
                    "interval": "D",
                    "timezone": "Europe/Berlin",
                    "theme": "dark",
                    "style": "1",
                    "locale": "de_DE",
                    "toolbar_bg": "#16213e",
                    "enable_publishing": false,
                    "hide_side_toolbar": false,
                    "allow_symbol_change": true,
                    "container_id": "tradingview_chart"
                }});
            </script>
        </div>

        {news_section}

        <div style="margin-top: 30px; padding: 20px; background: #16213e; border-radius: 10px;">
            <h3 style="color: #e94560; margin-top: 0;">🔗 Quellen</h3>
            <a href="{c.source_url_quote}" target="_blank" style="color: #4dabf7; margin-right: 20px;">Yahoo Finance Quote</a>
            <a href="{c.source_url_options}" target="_blank" style="color: #4dabf7; margin-right: 20px;">Options Chain</a>
            <a href="{c.source_url_earnings}" target="_blank" style="color: #4dabf7;">Earnings Kalender</a>
        </div>

        <div style="text-align: center; padding: 30px; color: #666; font-size: 12px; border-top: 1px solid #333; margin-top: 30px;">
            Movement Signal System | Automatisch generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}
        </div>
    </div>
</body>
</html>
"""
