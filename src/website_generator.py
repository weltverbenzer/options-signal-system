"""
Webseiten-Generator
===================
Generiert eine statische HTML-Seite fuer GitHub Pages.

Features:
- Aktuelles Signal anzeigen
- Historische Signale (letzte 7 Tage)
- Mobile-responsive Design
- Dunkles Theme
"""

import os
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from signal_generator import IronCondorSignal


class WebsiteGenerator:
    """Generiert eine statische Webseite mit Signalen"""

    def __init__(self, config: dict):
        """
        Args:
            config: Website-Konfiguration
        """
        website_config = config.get('website', {})
        self.enabled = website_config.get('enabled', False)
        self.output_dir = website_config.get('output_dir', 'docs')
        self.title = website_config.get('title', 'Options Signal System')

        # Stelle sicher dass Output-Verzeichnis existiert
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def generate(self, current_signal: IronCondorSignal,
                 history: Optional[List[dict]] = None) -> bool:
        """
        Generiert die Webseite mit aktuellem Signal und Historie.

        Args:
            current_signal: Aktuelles Signal
            history: Liste historischer Signale (optional)

        Returns:
            True wenn erfolgreich
        """
        if not self.enabled:
            print("Webseiten-Generierung deaktiviert")
            return False

        try:
            # HTML generieren
            html = self._generate_html(current_signal, history or [])

            # Datei schreiben
            output_path = Path(self.output_dir) / 'index.html'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            print(f"Webseite generiert: {output_path}")

            # Signal zur Historie hinzufuegen
            self._save_to_history(current_signal)

            return True

        except Exception as e:
            print(f"Fehler bei Webseiten-Generierung: {e}")
            return False

    def _save_to_history(self, signal: IronCondorSignal):
        """Speichert Signal in Historie-Datei"""
        history_path = Path(self.output_dir) / 'history.json'

        # Bestehende Historie laden
        history = []
        if history_path.exists():
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []

        # Neues Signal hinzufuegen
        history.insert(0, signal.to_dict())

        # Nur letzte 30 Tage behalten
        history = history[:30]

        # Speichern
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, default=str)

    def load_history(self) -> List[dict]:
        """Laedt Historie aus Datei"""
        history_path = Path(self.output_dir) / 'history.json'

        if not history_path.exists():
            return []

        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _generate_html(self, signal: IronCondorSignal,
                       history: List[dict]) -> str:
        """Generiert das komplette HTML"""

        # Signal-Karte
        if signal.is_valid:
            signal_card = self._generate_valid_signal_card(signal)
        else:
            signal_card = self._generate_no_signal_card(signal)

        # Historie-Tabelle
        history_html = self._generate_history_table(history)

        return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #0f3460;
            margin-bottom: 30px;
        }}

        header h1 {{
            color: #e94560;
            font-size: 2rem;
            margin-bottom: 10px;
        }}

        header .subtitle {{
            color: #888;
            font-size: 0.9rem;
        }}

        .signal-card {{
            background: #16213e;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}

        .signal-header {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            padding: 25px;
            text-align: center;
            border-bottom: 3px solid #e94560;
        }}

        .signal-header .status {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #e94560;
            margin-bottom: 10px;
        }}

        .signal-header .symbol {{
            font-size: 3rem;
            font-weight: bold;
            color: #fff;
        }}

        .signal-header .date {{
            color: #888;
            margin-top: 10px;
        }}

        .signal-body {{
            padding: 25px;
        }}

        .trade-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}

        .trade-leg {{
            background: #0f3460;
            border-radius: 10px;
            padding: 15px;
        }}

        .trade-leg .action {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}

        .trade-leg .action.sell {{
            color: #e94560;
        }}

        .trade-leg .action.buy {{
            color: #28a745;
        }}

        .trade-leg .strike {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #fff;
        }}

        .trade-leg .premium {{
            color: #888;
            font-size: 0.9rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}

        .stat-box {{
            background: #0f3460;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}

        .stat-box .label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 5px;
        }}

        .stat-box .value {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #fff;
        }}

        .stat-box .value.profit {{
            color: #28a745;
        }}

        .stat-box .value.loss {{
            color: #e94560;
        }}

        .recommendation {{
            background: linear-gradient(135deg, #0f3460 0%, #1a1a3e 100%);
            border-radius: 10px;
            padding: 25px;
            text-align: center;
        }}

        .recommendation .contracts {{
            font-size: 4rem;
            font-weight: bold;
            color: #e94560;
        }}

        .recommendation .label {{
            color: #888;
            margin-bottom: 15px;
        }}

        .risk-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 0.85rem;
        }}

        .risk-badge.low {{
            background: #28a745;
            color: #fff;
        }}

        .risk-badge.medium {{
            background: #ffc107;
            color: #000;
        }}

        .risk-badge.high {{
            background: #e94560;
            color: #fff;
        }}

        .no-signal {{
            text-align: center;
            padding: 50px 20px;
        }}

        .no-signal h2 {{
            color: #ffc107;
            font-size: 2rem;
            margin-bottom: 20px;
        }}

        .no-signal .reason {{
            background: #0f3460;
            border-radius: 10px;
            padding: 20px;
            max-width: 400px;
            margin: 0 auto 20px;
        }}

        .history-section {{
            background: #16213e;
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
        }}

        .history-section h2 {{
            color: #e94560;
            margin-bottom: 20px;
            font-size: 1.2rem;
        }}

        .history-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .history-table th,
        .history-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #0f3460;
        }}

        .history-table th {{
            color: #888;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .history-table .signal-status {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.75rem;
        }}

        .history-table .signal-status.valid {{
            background: #28a745;
            color: #fff;
        }}

        .history-table .signal-status.invalid {{
            background: #6c757d;
            color: #fff;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.8rem;
        }}

        @media (max-width: 600px) {{
            .signal-header .symbol {{
                font-size: 2rem;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}

            .recommendation .contracts {{
                font-size: 3rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p class="subtitle">Automatisierte 0DTE Iron Condor Signale</p>
        </header>

        {signal_card}

        {history_html}

        <footer>
            <p>Zuletzt aktualisiert: {datetime.now().strftime('%d.%m.%Y %H:%M')} MEZ</p>
            <p style="margin-top: 10px;">Options Signal System | Automatisch generiert</p>
        </footer>
    </div>
</body>
</html>"""

    def _generate_valid_signal_card(self, signal: IronCondorSignal) -> str:
        """Generiert Karte fuer gueltiges Signal"""
        risk_class = signal.risk_level.lower()

        return f"""
        <div class="signal-card">
            <div class="signal-header">
                <div class="status">Iron Condor Signal</div>
                <div class="symbol">{signal.symbol}</div>
                <div class="date">{signal.generated_at.strftime('%d. %B %Y')} | 0DTE</div>
            </div>

            <div class="signal-body">
                <div class="trade-grid">
                    <div class="trade-leg">
                        <div class="action sell">Sell Put</div>
                        <div class="strike">${signal.short_put_strike:.0f}</div>
                        <div class="premium">@ ${signal.short_put_premium:.2f}</div>
                    </div>
                    <div class="trade-leg">
                        <div class="action sell">Sell Call</div>
                        <div class="strike">${signal.short_call_strike:.0f}</div>
                        <div class="premium">@ ${signal.short_call_premium:.2f}</div>
                    </div>
                    <div class="trade-leg">
                        <div class="action buy">Buy Put</div>
                        <div class="strike">${signal.long_put_strike:.0f}</div>
                        <div class="premium">@ ${signal.long_put_premium:.2f}</div>
                    </div>
                    <div class="trade-leg">
                        <div class="action buy">Buy Call</div>
                        <div class="strike">${signal.long_call_strike:.0f}</div>
                        <div class="premium">@ ${signal.long_call_premium:.2f}</div>
                    </div>
                </div>

                <div class="stats-grid">
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
                        <div class="label">SPY Kurs</div>
                        <div class="value">${signal.current_price:.2f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="label">VIX</div>
                        <div class="value">{signal.vix:.1f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="label">Breakeven</div>
                        <div class="value">${signal.breakeven_lower:.0f}-${signal.breakeven_upper:.0f}</div>
                    </div>
                </div>

                <div class="recommendation">
                    <div class="label">Empfehlung</div>
                    <div class="contracts">{signal.recommended_contracts}</div>
                    <div class="label">Contract(s)</div>
                    <div style="margin-top: 15px;">
                        <span class="risk-badge {risk_class}">{signal.risk_level} RISK</span>
                    </div>
                    <div style="margin-top: 10px; color: #888; font-size: 0.9rem;">
                        Risiko: ${signal.total_risk:.0f} ({signal.risk_percent:.1f}% vom Konto)
                    </div>
                </div>
            </div>
        </div>"""

    def _generate_no_signal_card(self, signal: IronCondorSignal) -> str:
        """Generiert Karte fuer 'Kein Signal'"""
        return f"""
        <div class="signal-card">
            <div class="signal-body no-signal">
                <h2>Kein Signal heute</h2>
                <div class="reason">
                    <strong>Grund:</strong><br>
                    {signal.rejection_reason}
                </div>
                <div class="stats-grid" style="max-width: 400px; margin: 0 auto;">
                    <div class="stat-box">
                        <div class="label">SPY</div>
                        <div class="value">${signal.current_price:.2f}</div>
                    </div>
                    <div class="stat-box">
                        <div class="label">VIX</div>
                        <div class="value">{signal.vix:.1f}</div>
                    </div>
                </div>
                <p style="margin-top: 20px; color: #28a745;">Morgen neuer Versuch!</p>
            </div>
        </div>"""

    def _generate_history_table(self, history: List[dict]) -> str:
        """Generiert die Historie-Tabelle"""
        if not history:
            return ""

        rows = ""
        for item in history[:7]:  # Letzte 7 Tage
            date = item.get('generated_at', '')[:10]
            is_valid = item.get('is_valid', False)
            status_class = 'valid' if is_valid else 'invalid'
            status_text = 'Signal' if is_valid else 'Kein Signal'

            if is_valid:
                details = f"${item.get('short_put_strike', 0):.0f}/${item.get('short_call_strike', 0):.0f}"
                profit = f"${item.get('max_profit', 0):.0f}"
            else:
                details = item.get('rejection_reason', '-')[:30]
                profit = '-'

            rows += f"""
                <tr>
                    <td>{date}</td>
                    <td><span class="signal-status {status_class}">{status_text}</span></td>
                    <td>{details}</td>
                    <td>{profit}</td>
                </tr>"""

        return f"""
        <div class="history-section">
            <h2>Letzte Signale</h2>
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Datum</th>
                        <th>Status</th>
                        <th>Details</th>
                        <th>Max Profit</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from datetime import datetime

    print("Website-Generator Test")
    print("=" * 60)

    # Test-Konfiguration
    config = {
        'website': {
            'enabled': True,
            'output_dir': 'docs',
            'title': 'Options Signal System - Test'
        }
    }

    # Dummy-Signal erstellen
    test_signal = IronCondorSignal(
        symbol='SPY',
        expiry='2026-01-23',
        generated_at=datetime.now(),
        short_put_strike=480,
        long_put_strike=478,
        short_call_strike=495,
        long_call_strike=497,
        short_put_premium=0.45,
        long_put_premium=0.20,
        short_call_premium=0.40,
        long_call_premium=0.18,
        net_credit=0.47,
        max_loss=153,
        max_profit=47,
        breakeven_lower=479.53,
        breakeven_upper=495.47,
        recommended_contracts=1,
        total_risk=153,
        risk_percent=3.1,
        current_price=487.50,
        vix=16.5,
        expected_move=1.2,
        iv_percentile=45,
        risk_level='MEDIUM',
        confidence='HIGH',
        notes=['Test-Signal'],
        is_valid=True,
        rejection_reason=None
    )

    generator = WebsiteGenerator(config)
    success = generator.generate(test_signal)

    if success:
        print(f"Test-Webseite wurde in '{config['website']['output_dir']}/index.html' erstellt")
    else:
        print("Fehler bei der Webseiten-Generierung")
