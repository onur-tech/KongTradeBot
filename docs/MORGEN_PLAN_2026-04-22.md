# Morgen-Plan — 2026-04-22
_Erstellt: 2026-04-21 | Von: Windows-CC_

---

## PRIO 1 — Bot-Stabilität verifizieren

**Frage:** Läuft der Bot jetzt 24h stabil ohne Crash-Loop?

```bash
# Restarts seit letztem Fix prüfen
journalctl -u kongtrade-bot | grep -c "Started"

# Aktueller Status
systemctl status kongtrade-bot

# Letzte 50 Log-Zeilen
journalctl -u kongtrade-bot -n 50
```

**Ziel:** Max 1-2 Restarts pro Tag (automatische Wiederherstellung nach Fehler OK).
**Root Cause war:** kongtrade-deploy.timer deaktiviert? → `systemctl status kongtrade-deploy.timer`

---

## PRIO 2 — Weather Trading auf LIVE schalten

**Startdatum DRY_RUN:** 2026-04-20 → LIVE frühestens: **2026-04-27**

```bash
# DRY_RUN Ergebnisse prüfen
grep "WeatherScout" /root/KongTradeBot/logs/bot_*.log | grep "Opportunit"

# Wenn Opportunities gefunden + Logik korrekt:
# .env anpassen:
WEATHER_DRY_RUN=false
WEATHER_MAX_DAILY_USD=20
```

**Erstes Signal:** Istanbul war erstes Signal mit +90% Edge (identifiziert 20.04.)
**Bedingung für LIVE:** Min. 3-5 DRY_RUN-Opportunities mit korrekter Logik beobachtet.

---

## PRIO 3 — Telegram Bridge aktivieren

**Was Onur holen muss:**
1. `my.telegram.org` → mit Telegram-Nummer einloggen
2. "API development tools" → Neue App
3. `api_id` + `api_hash` notieren

**Dann Server-CC:**
```bash
# .env ergänzen:
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_GROUP_CHAT_ID=-100XXXXXXXXX   # aus @GlintAlertsBot /start
GLINT_BRIDGE_ENABLED=true
```

**Anleitung:** `docs/T_TELEGRAM_BRIDGE_SETUP.md`

---

## PRIO 4 — X/Twitter Monitor live (Xquik)

**Kosten:** $20/Monat (Starter-Plan, 140.000 Tweets/Mo)
**Setup:** Nur 3 Schritte (API-Key → Monitor → Webhook)

**Anleitung:** `prompts/t_x_twitter_xquik_setup.md` (heute erstellt)

**Tier-1 Accounts zuerst:**
- `@Polymarket` — offizielle Ankündigungen
- `@glintintel` — Glint Updates
- `@spydenuevo` — neobrother, Weather-Trading

**Webhook-URL auf Server:** `https://kongtrade.server/webhook/x-alert`

---

## PRIO 5 — PANews Wallets Integration

**Server-CC Prompt:** `prompts/integrate_panews_wallets.md`

Reihenfolge nach ROI:
1. **EFFICIENCYEXPERT** (`0x8c0b...7aa5`) — 1.659% ROI, Esports 42.8/Tag
2. **synnet** (`0x8e0b...e5c`) — 121% ROI, Tennis 0.5/Tag
3. **Frank0951** (`0x4047...293`) — 49% ROI, Valorant 5.5/Tag
4. **middleoftheocean** (`0x6c74...d4e`) — 83.7% WR, Soccer 13/Tag
5. **HondaCivic** (`0x15ce...5fa`) — 85.7% WR, Weather (predicts.guru PENDING)

**Nach Integration:** Bot-Restart + Verify-Log prüfen.

---

## Wann was (Timeline)

| Zeit | Aufgabe | Wer |
|------|---------|-----|
| Früh | Bot-Stabilität Check | Server-CC |
| Früh | Dashboard Tab 4 deployen | Server-CC |
| Früh | kongtrade-status Push (PAT-Update) | Onur + Server-CC |
| Mittag | PANews Wallets integrieren | Server-CC |
| Mittag | Xquik Account + API-Key | Onur |
| Abend | Telegram Bridge (API_ID/HASH) | Onur + Server-CC |
| Abend | X-Monitor Webhook aktivieren | Server-CC |

---

_Stand: 2026-04-21 | Nächste Review: 2026-05-05 (PANews predicts.guru Queue)_
