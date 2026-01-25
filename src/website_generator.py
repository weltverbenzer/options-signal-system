"""
Webseiten-Generator v3
======================
Generiert statische HTML-Seiten für GitHub Pages.

Features:
- Übersichtsseite mit allen Kandidaten
- Detail-Seiten pro Kandidat mit:
  - TradingView Chart
  - News-Auszuege
  - Erweiterte Trade-Details
- Mobile-responsive Design
- Dunkles Theme
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path


class WebsiteGenerator:
    """Generiert statische Webseiten mit Kandidaten"""

    def __init__(self, config: dict):
        website_config = config.get('website', {})
        self.enabled = website_config.get('enabled', False)
        self.title = website_config.get('title', 'Options Signal System')

        # Output-Verzeichnis relativ zum Projekt-Root
        project_root = Path(__file__).parent.parent
        self.output_dir = project_root / website_config.get('output_dir', 'docs')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_v2(self, results: Dict) -> bool:
        """Generiert alle Webseiten"""
        if not self.enabled:
            print("Webseiten-Generierung deaktiviert")
            return False

        try:
            # Hauptseite generieren
            html = self._generate_main_page(results)
            with open(self.output_dir / 'index.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Hauptseite generiert: {self.output_dir / 'index.html'}")

            # Detail-Seiten generieren
            all_candidates = results.get('iron_condor', []) + results.get('straddle', [])
            for item in all_candidates:
                c = item['candidate']
                d = item['details']
                strategy = 'iron_condor' if item in results.get('iron_condor', []) else 'straddle'

                detail_html = self._generate_detail_page(c, d, strategy)
                detail_path = self.output_dir / f"{c.symbol.lower()}.html"
                with open(detail_path, 'w', encoding='utf-8') as f:
                    f.write(detail_html)
                print(f"Detail-Seite generiert: {detail_path}")

            return True

        except Exception as e:
            print(f"Fehler bei Webseiten-Generierung: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_base_styles(self) -> str:
        """Gemeinsame CSS-Styles"""
        return """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        header { text-align: center; padding: 30px 0; border-bottom: 2px solid #e94560; margin-bottom: 30px; }
        header h1 { color: #e94560; font-size: 2rem; margin-bottom: 10px; }
        header .date { color: #888; font-size: 0.9rem; }
        a { color: #4dabf7; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #e94560; font-size: 1.5rem; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .section .subtitle { color: #888; font-size: 0.9rem; margin-bottom: 20px; }
        .card {
            background: #16213e;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #28a745;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(0,0,0,0.3); }
        .card.warning { border-left-color: #ffc107; }
        .card.invalid { border-left-color: #dc3545; opacity: 0.7; }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .symbol { font-size: 1.8rem; font-weight: bold; color: #fff; }
        .company { color: #888; font-size: 0.9rem; margin-top: 5px; }
        .score { background: #0f3460; padding: 8px 15px; border-radius: 20px; font-size: 0.9rem; color: #fff; }
        .price { color: #28a745; font-size: 1.3rem; margin-bottom: 15px; }
        .earnings-badge { background: #e94560; color: #fff; padding: 3px 10px; border-radius: 15px; font-size: 0.8rem; margin-left: 10px; }
        .reasons { background: #0f3460; padding: 15px; border-radius: 10px; margin-bottom: 15px; }
        .reasons-label { color: #e94560; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .trade-details { background: #0a1628; padding: 15px; border-radius: 10px; margin-top: 15px; }
        .trade-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #16213e; }
        .trade-row:last-child { border-bottom: none; }
        .trade-row .value { font-weight: bold; }
        .profit { color: #28a745; }
        .loss { color: #dc3545; }
        .warning-text { color: #ffc107; }
        .warning-box { background: rgba(255, 193, 7, 0.1); border: 1px solid #ffc107; padding: 10px; border-radius: 5px; margin-top: 10px; color: #ffc107; font-size: 0.85rem; }
        .no-candidates { background: #16213e; border-radius: 10px; padding: 30px; text-align: center; color: #888; }
        .disclaimer { background: #2a2a4a; padding: 20px; border-radius: 10px; text-align: center; margin-top: 30px; }
        footer { text-align: center; padding: 30px; color: #666; font-size: 0.8rem; }
        .detail-link { display: inline-block; margin-top: 10px; padding: 8px 15px; background: #e94560; color: #fff; border-radius: 5px; font-size: 0.85rem; }
        .detail-link:hover { background: #d63550; text-decoration: none; }
        @media (max-width: 600px) { .card-header { flex-direction: column; } .score { margin-top: 10px; } .symbol { font-size: 1.4rem; } }
        """

    def _generate_main_page(self, results: Dict) -> str:
        """Generiert die Hauptseite"""
        generated_at = results.get('generated_at', datetime.now())

        ic_cards = ""
        for item in results.get('iron_condor', []):
            ic_cards += self._create_card_html(item, 'iron_condor')

        st_cards = ""
        for item in results.get('straddle', []):
            st_cards += self._create_card_html(item, 'straddle')

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>{self._get_base_styles()}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p class="date">{generated_at.strftime('%d. %B %Y - %H:%M')} Uhr</p>
        </header>

        <div class="section">
            <h2>Iron Condor Kandidaten</h2>
            <p class="subtitle">Ruhige Aktien ohne Events - Seitwärtsbewegung erwartet</p>
            {ic_cards if ic_cards else '<div class="no-candidates">Keine geeigneten Kandidaten gefunden</div>'}
        </div>

        <div class="section">
            <h2>Straddle Kandidaten</h2>
            <p class="subtitle">Aktien mit Earnings/Events - Große Bewegung erwartet</p>
            {st_cards if st_cards else '<div class="no-candidates">Keine Earnings/Events heute</div>'}
        </div>

        <div class="disclaimer">
            <strong>WICHTIG:</strong> Dies sind Vorschläge - DU entscheidest!<br>
            Klicke auf eine Karte für Details, News und Chart.
        </div>

        <footer>
            <p>Zuletzt aktualisiert: {datetime.now().strftime('%d.%m.%Y %H:%M')} MEZ</p>
            <p style="margin-top: 10px;">Options Signal System v3</p>
        </footer>
    </div>
</body>
</html>"""

    def _create_card_html(self, item: Dict, strategy: str) -> str:
        """Erstellt klickbare Card für Hauptseite"""
        c = item['candidate']
        d = item['details']

        card_class = "card"
        if c.warnings:
            card_class += " warning"
        if not d.get('valid'):
            card_class += " invalid"

        earnings_badge = ""
        if c.earnings_date and c.days_to_earnings is not None:
            if c.days_to_earnings == 0:
                earnings_badge = '<span class="earnings-badge">EARNINGS HEUTE</span>'
            elif c.days_to_earnings == 1:
                earnings_badge = '<span class="earnings-badge">Earnings morgen</span>'
            elif c.days_to_earnings > 0:
                earnings_badge = f'<span class="earnings-badge">Earnings in {c.days_to_earnings}T</span>'

        score = c.iron_condor_score if strategy == "iron_condor" else c.straddle_score
        detail_url = f"{c.symbol.lower()}.html"

        return f"""
        <a href="{detail_url}" style="text-decoration: none; color: inherit;">
        <div class="{card_class}">
            <div class="card-header">
                <div>
                    <span class="symbol">{c.symbol}</span>
                    {earnings_badge}
                    <div class="company">{c.company_name}</div>
                </div>
                <div class="score">Score: {score:.0f}/100</div>
            </div>
            <div class="price">${c.current_price:.2f}</div>
            <div class="reasons">
                <div class="reasons-label">Warum dieser Kandidat?</div>
                {', '.join(c.reasons)}
            </div>
            <span class="detail-link">Details, News & Chart anzeigen</span>
        </div>
        </a>"""

    def _generate_detail_page(self, c, d: Dict, strategy: str) -> str:
        """Generiert Detail-Seite mit Chart und News"""
        score = c.iron_condor_score if strategy == "iron_condor" else c.straddle_score
        strategy_name = "Iron Condor" if strategy == "iron_condor" else "Straddle"

        # Trade Details HTML
        if strategy == "iron_condor" and d.get('valid'):
            trade_html = f"""
            <div class="trade-details">
                <h3 style="color:#e94560; margin-bottom:15px;">Iron Condor Setup</h3>
                <div class="trade-row"><span>Sell Put</span><span class="value">${d['short_put']:.0f}</span></div>
                <div class="trade-row"><span>Buy Put (Wing)</span><span class="value">${d['long_put']:.0f}</span></div>
                <div class="trade-row"><span>Sell Call</span><span class="value">${d['short_call']:.0f}</span></div>
                <div class="trade-row"><span>Buy Call (Wing)</span><span class="value">${d['long_call']:.0f}</span></div>
                <div class="trade-row" style="margin-top:15px; border-top:2px solid #333; padding-top:15px;">
                    <span>Net Credit</span><span class="value profit">${d['net_credit']:.2f} pro Contract</span>
                </div>
                <div class="trade-row"><span>Max Profit</span><span class="value profit">${d.get('max_profit', d['net_credit']*100):.0f}</span></div>
                <div class="trade-row"><span>Max Loss</span><span class="value loss">${d['max_loss']:.0f}</span></div>
                <div class="trade-row"><span>Empfohlene Contracts</span><span class="value">{d.get('contracts', 1)}</span></div>
            </div>"""
        elif strategy == "straddle" and d.get('valid'):
            trade_html = f"""
            <div class="trade-details">
                <h3 style="color:#e94560; margin-bottom:15px;">Straddle Setup</h3>
                <div class="trade-row"><span>Buy Call</span><span class="value">${d['call_strike']:.0f} @ ${d['call_price']:.2f}</span></div>
                <div class="trade-row"><span>Buy Put</span><span class="value">${d['put_strike']:.0f} @ ${d['put_price']:.2f}</span></div>
                <div class="trade-row"><span>Verfall</span><span class="value">{d['expiry']}</span></div>
                <div class="trade-row" style="margin-top:15px; border-top:2px solid #333; padding-top:15px;">
                    <span>Gesamtkosten</span><span class="value warning-text">${d['total_cost']:.0f}</span>
                </div>
                <div class="trade-row"><span>Risiko vom Konto</span><span class="value">{d['risk_pct']:.1f}%</span></div>
                <div class="trade-row"><span>Breakeven Up</span><span class="value">${d['breakeven_up']:.2f}</span></div>
                <div class="trade-row"><span>Breakeven Down</span><span class="value">${d['breakeven_down']:.2f}</span></div>
                <div class="trade-row"><span>Benötigte Bewegung</span><span class="value">+/-{d['breakeven_move_pct']:.1f}%</span></div>
            </div>"""
        else:
            trade_html = f'<div class="warning-box">Trade nicht möglich: {d.get("reason", "Unbekannt")}</div>'

        # News HTML
        news_html = ""
        if hasattr(c, 'news') and c.news:
            news_items = ""
            for news in c.news[:5]:
                pub_date = ""
                if news.get('published'):
                    try:
                        pub_date = datetime.fromtimestamp(news['published']).strftime('%d.%m.%Y')
                    except:
                        pass
                news_items += f"""
                <div style="background:#0a1628; padding:15px; border-radius:10px; margin-bottom:10px;">
                    <a href="{news.get('link', '#')}" target="_blank" style="color:#fff; font-weight:bold; font-size:1rem;">
                        {news.get('title', 'Keine Headline')}
                    </a>
                    <p style="color:#888; font-size:0.85rem; margin-top:5px;">{news.get('source', '')} {pub_date}</p>
                    <p style="color:#aaa; font-size:0.9rem; margin-top:8px;">{news.get('summary', '')}</p>
                </div>"""
            news_html = f"""
            <div class="section">
                <h2>Aktuelle News</h2>
                {news_items}
            </div>"""
        else:
            news_html = """
            <div class="section">
                <h2>Aktuelle News</h2>
                <div class="no-candidates">Keine aktuellen News verfügbar</div>
            </div>"""

        # Earnings Info
        earnings_info = ""
        if c.earnings_date:
            earnings_info = f"""
            <div style="background:#e94560; color:#fff; padding:15px; border-radius:10px; margin-bottom:20px; text-align:center;">
                <strong>EARNINGS: {c.earnings_date}</strong>
                {f' (in {c.days_to_earnings} Tagen)' if c.days_to_earnings and c.days_to_earnings > 0 else ' - HEUTE!' if c.days_to_earnings == 0 else ''}
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{c.symbol} - {strategy_name} | {self.title}</title>
    <style>
        {self._get_base_styles()}
        .back-link {{ display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #0f3460; border-radius: 5px; }}
        .chart-container {{ background: #16213e; border-radius: 15px; padding: 20px; margin-bottom: 30px; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .info-box {{ background: #0f3460; padding: 15px; border-radius: 10px; text-align: center; }}
        .info-box .label {{ color: #888; font-size: 0.75rem; text-transform: uppercase; }}
        .info-box .value {{ color: #fff; font-size: 1.3rem; font-weight: bold; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">Zurück zur Übersicht</a>

        <header>
            <h1>{c.symbol}</h1>
            <p style="color:#888; font-size:1.1rem;">{c.company_name}</p>
            <p class="date">{strategy_name} Kandidat | Score: {score:.0f}/100</p>
        </header>

        {earnings_info}

        <div class="info-grid">
            <div class="info-box">
                <div class="label">Aktueller Kurs</div>
                <div class="value" style="color:#28a745;">${c.current_price:.2f}</div>
            </div>
            <div class="info-box">
                <div class="label">IV Percentile</div>
                <div class="value">{c.iv_percentile:.0f}%</div>
            </div>
            <div class="info-box">
                <div class="label">Expected Move</div>
                <div class="value">{c.expected_move_pct:.1f}%</div>
            </div>
            <div class="info-box">
                <div class="label">Bid-Ask Spread</div>
                <div class="value">{c.bid_ask_spread_pct:.1f}%</div>
            </div>
        </div>

        <div class="section">
            <h2>Chart</h2>
            <div class="chart-container">
                <!-- TradingView Widget -->
                <div class="tradingview-widget-container">
                    <div id="tradingview_chart" style="height:400px;"></div>
                </div>
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                new TradingView.widget({{
                    "width": "100%",
                    "height": 400,
                    "symbol": "{c.symbol}",
                    "interval": "D",
                    "timezone": "Europe/Berlin",
                    "theme": "dark",
                    "style": "1",
                    "locale": "de_DE",
                    "toolbar_bg": "#16213e",
                    "enable_publishing": false,
                    "hide_side_toolbar": false,
                    "allow_symbol_change": false,
                    "container_id": "tradingview_chart",
                    "hide_volume": false
                }});
                </script>
            </div>
        </div>

        <div class="section">
            <h2>Trade Setup</h2>
            <div class="reasons">
                <div class="reasons-label">Warum dieser Kandidat?</div>
                {', '.join(c.reasons)}
            </div>
            {trade_html}
        </div>

        {news_html}

        <div class="section">
            <h2>Quellen</h2>
            <div style="display:flex; gap:15px; flex-wrap:wrap;">
                <a href="{c.source_url_quote}" target="_blank" class="detail-link">Yahoo Finance Kurs</a>
                <a href="{c.source_url_options}" target="_blank" class="detail-link">Optionskette</a>
                <a href="{c.source_url_earnings}" target="_blank" class="detail-link">Earnings Kalender</a>
            </div>
        </div>

        <footer>
            <p>Generiert: {datetime.now().strftime('%d.%m.%Y %H:%M')} MEZ</p>
            <a href="index.html">Zurück zur Übersicht</a>
        </footer>
    </div>
</body>
</html>"""
