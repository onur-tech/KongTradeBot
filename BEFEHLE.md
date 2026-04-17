# BEFEHLE.md — Polymarket Bot Spickzettel

Alle Befehle werden im Bot-Verzeichnis ausgeführt:
```
cd "C:\Users\OnurAribas\Downloads\Trading Bot\Trading Bot\Trading Bot"
```

---

## Bot Starten & Stoppen

```powershell
# Dry-Run starten (Standard — kein echtes Geld)
python main.py

# Live-Trading starten (echtes Geld!)
python main.py --live

# Bot stoppen
Ctrl+C

# Laufenden Bot-Prozess finden
tasklist | findstr python

# Bot-Prozess erzwingen beenden
taskkill /F /IM python.exe
```

---

## Bot Neustarten

```powershell
# 1. Stoppen (Ctrl+C oder):
taskkill /F /IM python.exe

# 2. Neu starten (Dry-Run):
python main.py

# 2. Neu starten (Live):
python main.py --live
```

---

## Auswertung & Analyse

```powershell
# Performance-Auswertung (PnL, Win-Rate, Statistiken)
python auswertung.py

# Offene Märkte auflösen & PnL aktualisieren
python resolver.py

# Steuer-Export (Jahr angeben)
python main.py --export-tax 2026
python main.py --export-tax 2025
```

---

## Wallet & Balance

```powershell
# USDC-Kontostand der eigenen Wallet prüfen
python wallet_check.py

# Polymarket API-Verbindung testen
python api_test.py
```

---

## Logs überwachen

```powershell
# Live-Log verfolgen (heutiges Datum)
Get-Content "logs\bot_$(Get-Date -Format 'yyyy-MM-dd').log" -Wait -Tail 50

# Nur Fehler und Trades anzeigen
Get-Content "logs\bot_$(Get-Date -Format 'yyyy-MM-dd').log" -Wait -Tail 100 |
  Select-String "ERROR|WARNING|TRADE|erlaubt|abgelehnt|Kill"

# Letzte 100 Zeilen einmalig lesen
Get-Content "logs\bot_$(Get-Date -Format 'yyyy-MM-dd').log" -Tail 100

# Alle heutigen ERRORs zählen
Select-String "ERROR" "logs\bot_$(Get-Date -Format 'yyyy-MM-dd').log" | Measure-Object
```

---

## Abhängigkeiten installieren

```powershell
# Alle Pakete aus requirements.txt installieren
pip install -r requirements.txt

# Einzelnes Paket installieren / updaten
pip install py-clob-client --upgrade
pip install anthropic --upgrade

# Installierte Pakete anzeigen
pip list

# Paket-Versionen prüfen
pip show py-clob-client
pip show anthropic
```

---

## Claude Code starten

```powershell
# Claude Code im Bot-Verzeichnis starten
claude

# Claude Code mit bestimmter Datei öffnen
claude main.py

# Claude Code Version prüfen
claude --version
```

---

## Cache & Temp-Dateien löschen

```powershell
# Python __pycache__ löschen (bei merkwürdigen Import-Fehlern)
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# .pyc Dateien löschen
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Bot-State zurücksetzen (ACHTUNG: löscht offene Positionen!)
Remove-Item bot_state.json -ErrorAction SilentlyContinue
Remove-Item wallet_history.json -ErrorAction SilentlyContinue

# pip-Cache löschen (bei Installation-Problemen)
pip cache purge
```

---

## Konfiguration & Umgebung

```powershell
# .env Datei bearbeiten
notepad .env

# .env.live bearbeiten (Live-Konfiguration)
notepad .env.live

# Python-Version prüfen
python --version

# Aktuelles Verzeichnis anzeigen
pwd

# Dateien im Bot-Ordner anzeigen
ls
```

---

## Tests ausführen

```powershell
# Execution Engine testen
python test_execution_engine.py

# Performance Tracker testen
python test_performance_tracker.py
```

---

## Wichtige Dateien

| Datei | Bedeutung |
|---|---|
| `.env` | Aktive Konfiguration (Wallet, API-Keys, Limits) |
| `.env.live` | Live-Trading Konfiguration (konservative Limits) |
| `bot_state.json` | Offene Positionen + bekannte Tx-Hashes |
| `trades_archive.json` | Alle Trades (für Auswertung & Steuer) |
| `wallet_history.json` | Whale-Wallet Verlauf |
| `logs/bot_YYYY-MM-DD.log` | Tages-Logdatei |
