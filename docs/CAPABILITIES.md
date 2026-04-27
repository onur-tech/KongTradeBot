# KongTrade Capabilities & Bright Data Strategy

## Bright Data Account Status
- Plan: Pay-as-you-go
- Balance: $206.98 (Stand 27.04.2026)
- API-Token: `BRIGHTDATA_API_TOKEN` (siehe `.env`, **nicht** in Git)
- MCP URL: `BRIGHTDATA_MCP_URL` (Token in der URL, für Claude Code)
- 5000 free MCP requests/month (resets monatlich)
- Promo Code: `APIS25` (25% off PAYG für 6 Monate)
- Monthly budget guard: `BRIGHTDATA_MONTHLY_BUDGET_USD=100` mit
  Warn/Kill-Schwellen (80% / 95%)

## Bereits provisioniert (Stand 25.04.2026)

Zones:
- `mcp_unlocker` — Web Unlocker (BRIGHTDATA_ZONE_UNLOCKER)
- `mcp_browser`  — Scraping Browser (BRIGHTDATA_ZONE_BROWSER)
- `serp_news`    — SERP API (BRIGHTDATA_ZONE_SERP)

Datacenter Proxy für Wunderground-Latency-Arb:
- Host: `brd.superproxy.io:33335`
- Username: `brd-customer-hl_50f5e25a-zone-datacenterweather`

Dataset IDs (Scrapers Library, in `.env` als `BD_DS_*`):
X_POSTS, X_PROFILES, INSTAGRAM_PROFILES, TIKTOK_PROFILES,
YOUTUBE_CHANNELS, FACEBOOK_PROFILES, +9 weitere

## Phase 1 — Aktiv ab 27.04.2026 (~$70-80/Monat)
- Twitter Posts Scraper PAYG für 50 Watchlist-Accounts hourly
  - ~36 K records/Monat × $1.50/1k = $54/Monat
  - Mit APIS25: $40.50/Monat
- News-Aggregation via Web Unlocker für 4 Sites hourly:
  reuters.com, bloomberg.com, decrypt.co, politico.com
  - ~14 K requests/Monat × $1.50/1k = $21/Monat
  - Erste 5 K via MCP free → $13.50/Monat netto
- Polymarket: **NICHT** Bright Data — public CLOB API ist gratis
- **Total Phase 1: ~$54/Monat netto**
- Runway aus $206.98 Balance: ~3.8 Monate

## Phase 2 — Trigger: Phase 1 Edge verifiziert (~$200-500/Monat)
- Twitter scaling auf 200 Accounts hourly = $200/Monat
- News scaling auf 20 Sites = $75/Monat oder $499 Starter-Sub
- Eventuell Twitter Profile-Scraper für Wallet-Discovery

## Phase 3 — Trigger: Bot live mit echtem Geld (>$1000/Monat)
- Subscription Tier (Web Scraper API Growth $499/Monat) bei
  >330 K records/Monat
- Polymarket-Fallback-Scraper aktivieren
- Marketplace Datasets für historischen Backfill

## NICHT nutzen
- Scraping Browser (per-GB Pricing, unpredictable)
- SERP API (Polymarket reicht)
- Crawl API (overkill für unsere Volumes)
- Marketplace Twitter Dataset $250 Minimum (zu stale für Live-Signals,
  nur für historischen Backfill)

## AI Startup Program — TODO
Apply at brightdata.com — bis zu $20.000 Credit für AI-Startups.
Anwendbar wenn KongTrade als Produkt positioniert wird.

## Login-protected Content
Twitter Following-Listen erfordern KYC + Compliance Review bei
Bright Data. **NICHT** Standard-Workflow. Workaround: Onur tippt
manuell wichtige Watchlist-Accounts.

## Aktuelle Implementation (Skelett, dormant)
- `services/trend_monitor/` — Module-Skeleton, kein Live-Code
- `services/trend_monitor/watchlist.py` — Onur ergänzt initiale 50 Accounts
- `services/trend_monitor/twitter_scraper.py` — Stub mit TODO-Markern
- `services/trend_monitor/news_scraper.py` — Stub
- `services/trend_monitor/signals_db.py` — `data/trend_signals.db` Schema
- `/etc/systemd/system/kongtrade-trend-monitor.timer` — `hourly`,
  daemon-reload'd aber **NICHT** enabled, **NICHT** started
- `.env` Variable `TREND_MONITOR_ENABLED=false` (siehe `.env.example`)

## Gating für Aktivierung
1. Onur erweitert `watchlist.py` mit konkreten Twitter-Handles
2. APIS25-Promo aktivieren (Browser, einmalig)
3. `TREND_MONITOR_ENABLED=true` in `.env`
4. `sudo systemctl enable --now kongtrade-trend-monitor.timer`
5. Nach 24-48 h Beobachtung der Cost-Per-Hour gegen `/api/v2/ops/data`
