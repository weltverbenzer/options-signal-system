#!/usr/bin/env python3
"""
Options Signal System - Movement Screener v3
=============================================
Findet Aktien mit hohem Bewegungspotential.
Analysiert News-Sentiment und Expected Move.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from movement_screener import MovementScreener
from email_sender_v3 import EmailSenderV3
from website_generator_v3 import WebsiteGeneratorV3


def load_config(config_path: str = None) -> dict:
    """Lädt Konfiguration aus Datei oder Umgebungsvariablen"""
    possible_paths = [
        config_path,
        'config.yaml',
        Path(__file__).parent.parent / 'config.yaml',
    ]

    for path in possible_paths:
        if path and Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    # Fallback: Umgebungsvariablen
    return {
        'account': {
            'capital': int(os.getenv('CAPITAL', 5000)),
            'max_risk_percent': float(os.getenv('MAX_RISK_PERCENT', 2))
        },
        'email': {
            'enabled': os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
            'recipient': os.getenv('EMAIL_RECIPIENT', ''),
            'smtp': {
                'server': os.getenv('SMTP_SERVER', ''),
                'port': int(os.getenv('SMTP_PORT', 587)),
                'username': os.getenv('SMTP_USERNAME', ''),
                'password': os.getenv('SMTP_PASSWORD', '')
            }
        },
        'website': {
            'enabled': os.getenv('WEBSITE_ENABLED', 'true').lower() == 'true',
            'output_dir': os.getenv('WEBSITE_OUTPUT_DIR', 'docs'),
            'title': os.getenv('WEBSITE_TITLE', 'Movement Signal System')
        }
    }


def run_screening() -> dict:
    """Führt das Movement-Screening durch"""
    print("=" * 60)
    print("MOVEMENT SIGNAL SYSTEM v3")
    print(f"Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)

    # Screening
    screener = MovementScreener()
    candidates = screener.screen_all()

    return {
        'candidates': candidates[:20],  # Top 20
        'generated_at': datetime.now()
    }


def main():
    parser = argparse.ArgumentParser(description='Movement Signal System v3')
    parser.add_argument('--config', '-c', help='Pfad zur Konfigurationsdatei')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Nur anzeigen')

    args = parser.parse_args()
    config = load_config(args.config)

    # Screening durchführen
    results = run_screening()

    # Ausgabe
    print("\n" + "=" * 60)
    print("TOP MOVEMENT KANDIDATEN")
    print("(Erwartete Bewegung in den nächsten Tagen)")
    print("=" * 60)

    for i, c in enumerate(results['candidates'], 1):
        print(f"\n#{i} {c.symbol} ({c.company_name})")
        print(f"  Kurs: ${c.current_price:.2f} | Movement Score: {c.movement_score:.0f}/100")
        print(f"  Expected Move: {c.expected_move_pct:.1f}% | IV Percentile: {c.iv_percentile:.0f}%")
        print(f"  News: {c.news_count} ({c.sentiment_label})")
        if c.has_earnings_soon:
            print(f"  Earnings: {c.earnings_date} (in {c.days_to_earnings} Tagen)")
        print(f"  Gründe: {', '.join(c.reasons)}")

    if args.dry_run:
        print("\n[DRY-RUN] Keine E-Mail/Website-Generierung")
        return True

    # Website generieren
    print("\n[1/2] Generiere Website...")
    website_gen = WebsiteGeneratorV3(config)
    if website_gen.enabled:
        success = website_gen.generate(results)
        print(f"  Website: {'Generiert' if success else 'Fehler'}")
    else:
        print("  Website deaktiviert")

    # E-Mail senden
    print("\n[2/2] Sende E-Mail...")
    email_sender = EmailSenderV3(config)
    if email_sender.enabled:
        success = email_sender.send_candidates(results)
        print(f"  E-Mail: {'Gesendet' if success else 'Fehler'}")
    else:
        print("  E-Mail deaktiviert")

    print("\n" + "=" * 60)
    print("FERTIG!")
    print("=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
