"""
E-Mail-Sender v2
================
Versendet E-Mails mit Kandidaten-Auswahl fuer beide Strategien.
Inkl. Begruendungen und Trade-Details.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List


class EmailSenderV2:
    """Versendet E-Mails mit Kandidaten-Listen"""

    def __init__(self, config: dict):
        email_config = config.get('email', {})
        self.enabled = email_config.get('enabled', False)
        self.recipient = email_config.get('recipient', '')

        smtp_config = email_config.get('smtp', {})
        self.smtp_server = smtp_config.get('server', '')
        self.smtp_port = smtp_config.get('port', 587)
        self.smtp_username = smtp_config.get('username', '')
        self.smtp_password = smtp_config.get('password', '')

    def send_candidates(self, results: Dict) -> bool:
        """Versendet Kandidaten-E-Mail"""
        if not self.enabled or not self._validate_config():
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Options Signale - {datetime.now().strftime('%d.%m.%Y')}"
            msg['From'] = self.smtp_username
            msg['To'] = self.recipient

            text = self._create_text(results)
            html = self._create_html(results)

            msg.attach(MIMEText(text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html, 'html', 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"E-Mail Fehler: {e}")
            return False

    def _validate_config(self) -> bool:
        return all([self.recipient, self.smtp_server, self.smtp_username, self.smtp_password])

    def _create_text(self, results: Dict) -> str:
        """Plain-Text Version"""
        lines = [
            "=" * 60,
            "OPTIONS SIGNAL SYSTEM",
            f"Generiert: {results['generated_at'].strftime('%d.%m.%Y %H:%M')}",
            "=" * 60,
            "",
            "IRON CONDOR KANDIDATEN",
            "(Ruhige Aktien ohne Events - Seitwaertsbewegung erwartet)",
            "-" * 40,
        ]

        for item in results.get('iron_condor', []):
            c = item['candidate']
            d = item['details']
            lines.append(f"\n{c.symbol} ({c.company_name})")
            lines.append(f"  Kurs: ${c.current_price:.2f} | Score: {c.iron_condor_score:.0f}/100")
            lines.append(f"  WARUM: {', '.join(c.reasons)}")
            if d.get('valid'):
                lines.append(f"  TRADE: Sell ${d['short_put']:.0f}P/${d['short_call']:.0f}C")
                lines.append(f"         Buy ${d['long_put']:.0f}P/${d['long_call']:.0f}C")
                lines.append(f"  Credit: ${d['net_credit']:.2f} | Max Loss: ${d['max_loss']:.0f}")
            else:
                lines.append(f"  NICHT HANDELBAR: {d.get('reason', 'Unbekannt')}")
            if c.warnings:
                lines.append(f"  WARNUNG: {', '.join(c.warnings)}")
            lines.append(f"  QUELLEN: {c.source_url_quote}")
            lines.append(f"           {c.source_url_options}")

        lines.extend([
            "",
            "=" * 60,
            "STRADDLE KANDIDATEN",
            "(Aktien mit Earnings/Events - Grosse Bewegung erwartet)",
            "-" * 40,
        ])

        for item in results.get('straddle', []):
            c = item['candidate']
            d = item['details']
            lines.append(f"\n{c.symbol} ({c.company_name})")
            lines.append(f"  Kurs: ${c.current_price:.2f} | Score: {c.straddle_score:.0f}/100")
            if c.earnings_date:
                lines.append(f"  EARNINGS: {c.earnings_date} (in {c.days_to_earnings} Tagen)")
            lines.append(f"  WARUM: {', '.join(c.reasons)}")
            if d.get('valid'):
                lines.append(f"  TRADE: Buy ${d['call_strike']:.0f}C + ${d['put_strike']:.0f}P")
                lines.append(f"  Verfall: {d['expiry']}")
                lines.append(f"  Kosten: ${d['total_cost']:.0f} | Breakeven: +/-{d['breakeven_move_pct']:.1f}%")
            else:
                lines.append(f"  NICHT HANDELBAR: {d.get('reason', 'Unbekannt')}")
            if c.warnings:
                lines.append(f"  WARNUNG: {', '.join(c.warnings)}")
            lines.append(f"  QUELLEN: {c.source_url_quote}")
            lines.append(f"           {c.source_url_options}")
            if c.earnings_date:
                lines.append(f"           {c.source_url_earnings}")

        lines.extend([
            "",
            "=" * 60,
            "WICHTIG: Dies sind Vorschlaege - DU entscheidest!",
            "Pruefe Liquiditaet (Bid/Ask) vor dem Trade.",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _create_html(self, results: Dict) -> str:
        """HTML Version"""
        ic_cards = ""
        for item in results.get('iron_condor', []):
            c = item['candidate']
            d = item['details']
            ic_cards += self._create_candidate_card(c, d, "iron_condor")

        st_cards = ""
        for item in results.get('straddle', []):
            c = item['candidate']
            d = item['details']
            st_cards += self._create_candidate_card(c, d, "straddle")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eaeaea;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            border-bottom: 2px solid #e94560;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #e94560;
            margin: 0;
        }}
        .header .date {{
            color: #888;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #e94560;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        .section .subtitle {{
            color: #888;
            font-size: 14px;
            margin-top: -10px;
            margin-bottom: 20px;
        }}
        .card {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #28a745;
        }}
        .card.warning {{
            border-left-color: #ffc107;
        }}
        .card.invalid {{
            border-left-color: #dc3545;
            opacity: 0.7;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
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
        }}
        .price {{
            color: #28a745;
            font-size: 18px;
            margin: 10px 0;
        }}
        .reasons {{
            background: #0f3460;
            padding: 10px 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .reasons-label {{
            color: #e94560;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .trade-details {{
            background: #0a1628;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        }}
        .trade-row {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #16213e;
        }}
        .trade-row:last-child {{
            border-bottom: none;
        }}
        .earnings-badge {{
            background: #e94560;
            color: #fff;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 12px;
            margin-left: 10px;
        }}
        .warning-box {{
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid #ffc107;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            color: #ffc107;
            font-size: 13px;
        }}
        .sources {{
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #333;
            font-size: 12px;
        }}
        .sources a {{
            color: #4dabf7;
            text-decoration: none;
            margin-right: 15px;
        }}
        .sources a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #333;
            margin-top: 30px;
        }}
        .disclaimer {{
            background: #2a2a4a;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Options Signal System</h1>
            <div class="date">{results['generated_at'].strftime('%d. %B %Y - %H:%M')} Uhr</div>
        </div>

        <div class="section">
            <h2>Iron Condor Kandidaten</h2>
            <p class="subtitle">Ruhige Aktien ohne Events - Seitwaertsbewegung erwartet</p>
            {ic_cards if ic_cards else '<p style="color:#888;">Keine geeigneten Kandidaten gefunden</p>'}
        </div>

        <div class="section">
            <h2>Straddle Kandidaten</h2>
            <p class="subtitle">Aktien mit Earnings/Events - Grosse Bewegung erwartet</p>
            {st_cards if st_cards else '<p style="color:#888;">Keine Earnings/Events heute</p>'}
        </div>

        <div class="disclaimer">
            <strong>WICHTIG:</strong> Dies sind Vorschlaege zur Auswahl - DU entscheidest!<br>
            Pruefe Bid/Ask Spreads vor dem Trade. Nicht alle Optionen sind immer handelbar.
        </div>

        <div class="footer">
            Options Signal System | Automatisch generiert
        </div>
    </div>
</body>
</html>
"""

    def _create_candidate_card(self, c, d, strategy: str) -> str:
        """Erstellt HTML-Card fuer einen Kandidaten"""
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

        warnings_html = ""
        if c.warnings:
            warnings_html = f'<div class="warning-box">{", ".join(c.warnings)}</div>'

        if strategy == "iron_condor" and d.get('valid'):
            trade_html = f"""
            <div class="trade-details">
                <div class="trade-row">
                    <span>Sell Put</span>
                    <span>${d['short_put']:.0f}</span>
                </div>
                <div class="trade-row">
                    <span>Buy Put</span>
                    <span>${d['long_put']:.0f}</span>
                </div>
                <div class="trade-row">
                    <span>Sell Call</span>
                    <span>${d['short_call']:.0f}</span>
                </div>
                <div class="trade-row">
                    <span>Buy Call</span>
                    <span>${d['long_call']:.0f}</span>
                </div>
                <div class="trade-row" style="margin-top:10px; padding-top:10px; border-top:1px solid #333;">
                    <span>Net Credit</span>
                    <span style="color:#28a745;">${d['net_credit']:.2f}</span>
                </div>
                <div class="trade-row">
                    <span>Max Loss</span>
                    <span style="color:#dc3545;">${d['max_loss']:.0f}</span>
                </div>
            </div>
            """
        elif strategy == "straddle" and d.get('valid'):
            trade_html = f"""
            <div class="trade-details">
                <div class="trade-row">
                    <span>Buy Call</span>
                    <span>${d['call_strike']:.0f} @ ${d['call_price']:.2f}</span>
                </div>
                <div class="trade-row">
                    <span>Buy Put</span>
                    <span>${d['put_strike']:.0f} @ ${d['put_price']:.2f}</span>
                </div>
                <div class="trade-row">
                    <span>Verfall</span>
                    <span>{d['expiry']}</span>
                </div>
                <div class="trade-row" style="margin-top:10px; padding-top:10px; border-top:1px solid #333;">
                    <span>Gesamtkosten</span>
                    <span style="color:#ffc107;">${d['total_cost']:.0f}</span>
                </div>
                <div class="trade-row">
                    <span>Breakeven</span>
                    <span>+/-{d['breakeven_move_pct']:.1f}%</span>
                </div>
            </div>
            """
        else:
            trade_html = f'<div class="trade-details" style="color:#dc3545;">Nicht handelbar: {d.get("reason", "Unbekannt")}</div>'

        score = c.iron_condor_score if strategy == "iron_condor" else c.straddle_score

        # Detail-Link zur Website
        detail_url = f"https://weltverbenzer.github.io/options-signal-system/{c.symbol.lower()}.html"

        # Quellen-Links
        sources_html = f"""
        <div class="sources">
            <strong>Quellen:</strong>
            <a href="{c.source_url_quote}" target="_blank">Kurs</a>
            <a href="{c.source_url_options}" target="_blank">Optionen</a>
            {'<a href="' + c.source_url_earnings + '" target="_blank">Earnings</a>' if c.earnings_date else ''}
        </div>
        """

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
            <a href="{detail_url}" target="_blank" style="display:inline-block; margin-top:15px; padding:10px 20px; background:#e94560; color:#fff; text-decoration:none; border-radius:5px; font-weight:bold;">
                Details, News & Chart anzeigen
            </a>
            {sources_html}
        </div>
        """
