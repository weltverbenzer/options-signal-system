#!/usr/bin/env python3
"""
Options Signal System - Hauptprogramm v2
=========================================
Screent Watchlist und liefert Kandidaten für:
- Iron Condor (ruhige Aktien ohne Events)
- Straddle/Strangle (Aktien mit Earnings/Events)

Mit Begruendungen und Liquiditaetspruefung.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from screener import StockScreener, ScreenerResult, DEFAULT_WATCHLIST
from market_data import MarketDataFetcher
from signal_generator import SignalGenerator, IronCondorSignal
from email_sender_v2 import EmailSenderV2
from website_generator import WebsiteGenerator


def load_config(config_path: str = None) -> dict:
    """Laedt Konfiguration aus Datei oder Umgebungsvariablen"""
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
            'title': os.getenv('WEBSITE_TITLE', 'Options Signal System')
        }
    }


def generate_iron_condor_details(symbol: str, config: dict) -> dict:
    """Generiert konkrete Iron Condor Details für ein Symbol"""
    try:
        fetcher = MarketDataFetcher(symbol)
        snapshot = fetcher.get_market_snapshot()

        generator = SignalGenerator(config)
        signal = generator.generate_signal(snapshot)

        if signal.is_valid:
            return {
                'valid': True,
                'short_put': signal.short_put_strike,
                'long_put': signal.long_put_strike,
                'short_call': signal.short_call_strike,
                'long_call': signal.long_call_strike,
                'net_credit': signal.net_credit,
                'max_profit': signal.max_profit,
                'max_loss': signal.max_loss,
                'contracts': signal.recommended_contracts,
                'risk_pct': signal.risk_percent
            }
        else:
            return {'valid': False, 'reason': signal.rejection_reason}

    except Exception as e:
        return {'valid': False, 'reason': str(e)}


def generate_straddle_details(symbol: str, current_price: float, capital: int = 5000) -> dict:
    """
    Generiert konkrete Straddle Details für ein Symbol.

    WICHTIG: Begrenzt Kosten auf max. 10% des Kapitals!
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)

        expirations = ticker.options
        if not expirations:
            return {'valid': False, 'reason': 'Keine Optionen verfügbar'}

        # Nächstes Verfallsdatum (oder übernächstes für mehr Zeit)
        expiry = expirations[0] if len(expirations) == 1 else expirations[1]

        chain = ticker.option_chain(expiry)

        # ATM Strike finden
        atm_strike = round(current_price)

        # Nächsten verfügbaren Strike
        call_strikes = chain.calls['strike'].values
        put_strikes = chain.puts['strike'].values

        atm_call_idx = abs(call_strikes - atm_strike).argmin()
        atm_put_idx = abs(put_strikes - atm_strike).argmin()

        atm_call = chain.calls.iloc[atm_call_idx]
        atm_put = chain.puts.iloc[atm_put_idx]

        call_price = (atm_call['bid'] + atm_call['ask']) / 2
        put_price = (atm_put['bid'] + atm_put['ask']) / 2

        total_cost = (call_price + put_price) * 100
        breakeven_up = atm_call['strike'] + call_price + put_price
        breakeven_down = atm_put['strike'] - call_price - put_price

        # Risiko berechnen (bei Straddle = Gesamtkosten)
        max_allowed = capital * 0.15  # Erhoehe auf 15% - Screener filtert vorher
        risk_pct = (total_cost / capital) * 100

        # Nur warnen, nicht blockieren (Screener filtert bereits nach Preis)
        too_expensive = total_cost > max_allowed

        return {
            'valid': True,
            'expiry': expiry,
            'call_strike': atm_call['strike'],
            'put_strike': atm_put['strike'],
            'call_price': call_price,
            'put_price': put_price,
            'total_cost': total_cost,
            'risk_pct': risk_pct,
            'breakeven_up': breakeven_up,
            'breakeven_down': breakeven_down,
            'breakeven_move_pct': ((breakeven_up - current_price) / current_price) * 100,
            'warning': f'Höheres Risiko: {risk_pct:.0f}% vom Konto' if too_expensive else None
        }

    except Exception as e:
        return {'valid': False, 'reason': str(e)}


def run_screening(config: dict) -> dict:
    """
    Fuehrt das Screening durch und sammelt alle Ergebnisse.
    """
    print("=" * 60)
    print("OPTIONS SIGNAL SYSTEM v2")
    print(f"Zeitpunkt: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("=" * 60)

    # 1. Screening
    capital = config.get('account', {}).get('capital', 5000)
    print(f"\n[1/3] Screene Watchlist (Kapital: ${capital})...")
    screener = StockScreener(capital=capital)
    results = screener.screen_all()

    iron_condor_candidates = results['iron_condor']
    straddle_candidates = results['straddle']

    print(f"\n  Iron Condor Kandidaten: {len(iron_condor_candidates)}")
    print(f"  Straddle Kandidaten: {len(straddle_candidates)}")

    # 2. Details für Top-Kandidaten generieren
    print("\n[2/3] Generiere Trade-Details...")

    ic_details = []
    for candidate in iron_condor_candidates[:3]:
        print(f"  Berechne Iron Condor für {candidate.symbol}...")
        details = generate_iron_condor_details(candidate.symbol, config)
        ic_details.append({
            'candidate': candidate,
            'details': details
        })

    st_details = []
    capital = config.get('account', {}).get('capital', 5000)
    for candidate in straddle_candidates[:3]:
        print(f"  Berechne Straddle für {candidate.symbol}...")
        details = generate_straddle_details(candidate.symbol, candidate.current_price, capital)
        st_details.append({
            'candidate': candidate,
            'details': details
        })

    return {
        'iron_condor': ic_details,
        'straddle': st_details,
        'generated_at': datetime.now()
    }


def main():
    parser = argparse.ArgumentParser(description='Options Signal System v2')
    parser.add_argument('--config', '-c', help='Pfad zur Konfigurationsdatei')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Nur anzeigen')

    args = parser.parse_args()
    config = load_config(args.config)

    # Screening durchfuehren
    results = run_screening(config)

    # Ausgabe
    print("\n" + "=" * 60)
    print("IRON CONDOR KANDIDATEN")
    print("(Ruhige Aktien ohne Events - Seitwärtsbewegung erwartet)")
    print("=" * 60)

    for item in results['iron_condor']:
        c = item['candidate']
        d = item['details']
        print(f"\n{c.symbol} ({c.company_name})")
        print(f"  Kurs: ${c.current_price:.2f} | Score: {c.iron_condor_score:.0f}/100")
        print(f"  Gruende: {', '.join(c.reasons)}")
        if d['valid']:
            print(f"  Trade: Sell {d['short_put']}/{d['short_call']} | Buy {d['long_put']}/{d['long_call']}")
            print(f"  Credit: ${d['net_credit']:.2f} | Max Loss: ${d['max_loss']:.0f}")
        else:
            print(f"  Trade nicht möglich: {d.get('reason', 'Unbekannt')}")
        if c.warnings:
            print(f"  Warnungen: {', '.join(c.warnings)}")

    print("\n" + "=" * 60)
    print("STRADDLE KANDIDATEN")
    print("(Aktien mit Earnings/Events - Große Bewegung erwartet)")
    print("=" * 60)

    for item in results['straddle']:
        c = item['candidate']
        d = item['details']
        print(f"\n{c.symbol} ({c.company_name})")
        print(f"  Kurs: ${c.current_price:.2f} | Score: {c.straddle_score:.0f}/100")
        if c.earnings_date:
            print(f"  Earnings: {c.earnings_date} (in {c.days_to_earnings} Tagen)")
        print(f"  Gruende: {', '.join(c.reasons)}")
        if d['valid']:
            print(f"  Trade: Buy {d['call_strike']}C + {d['put_strike']}P ({d['expiry']})")
            print(f"  Kosten: ${d['total_cost']:.0f} | Breakeven: +/-{d['breakeven_move_pct']:.1f}%")
        else:
            print(f"  Trade nicht möglich: {d.get('reason', 'Unbekannt')}")
        if c.warnings:
            print(f"  Warnungen: {', '.join(c.warnings)}")

    if args.dry_run:
        print("\n[DRY-RUN] Kein E-Mail/Website-Generierung")
        return True

    # Website generieren
    print("\n[3/4] Generiere Website...")
    website_gen = WebsiteGenerator(config)
    if website_gen.enabled:
        success = website_gen.generate_v2(results)
        print(f"  Website: {'Generiert' if success else 'Fehler'}")
    else:
        print("  Website deaktiviert")

    # E-Mail senden
    print("\n[4/4] Sende E-Mail...")
    email_sender = EmailSenderV2(config)
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
