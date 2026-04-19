#!/usr/bin/env python3
"""
scripts/discovery_poc.py — T-D83 Phase 1: On-Chain-Wallet-Discovery PoC

Scant globalen Polymarket-Trade-Stream, sammelt aktive Wallets,
und wendet verfuegbare Hard-Filter (HF-1, HF-2, HF-5, HF-8) an.

Output: analyses/discovery_poc_report.md

Usage:
    python3 scripts/discovery_poc.py
    python3 scripts/discovery_poc.py --pages 30 --top 100
"""
import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import aiohttp
except ImportError:
    print("aiohttp nicht installiert — pip install aiohttp")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
ANALYSES_DIR = BASE_DIR / "analyses"

# ── Konfiguration ──────────────────────────────────────────────────────────────

DATA_API   = "https://data-api.polymarket.com"
CONCURRENT = 8
RATE_DELAY = 0.05   # s zwischen Batches

# Hard-Filter-Schwellen
HF1_MIN_TRADES   = 50        # mindestens 50 Trades in 30 Tagen
HF2_MIN_AGE_DAYS = 60        # Account mind. 60 Tage alt
HF5_MAX_INACTIVE = 14        # letzte Aktivitaet < 14 Tage her
HF8_MIN_WR       = 0.55      # Win-Rate mind. 55 %
HF8_MAX_WR       = 0.75      # Win-Rate max. 75 % (kein manipulierter Edge)

# Aktuelle TARGET_WALLETS (nach Audit v1.0)
CURRENT_TARGETS = {
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b",
    "0x019782cab5d844f02bafb71f512758be78579f3c",
    "0x492442eab586f242b53bda933fd5de859c8a3782",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2",
}


# ── API-Helpers ────────────────────────────────────────────────────────────────

async def _get(session: aiohttp.ClientSession, url: str, params: dict = None) -> list | dict | None:
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return None
            return await r.json(content_type=None)
    except Exception:
        return None


async def _fetch_global_trades(session: aiohttp.ClientSession, pages: int) -> dict:
    """
    Holt `pages*100` globale Trades und liefert aktive Wallets
    mit Metadaten zurueck: {wallet: {trade_count, last_ts}}.
    """
    wallets: dict = {}
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=7)).timestamp()

    for offset in range(0, pages * 100, 100):
        data = await _get(session, f"{DATA_API}/trades", {"limit": 100, "offset": offset})
        if not data:
            break
        for t in data:
            w = (t.get("proxyWallet") or "").lower()
            if not w:
                continue
            ts = t.get("timestamp", 0)
            if ts < cutoff_ts:
                continue  # nur letzte 7 Tage beruecksichtigen
            if w not in wallets:
                wallets[w] = {"trade_count_stream": 0, "last_ts": 0, "name": ""}
            wallets[w]["trade_count_stream"] += 1
            if ts > wallets[w]["last_ts"]:
                wallets[w]["last_ts"] = ts
            if not wallets[w]["name"] and t.get("name"):
                wallets[w]["name"] = t["name"]
        await asyncio.sleep(RATE_DELAY)

    return wallets


async def _fetch_wallet_stats(session: aiohttp.ClientSession, wallet: str) -> dict:
    """
    Holt detaillierte Statistiken fuer eine Wallet:
    - Trades letzte 30 Tage (count)
    - Account-Alter (erste bekannte Aktivitaet)
    - Win-Rate-Schaetzung (REDEEM-unique-conditions / BUY-unique-conditions)
    - cashPnl (aktuelle Positionen)
    """
    now_ts   = datetime.now(timezone.utc).timestamp()
    cutoff30 = now_ts - 30 * 86400

    # 1. Trades letzte 30 Tage
    trades_data = await _get(session, f"{DATA_API}/trades", {"user": wallet, "limit": 500})
    trades_30d    = 0
    oldest_trade  = now_ts
    if trades_data:
        for t in trades_data:
            ts = t.get("timestamp", 0)
            if ts < oldest_trade:
                oldest_trade = ts
            if ts >= cutoff30:
                trades_30d += 1

    # 2. Activity fuer Win-Rate + Account-Alter
    activity_data = await _get(session, f"{DATA_API}/activity", {"user": wallet, "limit": 500})
    bought_conditions: set = set()
    redeemed_conditions: set = set()
    oldest_activity = oldest_trade

    if activity_data:
        for a in activity_data:
            ts  = a.get("timestamp", 0)
            typ = (a.get("type") or "").upper()
            cid = a.get("conditionId", "")
            if ts < oldest_activity:
                oldest_activity = ts

            if typ == "TRADE" and a.get("side", "").upper() == "BUY":
                if cid:
                    bought_conditions.add(cid)
            elif typ == "REDEEM":
                if cid:
                    redeemed_conditions.add(cid)

    # Win-Rate-Schaetzung: unique gewonnene Maerkte / unique gehandelte Maerkte
    win_rate_est = None
    total_traded = len(bought_conditions)
    total_won    = len(redeemed_conditions & bought_conditions)
    if total_traded >= 10:
        win_rate_est = round(total_won / total_traded, 4)

    # Account-Alter: -1 wenn API-Limit (500) getroffen — echtes Alter unbekannt
    activity_limit_hit = activity_data is not None and len(activity_data) >= 500
    trades_limit_hit   = trades_data is not None and len(trades_data) >= 500
    if activity_limit_hit or trades_limit_hit:
        account_age_days = -1   # UNKNOWN — Pagination-Limit erreicht
    else:
        account_age_days = int((now_ts - oldest_activity) / 86400) if oldest_activity < now_ts else 0

    # 3. Aktuelle Positions cashPnl
    pos_data = await _get(session, f"{DATA_API}/positions", {"user": wallet})
    cash_pnl = 0.0
    if pos_data and isinstance(pos_data, list):
        for p in pos_data:
            cash_pnl += float(p.get("cashPnl") or 0)

    return {
        "wallet": wallet,
        "trades_30d": trades_30d,
        "account_age_days": account_age_days,
        "age_unknown": account_age_days == -1,
        "win_rate_est": win_rate_est,
        "total_traded_markets": total_traded,
        "total_won_markets": total_won,
        "cash_pnl": round(cash_pnl, 2),
        "oldest_ts": oldest_activity,
    }


# ── Hard-Filter ────────────────────────────────────────────────────────────────

def _apply_hard_filters(stats: dict, last_ts: float) -> dict:
    now_ts       = datetime.now(timezone.utc).timestamp()
    inactive_days = (now_ts - last_ts) / 86400 if last_ts else 999
    wr            = stats.get("win_rate_est")

    age = stats["account_age_days"]
    if age == -1:
        hf2 = "UNKNOWN(Pagination-Limit — mind. mehrere Tage alt)"
    elif age >= HF2_MIN_AGE_DAYS:
        hf2 = "PASS"
    else:
        hf2 = f"FAIL({age}d < {HF2_MIN_AGE_DAYS}d)"

    results = {
        "HF-1_sample_size": "PASS" if stats["trades_30d"] >= HF1_MIN_TRADES else
                            f"FAIL({stats['trades_30d']} < {HF1_MIN_TRADES})",
        "HF-2_account_age": hf2,
        "HF-5_active_14d":  "PASS" if inactive_days <= HF5_MAX_INACTIVE else
                            f"FAIL({inactive_days:.0f}d inaktiv)",
        "HF-8_win_rate":    (f"PASS({wr:.0%})" if wr and HF8_MIN_WR <= wr <= HF8_MAX_WR else
                            f"FAIL({wr:.0%})" if wr else "UNKNOWN(zu wenig Daten)"),
    }

    fails = [k for k, v in results.items() if v.startswith("FAIL")]
    unknowns = [k for k, v in results.items() if v.startswith("UNKNOWN")]

    if fails:
        verdict = "FAIL"
    elif unknowns and len(unknowns) >= 2:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    return {"filters": results, "verdict": verdict, "fails": fails}


# ── Bericht ────────────────────────────────────────────────────────────────────

def _generate_report(candidates: list, scan_meta: dict) -> str:
    now   = datetime.now(timezone.utc)
    lines = [
        f"# Discovery PoC Report — T-D83 Phase 1",
        f"**Erstellt:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"## Scan-Parameter",
        f"| Parameter | Wert |",
        f"|-----------|------|",
        f"| Globale Trades gescannt | {scan_meta['global_trades_pages']} Seiten × 100 = {scan_meta['global_trades_pages']*100} |",
        f"| Unique aktive Wallets (7 Tage) | {scan_meta['unique_wallets']} |",
        f"| Detailliert analysiert | {scan_meta['analyzed']} |",
        f"| Scan-Dauer | {scan_meta['duration_s']:.0f}s |",
        f"",
        f"## Hard-Filter-Thresholds",
        f"| Filter | Schwelle |",
        f"|--------|----------|",
        f"| HF-1 Sample-Size | ≥ {HF1_MIN_TRADES} Trades/30d |",
        f"| HF-2 Account-Alter | ≥ {HF2_MIN_AGE_DAYS} Tage |",
        f"| HF-5 Aktivität | ≤ {HF5_MAX_INACTIVE} Tage inaktiv |",
        f"| HF-8 Win-Rate | {HF8_MIN_WR:.0%} – {HF8_MAX_WR:.0%} |",
        f"",
    ]

    passing = [c for c in candidates if c["verdict"] == "PASS"]
    review  = [c for c in candidates if c["verdict"] == "REVIEW"]
    failing = [c for c in candidates if c["verdict"] == "FAIL"]

    lines += [
        f"## Ergebnis-Übersicht",
        f"| Kategorie | Anzahl |",
        f"|-----------|--------|",
        f"| PASS (alle verfügbaren HF bestanden) | **{len(passing)}** |",
        f"| REVIEW (UNKNOWN-Filter, manuell prüfen) | {len(review)} |",
        f"| FAIL (mindestens 1 HF versagt) | {len(failing)} |",
        f"",
    ]

    # Top-Kandidaten (PASS + REVIEW, sortiert nach Win-Rate dann Trades)
    top_candidates = sorted(
        [c for c in candidates if c["verdict"] in ("PASS", "REVIEW")],
        key=lambda x: (
            -(x["stats"].get("win_rate_est") or 0),
            -x["stats"].get("trades_30d", 0),
        )
    )[:10]

    lines += [
        f"## Top-10 Kandidaten",
        f"| Wallet | Name | WR% | Trades/30d | Alter(d) | PnL | Bereits TARGET | Verdict |",
        f"|--------|------|-----|------------|----------|-----|----------------|---------|",
    ]

    for c in top_candidates:
        s    = c["stats"]
        w    = c["wallet"]
        name = c.get("name", "")[:16] or w[:8] + "..."
        wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
        pnl  = f"${s['cash_pnl']:+.0f}" if s['cash_pnl'] else "$0"
        in_t = "✅ JA" if w in CURRENT_TARGETS else "❌ NEU"
        lines.append(
            f"| `{w[:8]}...{w[-4:]}` | {name} | {wr} | {s['trades_30d']} | "
            f"{s['account_age_days']} | {pnl} | {in_t} | **{c['verdict']}** |"
        )

    # Neue Kandidaten (nicht in TARGET_WALLETS)
    new_candidates = [c for c in top_candidates if c["wallet"] not in CURRENT_TARGETS]
    lines += [
        f"",
        f"## Neue Kandidaten (nicht in TARGET_WALLETS)",
        f"_Wallets die Filter bestehen UND noch nicht monitort werden:_",
        f"",
    ]
    if new_candidates:
        for c in new_candidates:
            s    = c["stats"]
            w    = c["wallet"]
            name = c.get("name", "") or "unknown"
            wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            lines += [
                f"### {name} (`{w}`)",
                f"- Win-Rate (Schätzung): **{wr}**",
                f"- Trades letzte 30 Tage: **{s['trades_30d']}**",
                f"- Account-Alter: **{s['account_age_days']} Tage**",
                f"- Aktueller cashPnL: **${s['cash_pnl']:+.2f}**",
                f"- HF-1: {c['filters']['HF-1_sample_size']}",
                f"- HF-2: {c['filters']['HF-2_account_age']}",
                f"- HF-5: {c['filters']['HF-5_active_14d']}",
                f"- HF-8: {c['filters']['HF-8_win_rate']}",
                f"- **Verdict: {c['verdict']}**",
                f"",
            ]
    else:
        lines.append("_Keine neuen Kandidaten gefunden — alle PASS-Wallets bereits in TARGET_WALLETS._")

    # HF-8 Win-Rate Verteilung
    wr_distribution = {}
    for c in candidates:
        wr = c["stats"].get("win_rate_est")
        if wr:
            bucket = f"{int(wr*10)*10}%-{int(wr*10)*10+10}%"
            wr_distribution[bucket] = wr_distribution.get(bucket, 0) + 1

    lines += [
        f"",
        f"## Win-Rate-Verteilung (alle analysierten Wallets)",
        f"| Bereich | Anzahl Wallets |",
        f"|---------|----------------|",
    ]
    for bucket, count in sorted(wr_distribution.items()):
        marker = " ← HF-8 Zielbereich" if "50%" in bucket or "60%" in bucket or "70%" in bucket else ""
        lines.append(f"| {bucket} | {count}{marker} |")

    # Fail-Breakdown
    from collections import Counter
    all_fails: list = []
    for c in candidates:
        all_fails.extend(c.get("fails", []))
    fail_counts = Counter(all_fails)

    lines += [
        f"",
        f"## Fail-Breakdown (warum Wallets scheitern)",
        f"| Filter | Anzahl FAILs |",
        f"|--------|-------------|",
    ]
    for hf, cnt in sorted(fail_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {hf} | {cnt} |")

    # Top-10 FAIL-Kandidaten (beste WR, auch wenn sie scheitern)
    top_fail = sorted(
        [c for c in candidates if c["verdict"] == "FAIL"],
        key=lambda x: -(x["stats"].get("win_rate_est") or 0),
    )[:10]
    lines += [
        f"",
        f"## Top-10 FAILs (beste Win-Rate, trotzdem rausgefallen)",
        f"| Wallet | Name | WR% | Trades/30d | Alter(d) | Fail-Grund |",
        f"|--------|------|-----|------------|----------|-----------|",
    ]
    for c in top_fail:
        s    = c["stats"]
        w    = c["wallet"]
        name = (c.get("name") or "")[:14] or w[:8] + "..."
        wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
        age  = "?" if s["account_age_days"] == -1 else str(s["account_age_days"])
        fails_str = ", ".join(c.get("fails", []))
        lines.append(
            f"| `{w[:8]}...{w[-4:]}` | {name} | {wr} | {s['trades_30d']} | {age} | {fails_str} |"
        )

    # Limitierungen & Phase-2-Empfehlung
    lines += [
        f"",
        f"## Bekannte Limitierungen",
        f"1. **API Pagination-Limit (500)**: HF-Trader (BTC/ETH 5-min-Märkte) haben >500 Trades/Tag — ältester sichtbarer Record von heute → Account-Alter nicht bestimmbar. Fix: Pagination oder anderen Age-Endpoint. Aktuell → UNKNOWN statt FAIL.",
        f"2. **Stream dominiert von HFT-Bots**: BTC/ETH 5-min Up/Down Märkte machen Großteil des globalen Trade-Streams aus. Diese Wallets sind nicht sinnvoll zu kopieren. Phase 2: Filter nach market_slug excludiert *-updown-5m-*.",
        f"3. **Win-Rate-Schätzung ungenau**: REDEEM/BUY-Ratio unterschätzt echte WR — nicht alle Verliererpositionen haben explizite SELL-Events. Nur untere Schranke der echten WR.",
        f"4. **Sample-Bias**: Nur Wallets aus den letzten 7 Tagen im globalen Stream erfasst — Wallets die gerade pausieren werden nicht gesehen.",
        f"5. **HF-3, HF-4, HF-6, HF-7, HF-9 nicht auswertbar**: Drawdown, Profit-Konzentration, ROI auf Deposits, Last-Minute-Betting brauchen predicts.guru oder vollständige Handelshistorie.",
        f"6. **Rate-Limiting**: 300 Calls für 100 Wallets. Skalierung auf 1000+ braucht Caching-Layer.",
        f"",
        f"## Phase-2-Machbarkeits-Einschätzung",
        f"",
        f"**API funktioniert** ✅ — Discovery via globalem Trade-Stream ist machbar.",
        f"",
        f"| Komponente | Aufwand | Machbarkeit |",
        f"|------------|---------|-------------|",
        f"| Globaler Scan (1000 Wallets) | 1 Tag | ✅ Hoch |",
        f"| SQLite-Cache für Scan-Ergebnisse | 0.5 Tage | ✅ Hoch |",
        f"| Echte Win-Rate via Market-Resolution | 2 Tage | ⚠️ Mittel (API-Limit) |",
        f"| predicts.guru HF-3/4/6/9 Integration | 1 Tag | ⚠️ Mittel (Scraping) |",
        f"| Automatisierung + Telegram-Alerts | 0.5 Tage | ✅ Hoch |",
        f"| **Gesamt Phase 2** | **~5 Tage** | **Machbar** |",
        f"",
        f"**Empfehlung Phase 2**: SQLite-Cache + tägl. Scan von 500 Wallets + manuelle Freigabe per Telegram-Button bevor neue Wallet in TARGET_WALLETS aufgenommen wird.",
    ]

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(pages: int = 20, top: int = 100) -> None:
    t_start = time.time()
    print(f"🔍 Discovery PoC — T-D83 Phase 1")
    print(f"   Pages: {pages} ({pages*100} globale Trades) | Top: {top} Wallets")

    headers = {"User-Agent": "KongTradeBot/Discovery-PoC"}
    conn    = aiohttp.TCPConnector(limit=CONCURRENT)

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:

        # Phase 1: Globale Wallets sammeln
        print(f"\n[1/3] Globalen Trade-Stream scannen...")
        wallet_stream = await _fetch_global_trades(session, pages=pages)
        print(f"  → {len(wallet_stream)} unique Wallets gefunden (aktiv letzte 7 Tage)")

        # Top-N nach Trade-Count im Stream (als Aktivitäts-Proxy)
        sorted_wallets = sorted(
            wallet_stream.items(),
            key=lambda x: -x[1]["trade_count_stream"]
        )[:top]
        print(f"  → Analysiere Top-{len(sorted_wallets)} aktivste Wallets")

        # Phase 2: Detaillierte Stats parallel holen
        print(f"\n[2/3] Detaillierte Wallet-Stats abrufen (je 3 API-Calls)...")
        semaphore = asyncio.Semaphore(CONCURRENT)

        async def _bounded_fetch(wallet: str):
            async with semaphore:
                stats = await _fetch_wallet_stats(session, wallet)
                await asyncio.sleep(RATE_DELAY)
                return stats

        tasks   = [_bounded_fetch(w) for w, _ in sorted_wallets]
        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            stats = await coro
            results.append(stats)
            if i % 10 == 0:
                print(f"  → {i}/{len(tasks)} abgeschlossen...")

        print(f"  → {len(results)} Wallets analysiert")

        # Phase 3: Hard-Filter anwenden
        print(f"\n[3/3] Hard-Filter anwenden...")
        candidates = []
        for stats in results:
            wallet = stats["wallet"]
            last_ts = wallet_stream.get(wallet, {}).get("last_ts", 0)
            name    = wallet_stream.get(wallet, {}).get("name", "")
            hf      = _apply_hard_filters(stats, last_ts)
            candidates.append({
                "wallet":  wallet,
                "name":    name,
                "stats":   stats,
                "filters": hf["filters"],
                "verdict": hf["verdict"],
                "fails":   hf["fails"],
            })

        pass_count   = sum(1 for c in candidates if c["verdict"] == "PASS")
        review_count = sum(1 for c in candidates if c["verdict"] == "REVIEW")
        fail_count   = sum(1 for c in candidates if c["verdict"] == "FAIL")
        new_pass     = sum(1 for c in candidates if c["verdict"] == "PASS" and c["wallet"] not in CURRENT_TARGETS)

        print(f"  PASS:   {pass_count}  ({new_pass} davon NEU / nicht in TARGET_WALLETS)")
        print(f"  REVIEW: {review_count}")
        print(f"  FAIL:   {fail_count}")

    duration = time.time() - t_start
    scan_meta = {
        "global_trades_pages": pages,
        "unique_wallets":      len(wallet_stream),
        "analyzed":            len(results),
        "duration_s":          duration,
    }

    # Report generieren
    report_md = _generate_report(candidates, scan_meta)
    ANALYSES_DIR.mkdir(exist_ok=True)
    ts_str    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path  = ANALYSES_DIR / f"discovery_poc_{ts_str}.md"
    out_path.write_text(report_md, encoding="utf-8")
    print(f"\n✅ Report gespeichert: {out_path}")
    print(f"   Dauer: {duration:.0f}s")

    # Kurze Konsolen-Zusammenfassung
    top_candidates = sorted(
        [c for c in candidates if c["verdict"] in ("PASS", "REVIEW")],
        key=lambda x: (-(x["stats"].get("win_rate_est") or 0), -x["stats"].get("trades_30d", 0))
    )[:5]
    if top_candidates:
        print(f"\nTop-5 Kandidaten:")
        for c in top_candidates:
            s = c["stats"]
            wr = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            in_t = "IN_TARGET" if c["wallet"] in CURRENT_TARGETS else "NEU"
            print(f"  {c['wallet'][:10]}...{c['wallet'][-4:]} | WR={wr} | "
                  f"Trades30d={s['trades_30d']} | Alter={s['account_age_days']}d | {in_t} | {c['verdict']}")


def _cli_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=20,
                        help="Seiten globaler Trades (je 100, default=20 → 2000 Trades)")
    parser.add_argument("--top",   type=int, default=100,
                        help="Top-N aktivste Wallets detailliert analysieren (default=100)")
    args = parser.parse_args()
    asyncio.run(main(pages=args.pages, top=args.top))


if __name__ == "__main__":
    _cli_main()
