#!/usr/bin/env python3
"""
Options Signal System - Hauptprogramm
=====================================
Fuehrt den taeglichen Scan durch und versendet Signale.

Aufruf:
    python main.py              # Normaler Durchlauf
    python main.py --test       # Test-Modus (keine E-Mails)
    python main.py --dry-run    # Zeigt Signal ohne Versand
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

import yaml

# Pfad fuer lokale Imports
sys.path.insert(0, str(Path(__file__).parent))

from market_data import MarketDataFetcher
from signal_generator import SignalGenerator
from email_sender import EmailSender
from website_generator import WebsiteGenerator


def load_config(config_path: str = None) -> dict:
    """
    Laedt die Konfiguration aus YAML-Datei.

    Sucht in folgender Reihenfolge:
    1. Angegebener Pfad
    2. config.yaml im aktuellen Verzeichnis
    3. config.yaml im Projekt-Root
    4. Umgebungsvariablen

    Args:
        config_path: Optionaler Pfad zur Config-Datei

    Returns:
        Konfiguration als Dictionary
    """
    # Moegliche Config-Pfade
    possible_paths = [
        config_path,
        'config.yaml',
        Path(__file__).parent.parent / 'config.yaml',
        Path.home() / '.options-signal' / 'config.yaml'
    ]

    for path in possible_paths:
        if path and Path(path).exists():
            print(f"Lade Konfiguration von: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

    # Fallback: Umgebungsvariablen
    print("Keine config.yaml gefunden, nutze Umgebungsvariablen...")
    return {
        'account': {
            'capital': int(os.getenv('CAPITAL', 5000)),
            'max_risk_percent': float(os.getenv('MAX_RISK_PERCENT', 2))
        },
        'signal': {
            'symbol': os.getenv('SYMBOL', 'SPY'),
            'short_delta': float(os.getenv('SHORT_DELTA', 0.12)),
            'wing_width': float(os.getenv('WING_WIDTH', 2)),
            'min_vix': float(os.getenv('MIN_VIX', 12)),
            'max_vix': float(os.getenv('MAX_VIX', 25)),
            'min_iv_percentile': float(os.getenv('MIN_IV_PERCENTILE', 20))
        },
        'email': {
            'enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
            'recipient': os.getenv('EMAIL_RECIPIENT', ''),
            'smtp': {
                'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'port': int(os.getenv('SMTP_PORT', 587)),
                'username': os.getenv('SMTP_USERNAME', ''),
                'password': os.getenv('SMTP_PASSWORD', '')
            }
        },
        'website': {
            'enabled': os.getenv('WEBSITE_ENABLED', 'true').lower() == 'true',
            'output_dir': os.getenv('WEBSITE_OUTPUT_DIR', 'docs'),
            'title': os.getenv('WEBSITE_TITLE', 'Options Signal System')
        }
    }


def run_signal_generation(config: dict, dry_run: bool = False,
                          test_mode: bool = False) -> bool:
    """
    Fuehrt die Signal-Generierung durch.

    Args:
        config: Konfiguration
        dry_run: Wenn True, kein Versand
        test_mode: Wenn True, nutze Test-Daten

    Returns:
        True wenn erfolgreich
    """
    print("=" * 60)
    print("OPTIONS SIGNAL SYSTEM")
    print(f"Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)
    print()

    try:
        # 1. Marktdaten abrufen
        print("[1/4] Rufe Marktdaten ab...")
        symbol = config.get('signal', {}).get('symbol', 'SPY')
        fetcher = MarketDataFetcher(symbol)
        snapshot = fetcher.get_market_snapshot()

        print(f"      {symbol}: ${snapshot.price:.2f}")
        print(f"      VIX: {snapshot.vix:.2f}")
        print(f"      IV Percentile: {snapshot.iv_percentile:.1f}%")
        print(f"      Expected Move: {snapshot.expected_move:.2f}%")
        print()

        # 2. Signal generieren
        print("[2/4] Generiere Signal...")
        generator = SignalGenerator(config)
        signal = generator.generate_signal(snapshot)

        if signal.is_valid:
            print(f"      SIGNAL GEFUNDEN!")
            print(f"      Short Put: ${signal.short_put_strike:.0f}")
            print(f"      Short Call: ${signal.short_call_strike:.0f}")
            print(f"      Net Credit: ${signal.net_credit:.2f}")
            print(f"      Max Loss: ${signal.max_loss:.0f}")
            print(f"      Risk Level: {signal.risk_level}")
        else:
            print(f"      Kein Signal: {signal.rejection_reason}")
        print()

        if dry_run:
            print("[DRY-RUN] Kein Versand, nur Anzeige")
            print()
            _print_signal_details(signal)
            return True

        # 3. E-Mail versenden
        print("[3/4] Versende E-Mail...")
        email_sender = EmailSender(config)
        if email_sender.enabled:
            success = email_sender.send_signal(signal)
            print(f"      E-Mail: {'Gesendet' if success else 'Fehler'}")
        else:
            print("      E-Mail deaktiviert")
        print()

        # 4. Webseite generieren
        print("[4/4] Generiere Webseite...")
        website_gen = WebsiteGenerator(config)
        if website_gen.enabled:
            history = website_gen.load_history()
            success = website_gen.generate(signal, history)
            print(f"      Webseite: {'Generiert' if success else 'Fehler'}")
        else:
            print("      Webseite deaktiviert")
        print()

        print("=" * 60)
        print("FERTIG!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nFEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


def _print_signal_details(signal):
    """Gibt Signal-Details aus"""
    if signal.is_valid:
        print("-" * 40)
        print("SIGNAL DETAILS")
        print("-" * 40)
        print(f"Symbol:         {signal.symbol}")
        print(f"Verfall:        {signal.expiry}")
        print()
        print("Legs:")
        print(f"  Short Put:    ${signal.short_put_strike:.0f} @ ${signal.short_put_premium:.2f}")
        print(f"  Long Put:     ${signal.long_put_strike:.0f} @ ${signal.long_put_premium:.2f}")
        print(f"  Short Call:   ${signal.short_call_strike:.0f} @ ${signal.short_call_premium:.2f}")
        print(f"  Long Call:    ${signal.long_call_strike:.0f} @ ${signal.long_call_premium:.2f}")
        print()
        print(f"Net Credit:     ${signal.net_credit:.2f}")
        print(f"Max Profit:     ${signal.max_profit:.0f}")
        print(f"Max Loss:       ${signal.max_loss:.0f}")
        print(f"Breakeven:      ${signal.breakeven_lower:.2f} - ${signal.breakeven_upper:.2f}")
        print()
        print(f"Empfehlung:     {signal.recommended_contracts} Contract(s)")
        print(f"Risiko:         ${signal.total_risk:.0f} ({signal.risk_percent:.1f}%)")
        print(f"Risk Level:     {signal.risk_level}")
        print("-" * 40)
    else:
        print("-" * 40)
        print("KEIN SIGNAL")
        print(f"Grund: {signal.rejection_reason}")
        print("-" * 40)


def main():
    """Haupteinstiegspunkt"""
    parser = argparse.ArgumentParser(
        description='Options Signal System - 0DTE Iron Condor Signale'
    )
    parser.add_argument(
        '--config', '-c',
        help='Pfad zur Konfigurationsdatei'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Signal generieren ohne zu versenden'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test-Modus'
    )

    args = parser.parse_args()

    # Konfiguration laden
    config = load_config(args.config)

    # Signal generieren
    success = run_signal_generation(
        config,
        dry_run=args.dry_run,
        test_mode=args.test
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
