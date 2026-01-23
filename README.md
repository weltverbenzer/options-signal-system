# Options Signal System

Automatisiertes System fuer taegliche 0DTE Iron Condor Signale auf SPY.

## Was macht dieses System?

- Analysiert taeglich den Markt (SPY, VIX, Optionskette)
- Generiert Iron Condor Trade-Signale wenn Bedingungen erfuellt
- Versendet E-Mail mit konkreten Trade-Anweisungen
- Aktualisiert eine Webseite mit aktuellen Signalen

## Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/DEIN-USERNAME/options-signal-system.git
cd options-signal-system
```

### 2. Python-Umgebung einrichten

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Konfiguration erstellen

```bash
cp config.example.yaml config.yaml
```

Bearbeite `config.yaml` und trage deine Einstellungen ein:

```yaml
account:
  capital: 5000          # Dein Trading-Kapital
  max_risk_percent: 2    # Max. Risiko pro Trade

email:
  enabled: true
  recipient: "deine.email@beispiel.de"
  smtp:
    username: "dein.gmail@gmail.com"
    password: "xxxx xxxx xxxx xxxx"  # Gmail App-Password
```

### 4. Lokal testen

```bash
cd src
python main.py --dry-run
```

## Automatischer Betrieb mit GitHub Actions

### Secrets einrichten

Gehe zu deinem Repository > Settings > Secrets and variables > Actions

Fuege folgende Secrets hinzu:
- `EMAIL_RECIPIENT`: Deine E-Mail-Adresse
- `SMTP_USERNAME`: Gmail-Adresse
- `SMTP_PASSWORD`: Gmail App-Password

### Gmail App-Password erstellen

1. Gehe zu https://myaccount.google.com/security
2. Aktiviere 2-Faktor-Authentifizierung
3. Gehe zu https://myaccount.google.com/apppasswords
4. Erstelle ein App-Password fuer "Mail"
5. Kopiere das 16-stellige Password

### GitHub Pages aktivieren

1. Gehe zu Repository > Settings > Pages
2. Source: "Deploy from a branch"
3. Branch: "main", Folder: "/docs"
4. Save

Deine Signale sind dann unter `https://DEIN-USERNAME.github.io/options-signal-system/` erreichbar.

## Projektstruktur

```
options-signal-system/
├── .github/
│   └── workflows/
│       └── daily-signal.yml    # GitHub Actions Workflow
├── docs/                       # Generierte Webseite
│   ├── index.html
│   └── history.json
├── src/
│   ├── main.py                 # Hauptprogramm
│   ├── market_data.py          # Marktdaten-Modul
│   ├── signal_generator.py     # Signal-Generator
│   ├── email_sender.py         # E-Mail-Versand
│   └── website_generator.py    # Webseiten-Generator
├── config.example.yaml         # Beispiel-Konfiguration
├── requirements.txt            # Python Dependencies
└── README.md
```

## Signal-Kriterien

Ein Iron Condor Signal wird generiert wenn:

- VIX zwischen 12 und 25
- Keine Fed-Entscheidung heute
- Keine wichtigen Wirtschaftsdaten (CPI, Jobs)
- IV Percentile > 20%
- Ausreichend Liquiditaet in den Optionen

Wenn Bedingungen nicht erfuellt: "Kein Signal heute"

## Risiko-Hinweis

**WICHTIG**: Options-Trading birgt erhebliche Risiken.

- Dieses System ist fuer Bildungszwecke gedacht
- Vergangene Signale garantieren keine zukuenftigen Gewinne
- Handel nur mit Kapital das du bereit bist zu verlieren
- Max. 2% Risiko pro Trade einhalten

## Lizenz

MIT License - siehe LICENSE file
