"""
E-Mail-Sender v3
================
Versendet E-Mails mit Movement-Kandidaten.
Inkl. News-Sentiment und Expected Move.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List


class EmailSenderV3:
    """Versendet E-Mails mit Movement-Kandidaten"""

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
            msg['Subject'] = f"Movement Signale - {datetime.now().strftime('%d.%m.%Y')}"
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
            "MOVEMENT SIGNAL SYSTEM",
            f"Generiert: {results['generated_at'].strftime('%d.%m.%Y %H:%M')}",
            "=" * 60,
            "",
            "TOP BEWEGUNGS-KANDIDATEN",
            "(Erwartete Volatilität in den nächsten Tagen)",
            "-" * 40,
        ]

        for i, c in enumerate(results.get('candidates', []), 1):
            lines.append(f"\n#{i} {c.symbol} ({c.company_name})")
            lines.append(f"  Kurs: ${c.current_price:.2f} | Score: {c.movement_score:.0f}/100")
            lines.append(f"  News: {c.news_count} Artikel | Sentiment: {c.sentiment_label}")
            if c.has_earnings_soon:
                lines.append(f"  EARNINGS: {c.earnings_date} (in {c.days_to_earnings} Tagen)")
            lines.append(f"  WARUM: {', '.join(c.reasons)}")
            lines.append(f"  DETAILS: https://weltverbenzer.github.io/options-signal-system/{c.symbol.lower()}.html")

        lines.extend([
            "",
            "=" * 60,
            "WICHTIG: Dies sind Vorschläge - DU entscheidest!",
            "Sentiment-Analyse basiert auf News-Keywords.",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _create_html(self, results: Dict) -> str:
        """HTML Version"""
        cards = ""
        for i, c in enumerate(results.get('candidates', []), 1):
            cards += self._create_candidate_card(c, i)

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
        }}
        .price {{
            color: #28a745;
            font-size: 18px;
            margin: 10px 0;
        }}
        .metrics {{
            display: flex;
            gap: 15px;
            margin: 15px 0;
        }}
        .metric {{
            background: #0a1628;
            padding: 10px;
            border-radius: 5px;
        }}
        .metric-label {{
            color: #888;
            font-size: 12px;
        }}
        .metric-value {{
            color: #fff;
            font-size: 16px;
            font-weight: bold;
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
            <h1>Movement Signal System</h1>
            <div class="date">{results['generated_at'].strftime('%d. %B %Y - %H:%M')} Uhr</div>
        </div>

        <div class="section">
            <h2>Top Movement Kandidaten</h2>
            <p class="subtitle">Aktien mit erwarteter Volatilität in den nächsten Tagen</p>
            {cards if cards else '<p style="color:#888;">Keine Kandidaten gefunden</p>'}
        </div>

        <div class="disclaimer">
            <strong>WICHTIG:</strong> Dies sind Vorschläge - DU entscheidest!<br>
            Sentiment-Analyse basiert auf News-Keywords und ist nicht perfekt.
        </div>

        <div class="footer">
            Movement Signal System | Automatisch generiert
        </div>
    </div>
</body>
</html>
"""

    def _create_candidate_card(self, c, rank: int) -> str:
        """Erstellt HTML-Card für einen Kandidaten"""
        card_class = "card"
        if c.movement_score >= 70:
            card_class += " high-score"

        earnings_badge = ""
        if c.has_earnings_soon and c.days_to_earnings is not None:
            if c.days_to_earnings == 0:
                earnings_badge = '<span class="earnings-badge">EARNINGS HEUTE</span>'
            elif c.days_to_earnings == 1:
                earnings_badge = '<span class="earnings-badge">Earnings morgen</span>'
            else:
                earnings_badge = f'<span class="earnings-badge">Earnings in {c.days_to_earnings}T</span>'

        # Sentiment Badge
        if c.sentiment_score > 0:
            sentiment_class = "positive"
        elif c.sentiment_score < 0:
            sentiment_class = "negative"
        else:
            sentiment_class = "neutral"

        # Detail-Link
        detail_url = f"https://weltverbenzer.github.io/options-signal-system/{c.symbol.lower()}.html"

        return f"""
        <div class="{card_class}">
            <div class="card-header">
                <div>
                    <span class="rank">#{rank}</span>
                    <span class="symbol">{c.symbol}</span>
                    {earnings_badge}
                    <div class="company">{c.company_name}</div>
                </div>
                <div class="score">Score: {c.movement_score:.0f}/100</div>
            </div>
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

            <div class="reasons">
                <div class="reasons-label">Warum dieser Kandidat?</div>
                {', '.join(c.reasons)}
            </div>

            <a href="{detail_url}" target="_blank" style="display:inline-block; margin-top:15px; padding:10px 20px; background:#e94560; color:#fff; text-decoration:none; border-radius:5px; font-weight:bold;">
                Details, News & Chart anzeigen
            </a>
        </div>
        """
