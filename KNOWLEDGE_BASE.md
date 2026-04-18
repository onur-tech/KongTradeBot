# KongTrade Bot — Knowledge Base
_Format: Problem → Root-Cause → Fix → Status_

## P001 — FillTracker: open_positions immer leer

**Status:** BEHOBEN (18.04.2026)

**Symptom:** Bot platziert Orders, Dashboard zeigt 0 offene Positionen.

**Root-Cause:** FillTracker._subscribe() nutzte Builder-Credentials statt L2-Credentials.
Polymarket User-Channel benötigt L2-Creds via ClobClient.derive_api_key().
Falsche Creds -> silent disconnect -> keine Events -> alles bleibt in pending hängen.

**Referenz:** github.com/Polymarket/clob-client/issues/303

**Fix:** core/fill_tracker.py -> _derive_l2_creds() nutzt ClobClient.derive_api_key().

---

## P002 — dict object has no attribute signature_type

**Status:** BEHOBEN (17.04.2026)

**Root-Cause:** get_balance_allowance() mit plain dict aufgerufen statt BalanceAllowanceParams Objekt.

**Fix:** from py_clob_client.clob_types import BalanceAllowanceParams; params = BalanceAllowanceParams(...)

---

## P003 — Pending Orders nach Neustart verloren

**Status:** BEHOBEN (18.04.2026)

**Root-Cause:** save_positions() speicherte nicht _pending_data, market_closes_at fehlte.

**Fix:** main.py: market_closes_at serialisieren + recover_stale_positions() via REST API beim Start.

---

## P004 — Proxy-Deploy Catch-22

**Status:** DOKUMENTIERT

**Symptom:** Alle Orders scheitern, Proxy nicht deployed.

**Lösung:** $1 Manual-Trade auf polymarket.com über NORWEGEN-VPN (nicht Finnland!).

---

## P005 — Balance-Fetch fehlschlägt (rpc.ankr.com)

**Status:** WORKAROUND

**Root-Cause:** rpc.ankr.com blockiert Hetzner-IP.

**Workaround:** Fallback-RPCs: polygon-bor-rpc.publicnode.com (reliable), polygon-rpc.com, 1rpc.io/matic.

---

## P006 — signature_type=1 Pflicht für Magic-Link

**Status:** DOKUMENTIERT

**Fix:** ClobClient(... signature_type=1). Ohne diesen Parameter -> Auth-Fehler bei allen Orders.

---

## P007 — NegRisk-Märkte (z.B. Maduro Venezuela)

**Status:** DOKUMENTIERT

**Fix:** neg_risk Flag aus Orderbook lesen (_get_market_info), im Log als [NEGRISK] markieren.

---

## P008 — Ghost Trades durch create_order + post_order separat

**Status:** DOKUMENTIERT

**Fix:** Immer create_and_post_order() in EINEM Call. Niemals create_order() + post_order() separat.

---

## Infrastruktur-Quick-Reference

Server:          89.167.29.183 (Hetzner Helsinki)
Bot-Pfad:        /root/KongTradeBot/
Proxy-Wallet:    0x700BC51b721F168FF975ff28942BC0E5fAF945eb
Magic-EOA:       0xd7869A5Cae59FDb6ab306ab332a9340AceC8cbE2
USDC.e Contract: 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
Dashboard-URL:   ssh -L 5000:localhost:5000 root@89.167.29.183 -> http://localhost:5000
Bot Log:         /root/KongTradeBot/logs/bot_YYYY-MM-DD.log
State:           /root/KongTradeBot/bot_state.json
Metrics DB:      /root/KongTradeBot/metrics.db
