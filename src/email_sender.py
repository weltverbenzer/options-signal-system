"""
E-Mail-Modul
============
Versendet formatierte Trade-Signale per E-Mail.

Unterstuetzt:
- Gmail SMTP
- Formatierte HTML-E-Mails
- Plain-Text Fallback
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from signal_generator import IronCondorSignal


class EmailSender:
    """Versendet E-Mails mit Trade-Signalen"""

    def __init__(self, config: dict):
        """
        Args:
            config: E-Mail-Konfiguration
        """
        email_config = config.get('email', {})
        self.enabled = email_config.get('enabled', False)
        self.recipient = email_config.get('recipient', '')

        smtp_config = email_config.get('smtp', {})
        self.smtp_server = smtp_config.get('server', 'smtp.gmail.com')
        self.smtp_port = smtp_config.get('port', 587)
        self.smtp_username = smtp_config.get('username', '')
        self.smtp_password = smtp_config.get('password', '')

    def send_signal(self, signal: IronCondorSignal) -> bool:
        """
        Versendet ein Signal per E-Mail.

        Args:
            signal: Das zu versendende Signal

        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.enabled:
            print("E-Mail-Versand deaktiviert")
            return False

        if not self._validate_config():
            print("E-Mail-Konfiguration unvollstaendig")
            return False

        try:
            # E-Mail erstellen
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self._create_subject(signal)
            msg['From'] = self.smtp_username
            msg['To'] = self.recipient

            # Plain-Text Version
            text_content = self._create_text_content(signal)
            part1 = MIMEText(text_content, 'plain', 'utf-8')

            # HTML Version
            html_content = self._create_html_content(signal)
            part2 = MIMEText(html_content, 'html', 'utf-8')

            msg.attach(part1)
            msg.attach(part2)

            # Senden
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            print(f"E-Mail erfolgreich an {self.recipient} gesendet")
            return True

        except Exception as e:
            print(f"Fehler beim E-Mail-Versand: {e}")
            return False

    def _validate_config(self) -> bool:
        """Prueft ob die Konfiguration vollstaendig ist"""
        return all([
            self.recipient,
            self.smtp_server,
            self.smtp_username,
            self.smtp_password
        ])

    def _create_subject(self, signal: IronCondorSignal) -> str:
        """Erstellt den E-Mail-Betreff"""
        date_str = signal.generated_at.strftime('%d.%m.%Y')

        if signal.is_valid:
            return f"SIGNAL: {signal.symbol} Iron Condor - {date_str}"
        else:
            return f"KEIN SIGNAL: {signal.symbol} - {date_str}"

    def _create_text_content(self, signal: IronCondorSignal) -> str:
        """Erstellt Plain-Text Inhalt"""
        if not signal.is_valid:
            return f"""
OPTIONS SIGNAL SYSTEM
=====================

Datum: {signal.generated_at.strftime('%d.%m.%Y %H:%M')}
Symbol: {signal.symbol}

KEIN SIGNAL HEUTE
-----------------
Grund: {signal.rejection_reason}

Markt-Kontext:
- SPY Kurs: ${signal.current_price:.2f}
- VIX: {signal.vix:.2f}
- Expected Move: {signal.expected_move:.2f}%

Morgen neuer Versuch!
"""

        return f"""
OPTIONS SIGNAL SYSTEM - IRON CONDOR
====================================

Datum: {signal.generated_at.strftime('%d.%m.%Y %H:%M')}
Symbol: {signal.symbol}
Verfall: {signal.expiry} (0DTE)

TRADE-SETUP
-----------
VERKAUFE:
  PUT  @ Strike ${signal.short_put_strike:.0f}  |  Premium: ${signal.short_put_premium:.2f}
  CALL @ Strike ${signal.short_call_strike:.0f}  |  Premium: ${signal.short_call_premium:.2f}

KAUFE (Absicherung):
  PUT  @ Strike ${signal.long_put_strike:.0f}  |  Premium: ${signal.long_put_premium:.2f}
  CALL @ Strike ${signal.long_call_strike:.0f}  |  Premium: ${signal.long_call_premium:.2f}

TRADE-DETAILS
-------------
Net Credit (Einnahme): ${signal.net_credit:.2f} = ${signal.max_profit:.0f} pro Contract
Max. Verlust: ${signal.max_loss:.0f} pro Contract
Max. Gewinn: ${signal.max_profit:.0f} pro Contract

Breakeven unten: ${signal.breakeven_lower:.2f}
Breakeven oben: ${signal.breakeven_upper:.2f}

EMPFEHLUNG
----------
Anzahl Contracts: {signal.recommended_contracts}
Risiko: ${signal.total_risk:.0f} ({signal.risk_percent:.1f}% vom Konto)

RISIKO-BEWERTUNG
----------------
Risk Level: {signal.risk_level}
Confidence: {signal.confidence}

MARKT-KONTEXT
-------------
SPY Kurs: ${signal.current_price:.2f}
VIX: {signal.vix:.2f}
IV Percentile: {signal.iv_percentile:.1f}%
Expected Move: {signal.expected_move:.2f}%

{self._format_notes(signal.notes)}

---
Options Signal System - Automatisch generiert
"""

    def _create_html_content(self, signal: IronCondorSignal) -> str:
        """Erstellt HTML Inhalt"""
        if not signal.is_valid:
            return self._create_no_signal_html(signal)

        risk_color = {
            'LOW': '#28a745',
            'MEDIUM': '#ffc107',
            'HIGH': '#dc3545'
        }.get(signal.risk_level, '#6c757d')

        notes_html = ""
        if signal.notes:
            notes_html = "<br>".join([f"- {note}" for note in signal.notes])

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1a2e;
            color: #eaeaea;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            padding: 20px;
            text-align: center;
            border-bottom: 3px solid #e94560;
        }}
        .header h1 {{
            margin: 0;
            color: #e94560;
            font-size: 24px;
        }}
        .header .symbol {{
            font-size: 36px;
            font-weight: bold;
            color: #fff;
            margin: 10px 0;
        }}
        .header .date {{
            color: #aaa;
            font-size: 14px;
        }}
        .section {{
            padding: 20px;
            border-bottom: 1px solid #0f3460;
        }}
        .section h2 {{
            color: #e94560;
            margin-top: 0;
            font-size: 16px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .trade-legs {{
            background: #0f3460;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}
        .leg {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #16213e;
        }}
        .leg:last-child {{
            border-bottom: none;
        }}
        .leg .action {{
            font-weight: bold;
        }}
        .leg .sell {{
            color: #e94560;
        }}
        .leg .buy {{
            color: #28a745;
        }}
        .stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}
        .stat-box {{
            background: #0f3460;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .stat-box .label {{
            color: #aaa;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .stat-box .value {{
            font-size: 24px;
            font-weight: bold;
            color: #fff;
            margin-top: 5px;
        }}
        .stat-box .value.profit {{
            color: #28a745;
        }}
        .stat-box .value.loss {{
            color: #e94560;
        }}
        .recommendation {{
            background: #0f3460;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .recommendation .contracts {{
            font-size: 48px;
            font-weight: bold;
            color: #e94560;
        }}
        .recommendation .label {{
            color: #aaa;
        }}
        .risk-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            background: {risk_color};
            color: #fff;
        }}
        .market-context {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            text-align: center;
        }}
        .market-item .value {{
            font-size: 18px;
            font-weight: bold;
            color: #fff;
        }}
        .market-item .label {{
            font-size: 11px;
            color: #aaa;
        }}
        .notes {{
            background: #2a2a4a;
            border-left: 3px solid #ffc107;
            padding: 10px 15px;
            font-size: 13px;
            color: #ffc107;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>IRON CONDOR SIGNAL</h1>
            <div class="symbol">{signal.symbol}</div>
            <div class="date">{signal.generated_at.strftime('%d. %B %Y')} | 0DTE</div>
        </div>

        <div class="section">
            <h2>Trade Setup</h2>
            <div class="trade-legs">
                <div class="leg">
                    <span class="action sell">SELL PUT</span>
                    <span>Strike ${signal.short_put_strike:.0f}</span>
                    <span>${signal.short_put_premium:.2f}</span>
                </div>
                <div class="leg">
                    <span class="action sell">SELL CALL</span>
                    <span>Strike ${signal.short_call_strike:.0f}</span>
                    <span>${signal.short_call_premium:.2f}</span>
                </div>
                <div class="leg">
                    <span class="action buy">BUY PUT</span>
                    <span>Strike ${signal.long_put_strike:.0f}</span>
                    <span>${signal.long_put_premium:.2f}</span>
                </div>
                <div class="leg">
                    <span class="action buy">BUY CALL</span>
                    <span>Strike ${signal.long_call_strike:.0f}</span>
                    <span>${signal.long_call_premium:.2f}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Trade Details</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="label">Net Credit</div>
                    <div class="value profit">${signal.net_credit:.2f}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Max Profit</div>
                    <div class="value profit">${signal.max_profit:.0f}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Max Loss</div>
                    <div class="value loss">${signal.max_loss:.0f}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Breakeven Range</div>
                    <div class="value">${signal.breakeven_lower:.0f} - ${signal.breakeven_upper:.0f}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Empfehlung</h2>
            <div class="recommendation">
                <div class="contracts">{signal.recommended_contracts}</div>
                <div class="label">Contract(s)</div>
                <div style="margin-top: 15px;">
                    <span class="risk-badge">{signal.risk_level} RISK</span>
                </div>
                <div style="margin-top: 10px; color: #aaa;">
                    Risiko: ${signal.total_risk:.0f} ({signal.risk_percent:.1f}% vom Konto)
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Markt-Kontext</h2>
            <div class="market-context">
                <div class="market-item">
                    <div class="value">${signal.current_price:.2f}</div>
                    <div class="label">SPY Kurs</div>
                </div>
                <div class="market-item">
                    <div class="value">{signal.vix:.1f}</div>
                    <div class="label">VIX</div>
                </div>
                <div class="market-item">
                    <div class="value">{signal.iv_percentile:.0f}%</div>
                    <div class="label">IV Percentile</div>
                </div>
                <div class="market-item">
                    <div class="value">{signal.expected_move:.2f}%</div>
                    <div class="label">Expected Move</div>
                </div>
            </div>
        </div>

        {f'<div class="section"><div class="notes">{notes_html}</div></div>' if signal.notes else ''}

        <div class="footer">
            Options Signal System | Automatisch generiert am {signal.generated_at.strftime('%d.%m.%Y %H:%M')}
        </div>
    </div>
</body>
</html>
"""

    def _create_no_signal_html(self, signal: IronCondorSignal) -> str:
        """Erstellt HTML fuer 'Kein Signal' E-Mail"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1a1a2e;
            color: #eaeaea;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        .header {{
            background: #2d2d44;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            color: #ffc107;
            font-size: 28px;
        }}
        .content {{
            padding: 30px;
            text-align: center;
        }}
        .reason {{
            background: #0f3460;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            font-size: 16px;
        }}
        .market-info {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }}
        .market-item {{
            background: #0f3460;
            border-radius: 8px;
            padding: 15px;
        }}
        .market-item .value {{
            font-size: 20px;
            font-weight: bold;
            color: #fff;
        }}
        .market-item .label {{
            font-size: 12px;
            color: #aaa;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>KEIN SIGNAL HEUTE</h1>
        </div>

        <div class="content">
            <p>{signal.symbol} | {signal.generated_at.strftime('%d. %B %Y')}</p>

            <div class="reason">
                <strong>Grund:</strong><br>
                {signal.rejection_reason}
            </div>

            <p style="color: #aaa;">Die Marktbedingungen sind heute nicht optimal fuer einen Iron Condor Trade.</p>

            <div class="market-info">
                <div class="market-item">
                    <div class="value">${signal.current_price:.2f}</div>
                    <div class="label">SPY Kurs</div>
                </div>
                <div class="market-item">
                    <div class="value">{signal.vix:.1f}</div>
                    <div class="label">VIX</div>
                </div>
                <div class="market-item">
                    <div class="value">{signal.expected_move:.2f}%</div>
                    <div class="label">Expected Move</div>
                </div>
            </div>

            <p style="margin-top: 30px; color: #28a745;">Morgen neuer Versuch!</p>
        </div>

        <div class="footer">
            Options Signal System | {signal.generated_at.strftime('%d.%m.%Y %H:%M')}
        </div>
    </div>
</body>
</html>
"""

    def _format_notes(self, notes: list) -> str:
        """Formatiert Notes fuer Plain-Text"""
        if not notes:
            return ""

        formatted = "HINWEISE\n--------\n"
        for note in notes:
            formatted += f"- {note}\n"
        return formatted


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("E-Mail-Modul Test")
    print("=" * 60)
    print()
    print("Um das E-Mail-Modul zu testen, konfiguriere config.yaml mit")
    print("deinen SMTP-Zugangsdaten und fuehre main.py aus.")
    print()
    print("Fuer Gmail:")
    print("1. 2-Faktor-Authentifizierung aktivieren")
    print("2. App-Password erstellen: https://myaccount.google.com/apppasswords")
    print("3. App-Password in config.yaml eintragen")
