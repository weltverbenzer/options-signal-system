"""
Webseiten-Generator v2
======================
Generiert eine statische HTML-Seite fuer GitHub Pages.

Features:
- Iron Condor und Straddle Kandidaten anzeigen
- Mit Begruendungen und Quellen
- Mobile-responsive Design
- Dunkles Theme
"""

import os
import json
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path


class WebsiteGenerator:
    """Generiert eine statische Webseite mit Kandidaten"""

    def __init__(self, config: dict):
        """
        Args:
            config: Website-Konfiguration
        """
        website_config = config.get('website', {})
        self.enabled = website_config.get('enabled', False)
        self.title = website_config.get('title', 'Options Signal System')

        # Output-Verzeichnis relativ zum Projekt-Root (nicht src/)
        project_root = Path(__file__).parent.parent
        self.output_dir = project_root / website_config.get('output_dir', 'docs')

        # Stelle sicher dass Output-Verzeichnis existiert
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_v2(self, results: Dict) -> bool:
        """
        Generiert die Webseite mit Iron Condor und Straddle Kandidaten.

        Args:
            results: Dict mit 'iron_condor', 'straddle', 'generated_at'

        Returns:
            True wenn erfolgreich
        """
        if not self.enabled:
            print("Webseiten-Generierung deaktiviert")
            return False

        try:
            html = self._generate_html_v2(results)

            output_path = Path(self.output_dir) / 'index.html'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"Webseite generiert: {output_path}")
            return True

        except Exception as e:
            print(f"Fehler bei Webseiten-Generierung: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_html_v2(self, results: Dict) -> str:
        """Generiert HTML fuer v2 mit Kandidaten"""
        generated_at = results.get('generated_at', datetime.now())

        # Iron Condor Karten
        ic_cards = ""
        for item in results.get('iron_condor', []):
            ic_cards += self._create_candidate_card_html(item, 'iron_condor')

        # Straddle Karten
        st_cards = ""
        for item in results.get('straddle', []):
            st_cards += self._create_candidate_card_html(item, 'straddle')

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #e94560;
            margin-bottom: 30px;
        }}
        header h1 {{ color: #e94560; font-size: 2rem; margin-bottom: 10px; }}
        header .date {{ color: #888; font-size: 0.9rem; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{
            color: #e94560;
            font-size: 1.5rem;
            margin-bottom: 10px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        .section .subtitle {{ color: #888; font-size: 0.9rem; margin-bottom: 20px; }}
        .card {{
            background: #16213e;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #28a745;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }}
        .card.warning {{ border-left-color: #ffc107; }}
        .card.invalid {{ border-left-color: #dc3545; opacity: 0.7; }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        .symbol {{ font-size: 1.8rem; font-weight: bold; color: #fff; }}
        .company {{ color: #888; font-size: 0.9rem; margin-top: 5px; }}
        .score {{
            background: #0f3460;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #fff;
        }}
        .price {{ color: #28a745; font-size: 1.3rem; margin-bottom: 15px; }}
        .earnings-badge {{
            background: #e94560;
            color: #fff;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8rem;
            margin-left: 10px;
        }}
        .reasons {{
            background: #0f3460;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        .reasons-label {{
            color: #e94560;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}
        .trade-details {{
            background: #0a1628;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }}
        .trade-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #16213e;
        }}
        .trade-row:last-child {{ border-bottom: none; }}
        .trade-row .value {{ font-weight: bold; }}
        .profit {{ color: #28a745; }}
        .loss {{ color: #dc3545; }}
        .warning-text {{ color: #ffc107; }}
        .warning-box {{
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            color: #ffc107;
            font-size: 0.85rem;
        }}
        .sources {{
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #333;
            font-size: 0.85rem;
        }}
        .sources a {{ color: #4dabf7; text-decoration: none; margin-right: 15px; }}
        .sources a:hover {{ text-decoration: underline; }}
        .no-candidates {{
            background: #16213e;
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            color: #888;
        }}
        .disclaimer {{
            background: #2a2a4a;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-top: 30px;
        }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.8rem;
        }}
        @media (max-width: 600px) {{
            .card-header {{ flex-direction: column; }}
            .score {{ margin-top: 10px; }}
            .symbol {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p class="date">{generated_at.strftime('%d. %B %Y - %H:%M')} Uhr</p>
        </header>

        <div class="section">
            <h2>Iron Condor Kandidaten</h2>
            <p class="subtitle">Ruhige Aktien ohne Events - Seitwaertsbewegung erwartet</p>
            {ic_cards if ic_cards else '<div class="no-candidates">Keine geeigneten Kandidaten gefunden</div>'}
        </div>

        <div class="section">
            <h2>Straddle Kandidaten</h2>
            <p class="subtitle">Aktien mit Earnings/Events - Grosse Bewegung erwartet</p>
            {st_cards if st_cards else '<div class="no-candidates">Keine Earnings/Events heute</div>'}
        </div>

        <div class="disclaimer">
            <strong>WICHTIG:</strong> Dies sind Vorschlaege zur Auswahl - DU entscheidest!<br>
            Pruefe Bid/Ask Spreads vor dem Trade. Nicht alle Optionen sind immer handelbar.
        </div>

        <footer>
            <p>Zuletzt aktualisiert: {datetime.now().strftime('%d.%m.%Y %H:%M')} MEZ</p>
            <p style="margin-top: 10px;">Options Signal System v2 | Automatisch generiert</p>
        </footer>
    </div>
</body>
</html>"""

    def _create_candidate_card_html(self, item: Dict, strategy: str) -> str:
        """Erstellt HTML-Card fuer einen Kandidaten"""
        c = item['candidate']
        d = item['details']

        card_class = "card"
        if c.warnings:
            card_class += " warning"
        if not d.get('valid'):
            card_class += " invalid"

        # Earnings Badge
        earnings_badge = ""
        if c.earnings_date and c.days_to_earnings is not None:
            if c.days_to_earnings == 0:
                earnings_badge = '<span class="earnings-badge">EARNINGS HEUTE</span>'
            elif c.days_to_earnings == 1:
                earnings_badge = '<span class="earnings-badge">Earnings morgen</span>'
            elif c.days_to_earnings > 0:
                earnings_badge = f'<span class="earnings-badge">Earnings in {c.days_to_earnings}T</span>'

        # Score
        score = c.iron_condor_score if strategy == "iron_condor" else c.straddle_score

        # Trade Details
        if strategy == "iron_condor" and d.get('valid'):
            trade_html = f"""
            <div class="trade-details">
                <div class="trade-row"><span>Sell Put</span><span class="value">${d['short_put']:.0f}</span></div>
                <div class="trade-row"><span>Buy Put</span><span class="value">${d['long_put']:.0f}</span></div>
                <div class="trade-row"><span>Sell Call</span><span class="value">${d['short_call']:.0f}</span></div>
                <div class="trade-row"><span>Buy Call</span><span class="value">${d['long_call']:.0f}</span></div>
                <div class="trade-row" style="margin-top:10px; border-top:1px solid #333; padding-top:10px;">
                    <span>Net Credit</span><span class="value profit">${d['net_credit']:.2f}</span>
                </div>
                <div class="trade-row"><span>Max Loss</span><span class="value loss">${d['max_loss']:.0f}</span></div>
            </div>"""
        elif strategy == "straddle" and d.get('valid'):
            warning_html = f'<div class="warning-box">{d["warning"]}</div>' if d.get('warning') else ''
            trade_html = f"""
            <div class="trade-details">
                <div class="trade-row"><span>Buy Call</span><span class="value">${d['call_strike']:.0f} @ ${d['call_price']:.2f}</span></div>
                <div class="trade-row"><span>Buy Put</span><span class="value">${d['put_strike']:.0f} @ ${d['put_price']:.2f}</span></div>
                <div class="trade-row"><span>Verfall</span><span class="value">{d['expiry']}</span></div>
                <div class="trade-row" style="margin-top:10px; border-top:1px solid #333; padding-top:10px;">
                    <span>Gesamtkosten</span><span class="value warning-text">${d['total_cost']:.0f}</span>
                </div>
                <div class="trade-row"><span>Risiko</span><span class="value">{d['risk_pct']:.1f}% vom Konto</span></div>
                <div class="trade-row"><span>Breakeven</span><span class="value">+/-{d['breakeven_move_pct']:.1f}%</span></div>
            </div>
            {warning_html}"""
        else:
            trade_html = f'<div class="trade-details" style="color:#dc3545;">Nicht handelbar: {d.get("reason", "Unbekannt")}</div>'

        # Warnings
        warnings_html = ""
        if c.warnings:
            warnings_html = f'<div class="warning-box">{", ".join(c.warnings)}</div>'

        # Sources
        sources_html = f"""
        <div class="sources">
            <strong>Quellen:</strong>
            <a href="{c.source_url_quote}" target="_blank">Kurs</a>
            <a href="{c.source_url_options}" target="_blank">Optionen</a>
            {'<a href="' + c.source_url_earnings + '" target="_blank">Earnings</a>' if c.earnings_date else ''}
        </div>"""

        return f"""
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
            {trade_html}
            {warnings_html}
            {sources_html}
        </div>"""
