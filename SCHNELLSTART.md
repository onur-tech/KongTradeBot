# 🤖 POLYMARKET BOT — SCHNELLSTART

## Was ist das hier?
Automatisierter Copy-Trading Bot für Polymarket.
Kopiert Trades erfolgreicher Wallets proportional auf dein Konto.

---

## SCHRITT 1 — Dateien auf Server kopieren

```bash
# Ordner auf Server hochladen (z.B. via SFTP oder SCP)
scp -r polymarket_bot/ user@dein-server:/home/user/
```

---

## SCHRITT 2 — Setup ausführen (1 Befehl)

```bash
cd polymarket_bot
chmod +x setup.sh
./setup.sh
```

Das Script installiert automatisch alle Abhängigkeiten und erstellt die .env Vorlage.

---

## SCHRITT 3 — .env ausfüllen

```bash
nano .env
```

Mindestens diese 3 Felder:

```
PRIVATE_KEY=0x...          ← MetaMask Private Key
POLYMARKET_ADDRESS=0x...   ← Polymarket Proxy Adresse
TARGET_WALLETS=0x...       ← Wallet die kopiert werden soll
```

**Woher bekomme ich die Polymarket Adresse?**
→ polymarket.com einloggen → Profil → "Copy Proxy Address"

**Welche Wallets kopieren?**
→ polymonit.com/leaderboard → Wallet mit 58%+ Win Rate, 3+ Monate aktiv, 5-15 Trades/Tag

---

## SCHRITT 4 — Tests ausführen

```bash
python3 tests/test_wallet_monitor.py
python3 tests/test_execution_engine.py
python3 tests/test_performance_tracker.py
```

Alle Tests müssen grün sein bevor du weitermachst.

---

## SCHRITT 5 — Dry-Run starten (SICHER)

```bash
python3 main.py
```

Bot läuft, erkennt Trades, loggt alles — kauft aber NICHTS.
Mindestens 24-48 Stunden laufen lassen und Logs beobachten.

---

## SCHRITT 6 — Live gehen (ECHTES GELD)

Erst wenn Dry-Run gut aussieht:

```bash
python3 main.py --live
```

---

## Im Hintergrund laufen lassen (Server)

```bash
# Starten
nohup python3 main.py > logs/bot.log 2>&1 &
echo $! > bot.pid

# Logs beobachten
tail -f logs/bot.log

# Stoppen
kill $(cat bot.pid)
```

---

## Performance + Steuer prüfen

```python
# In Python Console:
from core.performance_tracker import PerformanceTracker
t = PerformanceTracker()
t.print_performance_report()           # Performance anzeigen
t.export_tax_csv(year=2026)            # CSV für Finanzamt exportieren
print(t.get_yearly_summary(2026))      # Jahres-Zusammenfassung
```

---

## Projektstruktur

```
polymarket_bot/
├── main.py                    ← Einstiegspunkt
├── .env.example               ← Config-Vorlage
├── requirements.txt           ← Abhängigkeiten
├── setup.sh                   ← Server-Setup Script
│
├── core/
│   ├── wallet_monitor.py      ← Wallets überwachen (Polling)
│   ├── websocket_monitor.py   ← Wallets überwachen (Echtzeit)
│   ├── execution_engine.py    ← Orders platzieren
│   ├── risk_manager.py        ← Kill-Switch, Limits
│   └── performance_tracker.py ← Performance + Steuer-Tracker
│
├── strategies/
│   └── copy_trading.py        ← Proportionales Sizing
│
├── utils/
│   ├── config.py              ← .env laden + validieren
│   └── logger.py              ← Logging
│
├── tests/                     ← Alle Tests
├── data/                      ← Trades werden hier gespeichert
└── logs/                      ← Log-Dateien
```

---

## Sicherheits-Checkliste

- [ ] Private Key nur in .env — niemals im Code
- [ ] .env in .gitignore (bereits eingestellt)
- [ ] Erst Dry-Run, dann Live
- [ ] Start mit kleinem Kapital ($100-200)
- [ ] Max Trade Size auf $10-25 begrenzen
- [ ] Tages-Verlustlimit auf $50 setzen

---

## Wichtige Konfiguration (.env)

| Variable | Empfehlung Start | Beschreibung |
|---|---|---|
| MAX_TRADE_SIZE_USD | 10 | Max $10 pro Trade |
| MAX_DAILY_LOSS_USD | 50 | Bot stoppt bei $50 Verlust/Tag |
| COPY_SIZE_MULTIPLIER | 0.05 | 5% der Whale-Position |
| MIN_TRADE_SIZE_USD | 2 | Trades unter $2 ignorieren |
| DRY_RUN | true | Erst auf true lassen! |

---

## Steuer (Deutschland)

- **Kein Gewerbe nötig** solange du dein eigenes Kapital handelst
- Gewinne als sonstige Einkünfte §22 EStG (dein persönlicher Steuersatz)
- Freigrenze: €1.000/Jahr (darunter steuerfrei)
- Verluste können gegengerechnet werden
- DAC8 ab 2026: Transaktionen werden automatisch gemeldet
- CSV-Export mit `t.export_tax_csv(year=2026)` → direkt in Blockpit importieren
- **Steuerberater mit Krypto-Erfahrung empfohlen** vor dem Live-Start

---

*Erstellt: April 2026 | Kein Finanzberatung*
