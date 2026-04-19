# T-TELEGRAM: Glint Alerts → Kong Trading Bot Bridge
_Erstellt: 2026-04-21 | Für: KongTradeBot T-NEWS Phase 2_

---

## Option 2 — Telegram Gruppe (manuell, sofort)

### Schritt 1: Neue Telegram Gruppe erstellen
- Telegram öffnen → Neuer Chat → Neue Gruppe
- Name: **"KongTrade Intelligence"**
- Onur hinzufügen

### Schritt 2: Glint Alerts Bot hinzufügen
- `@GlintAlertsBot` in die Gruppe einladen
- Bot sendet jetzt alle konfigurierten Alerts in die Gruppe
- Sicherstellen dass Keyword-Alerts bereits in Glint eingerichtet sind
  (→ `docs/T_NEWS_SETUP_ANLEITUNG.md` für Keyword-Sets)

### Schritt 3: Kong Trading Bot hinzufügen
- `@Kong_polymarket_bot` in die Gruppe einladen

### Schritt 4: Gruppe Chat-ID herausfinden
- In der Gruppe `/start` senden
- Im Browser aufrufen (TOKEN aus .env einsetzen):
  ```
  https://api.telegram.org/bot[TOKEN]/getUpdates
  ```
- In der JSON-Antwort suchen: `"chat":{"id":-100XXXXXXXXX}`
- Chat-ID notieren (beginnt immer mit `-100...`)

### Schritt 5: In .env auf Server eintragen
```
TELEGRAM_GROUP_CHAT_ID=-100XXXXXXXXX
GLINT_BRIDGE_ENABLED=true
```

Danach liest Server-CC alle Gruppen-Nachrichten und kann Glint-Alerts verarbeiten.

---

## Funktionsweise

```
Glint erkennt Signal
       │
  @GlintAlertsBot → Nachricht in "KongTrade Intelligence" Gruppe
                              │
                    @Kong_polymarket_bot liest Gruppe
                              │
                      Signal Parser (core/glint_parser.py)
                              │
               ┌──────────────┴──────────────┐
               │                             │
          Tier 1 Signal                 Tier 2/3 Signal
      (CRITICAL + Geopolitics)         (HIGH / MEDIUM)
               │                             │
          Auto-Trade                   Alert an Onur
```

---

## Hinweise

- Der Bot muss **Admin-Rechte** in der Gruppe haben um alle Nachrichten zu lesen
- `GLINT_BRIDGE_ENABLED=false` lässt den Bot die Gruppe ignorieren (safe default)
- Parser-Design: `prompts/t_glint_api_integration.md` → Phase 2
- Vollständige Implementierung erst nach T-WS (WebSocket Monitor)

---

_Nächster Schritt: Server-CC mit `prompts/t_glint_api_integration.md` beauftragen_
