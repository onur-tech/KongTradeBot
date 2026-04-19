#!/usr/bin/env python3
"""
scripts/discovery_poc_v2.py — T-D83 Phase 1.5: Category-driven Wallet Discovery

Phase 1 used the global trade stream and found only HFT-bots.
Phase 1.5 fixes three root causes:
  1. Category-driven market scan (Politics / Macro / Culture) via Gamma API
  2. HF-10 hard-filter: blocks HFT bots before detail-analysis
  3. 60-day data window + paginated activity for better account-age estimation

Output: analyses/discovery_phase_1_5_YYYY-MM-DD.md

Usage:
    python3 scripts/discovery_poc_v2.py
    python3 scripts/discovery_poc_v2.py --events 400 --top 80
"""
import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter, defaultdict
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

# ── Config ─────────────────────────────────────────────────────────────────────

GAMMA_API   = "https://gamma-api.polymarket.com"
DATA_API    = "https://data-api.polymarket.com"
CONCURRENT  = 8
RATE_DELAY  = 0.05

# Hard-filter thresholds
HF1_MIN_TRADES    = 50
HF2_MIN_AGE_DAYS  = 60
HF5_MAX_INACTIVE  = 14
HF8_MIN_WR        = 0.55
HF8_MAX_WR        = 0.75
HF10_MAX_HFT_FRAC = 0.50   # >50 % HFT trades → bot
HF10_MAX_TPD      = 100    # >100 trades/day average → bot

# Volume range for "niche" markets
MARKET_VOL_MIN = 25_000
MARKET_VOL_MAX = 3_000_000

# Category regex patterns (matched against event slug)
CATEGORY_RE: dict[str, re.Pattern] = {
    "politics": re.compile(
        r"trump|election|president|senate|tariff|ukraine|russia|nato|iran|"
        r"china|prime-minister|ceasefire|vote-|canada|israel|mexico|trade-war|"
        r"modi|macron|xi-jinping|putin|zelensky|kim-jong|peace-deal|sanctions|"
        r"democrat|republican|congress|parliament|referendum|general-election|"
        r"gubernatorial|midterm|brexit|erdogan|orban|lula|milei",
        re.I,
    ),
    "macro": re.compile(
        r"fed-|rate-cut|inflation|gdp|recession|interest-rate|national-debt|"
        r"gold-price|crude-oil|sp500|dow-jones|nasdaq|yield-curve|cpi-|pce-|"
        r"unemployment|housing-market|federal-reserve|treasury|oecd|imf-",
        re.I,
    ),
    "culture": re.compile(
        r"oscar|emmy|grammy|noble-prize|nobel|climate|carbon|ai-model|"
        r"artificial-intellig|openai|elon-musk|spacex|moon-|nasa|nuclear-|"
        r"celebrity|box-office|streaming|music-award|film-award|tech-ipo|"
        r"cryptocurrency-regulation|stablecoin|crypto-etf",
        re.I,
    ),
}

HFT_RE = re.compile(
    r"updown-5m|updown-15m|updown-1h|btc-updown|eth-updown|price-up-or-down|"
    r"bitcoin-price-up|ethereum-price-up",
    re.I,
)
SPORTS_RE = re.compile(
    r"\bnba\b|\bnfl\b|\bnhl\b|\bmlb\b|soccer-|tennis-|\bmma\b|\bufc\b|"
    r"-golf-|-dota2?-|-lol-|-cs2-|-valorant-|chess-match|cricket-|rugby-|"
    r"game1-|game2-|game3-|kill-over|map-winner|-esport",
    re.I,
)

# Current TARGET_WALLETS (Audit v1.0)
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


# ── API helpers ────────────────────────────────────────────────────────────────

async def _get(session: aiohttp.ClientSession, url: str, params: dict = None):
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            return await r.json(content_type=None)
    except Exception:
        return None


def _classify_slug(slug: str) -> str | None:
    if HFT_RE.search(slug) or SPORTS_RE.search(slug):
        return None
    for cat, pat in CATEGORY_RE.items():
        if pat.search(slug):
            return cat
    return None


# ── Phase 1: Market-based wallet collection ────────────────────────────────────

async def _fetch_qualifying_markets(session: aiohttp.ClientSession, max_events: int) -> list[dict]:
    """
    Fetches events from Gamma API, filters by category + volume, extracts
    (event_slug, category, token_id) tuples for trade-level scanning.
    """
    all_events: list[dict] = []
    batch = 100
    for offset in range(0, max_events, batch):
        data = await _get(session, f"{GAMMA_API}/events",
                          {"limit": batch, "offset": offset, "active": "true", "closed": "false"})
        if not data:
            break
        all_events.extend(data)
        await asyncio.sleep(RATE_DELAY)

    qualifying: list[dict] = []
    seen_tokens: set = set()

    for event in all_events:
        slug = event.get("slug", "")
        category = _classify_slug(slug)
        if category is None:
            continue

        markets = event.get("markets", [])
        if not markets:
            continue

        for mkt in markets:
            vol = float(mkt.get("volumeNum") or mkt.get("volume") or 0)
            if not (MARKET_VOL_MIN <= vol <= MARKET_VOL_MAX):
                continue

            raw_ids = mkt.get("clobTokenIds", "[]")
            try:
                token_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else (raw_ids or [])
            except Exception:
                continue

            for tid in token_ids[:2]:  # YES + NO tokens
                if tid and tid not in seen_tokens:
                    seen_tokens.add(tid)
                    qualifying.append({
                        "event_slug": slug,
                        "market_slug": mkt.get("slug", ""),
                        "category":   category,
                        "volume":     vol,
                        "token_id":   tid,
                    })

    return qualifying


async def _collect_wallets_from_markets(
    session: aiohttp.ClientSession,
    markets: list[dict],
    semaphore: asyncio.Semaphore,
) -> dict[str, dict]:
    """
    For each qualifying market token, fetches last 100 trades and records
    wallet → {category_counts, trade_count, last_ts, name}.
    """
    wallet_data: dict[str, dict] = {}

    async def _fetch_one(mkt: dict):
        async with semaphore:
            trades = await _get(session, f"{DATA_API}/trades",
                                {"asset_id": mkt["token_id"], "limit": 100})
            await asyncio.sleep(RATE_DELAY)
            if not trades:
                return
            cat = mkt["category"]
            for t in trades:
                w = (t.get("proxyWallet") or "").lower()
                if not w:
                    continue
                ts = t.get("timestamp", 0)
                if w not in wallet_data:
                    wallet_data[w] = {
                        "category_counts": Counter(),
                        "trade_count": 0,
                        "last_ts": 0,
                        "name": "",
                    }
                wallet_data[w]["category_counts"][cat] += 1
                wallet_data[w]["trade_count"] += 1
                if ts > wallet_data[w]["last_ts"]:
                    wallet_data[w]["last_ts"] = ts
                if not wallet_data[w]["name"] and t.get("name"):
                    wallet_data[w]["name"] = t["name"]

    tasks = [_fetch_one(m) for m in markets]
    await asyncio.gather(*tasks)
    return wallet_data


# ── Phase 2: HF-10 pre-filter ──────────────────────────────────────────────────

async def _check_hft(session: aiohttp.ClientSession, wallet: str) -> dict:
    """
    Fetches wallet's last 500 trades and checks HFT fraction + trades/day.
    Returns {hft_frac, trades_per_day, is_bot}.
    """
    data = await _get(session, f"{DATA_API}/trades", {"user": wallet, "limit": 500})
    if not data:
        return {"hft_frac": 0.0, "trades_per_day": 0.0, "is_bot": False}

    total = len(data)
    hft_count = sum(
        1 for t in data if HFT_RE.search(t.get("eventSlug", "") or t.get("slug", "") or "")
    )
    hft_frac = hft_count / total if total > 0 else 0.0

    if total >= 2:
        ts_list = [t.get("timestamp", 0) for t in data if t.get("timestamp")]
        if len(ts_list) >= 2:
            span_days = (max(ts_list) - min(ts_list)) / 86400
            tpd = total / max(span_days, 0.1)
        else:
            tpd = 0.0
    else:
        tpd = 0.0

    is_bot = hft_frac > HF10_MAX_HFT_FRAC or tpd > HF10_MAX_TPD
    return {"hft_frac": round(hft_frac, 3), "trades_per_day": round(tpd, 1), "is_bot": is_bot}


# ── Phase 3: Detailed wallet stats ─────────────────────────────────────────────

async def _fetch_wallet_stats(session: aiohttp.ClientSession, wallet: str) -> dict:
    """
    Collects detailed stats for hard-filter evaluation.
    Uses paginated activity (up to 1500 records) for 60-day coverage + account-age.
    """
    now_ts   = datetime.now(timezone.utc).timestamp()
    cutoff60 = now_ts - 60 * 86400

    # 1. Trades last 60 days
    trades_data = await _get(session, f"{DATA_API}/trades", {"user": wallet, "limit": 500})
    trades_60d   = 0
    oldest_trade = now_ts
    if trades_data:
        for t in trades_data:
            ts = t.get("timestamp", 0)
            if ts and ts < oldest_trade:
                oldest_trade = ts
            if ts and ts >= cutoff60:
                trades_60d += 1
    trades_limit_hit = (trades_data is not None and len(trades_data) >= 500)

    # 2. Paginated activity (up to 3 batches = 1500 records)
    bought_conditions: set  = set()
    redeemed_conditions: set = set()
    oldest_activity = oldest_trade
    activity_exhausted = False  # True if we fetched < 500 in a batch (ran out)

    for batch_offset in range(0, 1500, 500):
        batch = await _get(session, f"{DATA_API}/activity",
                           {"user": wallet, "limit": 500, "offset": batch_offset})
        await asyncio.sleep(0.02)
        if not batch:
            activity_exhausted = True
            break

        for a in batch:
            ts  = a.get("timestamp", 0)
            typ = (a.get("type") or "").upper()
            cid = a.get("conditionId", "")
            if ts and ts < oldest_activity:
                oldest_activity = ts

            if typ == "TRADE" and (a.get("side") or "").upper() == "BUY" and cid:
                bought_conditions.add(cid)
            elif typ == "REDEEM" and cid:
                redeemed_conditions.add(cid)

        if len(batch) < 500:  # last page reached
            activity_exhausted = True
            break

    # Account age
    if activity_exhausted or not trades_limit_hit:
        account_age_days = int((now_ts - oldest_activity) / 86400) if oldest_activity < now_ts else 0
        age_unknown = False
    else:
        account_age_days = -1  # pagination limit → unknown
        age_unknown = True

    # Win-rate estimate
    total_traded = len(bought_conditions)
    total_won    = len(redeemed_conditions & bought_conditions)
    win_rate_est = round(total_won / total_traded, 4) if total_traded >= 10 else None

    # Positions cashPnL
    pos_data = await _get(session, f"{DATA_API}/positions", {"user": wallet})
    cash_pnl = 0.0
    if pos_data and isinstance(pos_data, list):
        for p in pos_data:
            cash_pnl += float(p.get("cashPnl") or 0)

    return {
        "wallet":            wallet,
        "trades_60d":        trades_60d,
        "account_age_days":  account_age_days,
        "age_unknown":       age_unknown,
        "win_rate_est":      win_rate_est,
        "total_traded_mkts": total_traded,
        "total_won_mkts":    total_won,
        "cash_pnl":          round(cash_pnl, 2),
        "oldest_ts":         oldest_activity,
    }


# ── Phase 4: Hard filters ──────────────────────────────────────────────────────

def _apply_hard_filters(stats: dict, hft: dict, last_ts: float, cat_focus: dict) -> dict:
    now_ts       = datetime.now(timezone.utc).timestamp()
    inactive_days = (now_ts - last_ts) / 86400 if last_ts else 999
    wr            = stats.get("win_rate_est")
    age           = stats["account_age_days"]

    if age == -1:
        hf2 = "UNKNOWN(Pagination-Limit)"
    elif age >= HF2_MIN_AGE_DAYS:
        hf2 = "PASS"
    else:
        hf2 = f"FAIL({age}d < {HF2_MIN_AGE_DAYS}d)"

    if wr is None:
        hf8 = "UNKNOWN(zu wenig Daten)"
    elif HF8_MIN_WR <= wr <= HF8_MAX_WR:
        hf8 = f"PASS({wr:.0%})"
    else:
        hf8 = f"FAIL({wr:.0%})"

    results = {
        "HF-1_sample_size":  ("PASS" if stats["trades_60d"] >= HF1_MIN_TRADES
                              else f"FAIL({stats['trades_60d']} < {HF1_MIN_TRADES})"),
        "HF-2_account_age":  hf2,
        "HF-5_active_14d":   ("PASS" if inactive_days <= HF5_MAX_INACTIVE
                              else f"FAIL({inactive_days:.0f}d inaktiv)"),
        "HF-8_win_rate":     hf8,
        "HF-10_no_hft_bot":  ("PASS" if not hft["is_bot"]
                              else f"FAIL(HFT={hft['hft_frac']:.0%} TPD={hft['trades_per_day']:.0f})"),
    }

    fails    = [k for k, v in results.items() if v.startswith("FAIL")]
    unknowns = [k for k, v in results.items() if v.startswith("UNKNOWN")]

    if fails:
        verdict = "FAIL"
    elif len(unknowns) >= 2:
        verdict = "REVIEW"
    elif unknowns:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    return {"filters": results, "verdict": verdict, "fails": fails, "unknowns": unknowns}


# ── Category focus + Archetyp ──────────────────────────────────────────────────

def _compute_category_focus(cat_counts: Counter) -> dict:
    total = sum(cat_counts.values())
    if not total:
        return {"top_category": "unknown", "focus_frac": 0.0, "breakdown": {}}
    top_cat = cat_counts.most_common(1)[0][0]
    top_cnt = cat_counts[top_cat]
    focus_frac = top_cnt / total
    return {
        "top_category": top_cat,
        "focus_frac":   round(focus_frac, 3),
        "breakdown":    dict(cat_counts),
    }


def _classify_archetyp(stats: dict, hft: dict, focus: dict) -> str:
    cat  = focus["top_category"]
    frac = focus["focus_frac"]
    wr   = stats.get("win_rate_est") or 0.0

    if frac >= 0.70:
        return f"{cat.capitalize()}-Spezialist"
    elif frac >= 0.50:
        return f"{cat.capitalize()}-Fokus (Generalist-Tendenz)"
    else:
        return "Diversifizierter Generalist"


# ── Report generation ──────────────────────────────────────────────────────────

def _generate_report(candidates: list, scan_meta: dict) -> str:
    now   = datetime.now(timezone.utc)
    lines = [
        "# Discovery Phase 1.5 Report — T-D83",
        f"**Erstellt:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Scan-Konfiguration",
        "| Parameter | Wert |",
        "|-----------|------|",
        f"| Events gescannt (Gamma API) | {scan_meta['events_fetched']} |",
        f"| Qualifying Markets (HF-10 pre) | {scan_meta['qualifying_markets']} |",
        f"| Unique Wallets gesammelt | {scan_meta['wallets_collected']} |",
        f"| Nach HF-10 ausgeschlossen | {scan_meta['hft_excluded']} |",
        f"| Detailliert analysiert | {scan_meta['analyzed']} |",
        f"| Scan-Dauer | {scan_meta['duration_s']:.0f}s |",
        "",
        "## Kategorien gescannt",
        "| Kategorie | Qualifying Markets | Wallets beigesteuert |",
        "|-----------|------------------|---------------------|",
    ]
    for cat, cnt in sorted(scan_meta.get("category_market_counts", {}).items()):
        w_cnt = scan_meta.get("category_wallet_counts", {}).get(cat, 0)
        lines.append(f"| {cat} | {cnt} | {w_cnt} |")

    passing = [c for c in candidates if c["verdict"] == "PASS"]
    review  = [c for c in candidates if c["verdict"] == "REVIEW"]
    failing = [c for c in candidates if c["verdict"] == "FAIL"]
    new_pass = [c for c in passing if c["wallet"] not in CURRENT_TARGETS]

    lines += [
        "",
        "## Ergebnis-Übersicht",
        "| Kategorie | Anzahl |",
        "|-----------|--------|",
        f"| PASS | **{len(passing)}** ({len(new_pass)} NEU / nicht in TARGET_WALLETS) |",
        f"| REVIEW | {len(review)} |",
        f"| FAIL | {len(failing)} |",
        "",
        "## PASS-Kandidaten",
    ]

    if passing:
        lines += [
            "| Wallet | Name | Archetyp | WR% | Trades/60d | Alter(d) | cashPnL | TARGET? |",
            "|--------|------|---------|-----|------------|----------|---------|---------|",
        ]
        for c in sorted(passing, key=lambda x: -(x["stats"].get("win_rate_est") or 0)):
            s    = c["stats"]
            w    = c["wallet"]
            name = (c.get("name") or "")[:16] or (w[:8] + "...")
            wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            age  = "?" if s["account_age_days"] == -1 else str(s["account_age_days"])
            pnl  = f"${s['cash_pnl']:+.0f}"
            in_t = "✅" if w in CURRENT_TARGETS else "❌ NEU"
            arch = c.get("archetyp", "?")
            lines.append(
                f"| `{w[:8]}...{w[-4:]}` | {name} | {arch} | {wr} | "
                f"{s['trades_60d']} | {age} | {pnl} | {in_t} |"
            )
    else:
        lines.append("_Keine PASS-Kandidaten gefunden._")

    # Per-PASS detailed breakdown
    for c in passing:
        s    = c["stats"]
        w    = c["wallet"]
        name = c.get("name") or "unknown"
        wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
        age  = "UNKNOWN (Pagination-Limit)" if s["account_age_days"] == -1 else f"{s['account_age_days']} Tage"
        f    = c["filters"]
        focus = c.get("category_focus", {})
        hft   = c.get("hft", {})

        lines += [
            "",
            f"### {name} (`{w}`)",
            f"- **Archetyp**: {c.get('archetyp', '?')}",
            f"- **Kategorie-Fokus**: {focus.get('top_category','?')} — {focus.get('focus_frac',0):.0%} der Category-Trades",
            f"- Kategorie-Breakdown: {focus.get('breakdown',{})}",
            f"- Win-Rate (Schätzung): **{wr}**",
            f"- Trades letzte 60 Tage: **{s['trades_60d']}**",
            f"- Account-Alter: **{age}**",
            f"- HFT-Anteil eigener Trades: **{hft.get('hft_frac',0):.0%}** (Trades/Tag: {hft.get('trades_per_day',0):.1f})",
            f"- cashPnL: **${s['cash_pnl']:+.2f}**",
            f"- HF-1: {f['HF-1_sample_size']}",
            f"- HF-2: {f['HF-2_account_age']}",
            f"- HF-5: {f['HF-5_active_14d']}",
            f"- HF-8: {f['HF-8_win_rate']}",
            f"- HF-10: {f['HF-10_no_hft_bot']}",
            f"- **Verdict: {c['verdict']}**",
            "",
        ]

    # REVIEW section (abbreviated)
    if review:
        lines += [
            "## REVIEW-Kandidaten (UNKNOWN-Filter — manuell prüfen)",
            "| Wallet | Name | Archetyp | WR% | Trades/60d | Alter | UNKNOWN-Filter |",
            "|--------|------|---------|-----|------------|-------|----------------|",
        ]
        for c in sorted(review, key=lambda x: -(x["stats"].get("win_rate_est") or 0))[:10]:
            s       = c["stats"]
            w       = c["wallet"]
            name    = (c.get("name") or "")[:14] or w[:8]
            wr      = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            age     = "?" if s["account_age_days"] == -1 else str(s["account_age_days"])
            unknowns = ", ".join(c.get("unknowns", []))
            arch    = c.get("archetyp", "?")
            lines.append(
                f"| `{w[:8]}...{w[-4:]}` | {name} | {arch} | {wr} | "
                f"{s['trades_60d']} | {age} | {unknowns} |"
            )

    # Fail breakdown
    from collections import Counter as _Counter
    all_fails = []
    for c in candidates:
        all_fails.extend(c.get("fails", []))
    fail_counts = _Counter(all_fails)

    lines += [
        "",
        "## Fail-Breakdown",
        "| Filter | Anzahl FAILs |",
        "|--------|-------------|",
    ]
    for hf, cnt in sorted(fail_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {hf} | {cnt} |")

    # Win-rate distribution
    wr_dist: dict[str, int] = {}
    for c in candidates:
        wr = c["stats"].get("win_rate_est")
        if wr is not None:
            bucket = f"{int(wr * 10) * 10}%-{int(wr * 10) * 10 + 10}%"
            wr_dist[bucket] = wr_dist.get(bucket, 0) + 1

    lines += [
        "",
        "## Win-Rate-Verteilung",
        "| Bereich | Wallets |",
        "|---------|---------|",
    ]
    for b, cnt in sorted(wr_dist.items()):
        marker = " ← HF-8 Zielbereich" if any(x in b for x in ["50%", "60%", "70%"]) else ""
        lines.append(f"| {b} | {cnt}{marker} |")

    lines += [
        "",
        "## Bekannte Limitierungen",
        "1. **Account-Alter**: Ohne Polygonscan API-Key nur via Aktivitäts-Pagination bestimmbar.",
        "   3×500 Records = max 1500 Events. Sehr aktive Wallets bleiben UNKNOWN.",
        "2. **Gamma API Volume**: Feld enthält Gesamt-Lifetime-Volumen (nicht nur aktiv).",
        "   Nischen-Filter $25k-$3M trifft deshalb teils historische Märkte.",
        "3. **Category-Zuordnung**: Keyword-basiert — False-Positives möglich.",
        "4. **HF-10 Schwelle**: 50% HFT ist konservativ. Legitime Multi-Strategy-Trader könnten ausgeschlossen werden.",
        "5. **Win-Rate-Schätzung**: REDEEM/BUY-Ratio = untere Schranke. Echte WR vermutlich höher.",
        "6. **HF-3,4,6,7,9 fehlen**: Drawdown, Profit-Konzentration, ROI brauchen predicts.guru.",
        "",
        "## Phase-2-Machbarkeits-Einschätzung",
        "",
        "| Komponente | Phase 1.5 Status | Phase 2 Bedarf |",
        "|------------|-----------------|----------------|",
        "| Kategorie-Scan (Gamma API) | ✅ Implementiert | Mehr Kategorien, Zeitfenster |",
        "| HFT-Filter (HF-10) | ✅ Implementiert | Schwelle tunen |",
        "| Account-Alter | ⚠️ Pagination-basiert | Polygonscan API Key |",
        "| Win-Rate | ⚠️ REDEEM-Schätzung | Market-Resolution API |",
        "| HF-3/4/6/7/9 | ❌ Nicht implementiert | predicts.guru Integration |",
        "| Telegram-Alert | ❌ Nicht implementiert | 0.5 Tage |",
        "",
        "**Empfehlung**: Polygonscan API Key (kostenlos) in .env eintragen → HF-2 für alle Wallets lösbar.",
        "Phase 2 Gesamtaufwand: ~4 Tage (reduziert dank Phase 1.5 Erkenntnissen).",
    ]

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

async def main(max_events: int = 400, top: int = 80) -> None:
    t_start = time.time()
    print("🔍 Discovery PoC v2 — T-D83 Phase 1.5")
    print(f"   Events: {max_events} | Top Wallets: {top}")

    headers = {"User-Agent": "KongTradeBot/DiscoveryPoC-v2"}
    conn    = aiohttp.TCPConnector(limit=CONCURRENT * 2)

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        semaphore = asyncio.Semaphore(CONCURRENT)

        # ── Phase 1A: Category-driven market scan ──────────────────────────────
        print("\n[1/4] Kategorie-Märkte via Gamma API scannen...")
        qualifying_markets = await _fetch_qualifying_markets(session, max_events)
        cat_counts = Counter(m["category"] for m in qualifying_markets)
        print(f"  → {max_events} Events gescannt")
        for cat, cnt in sorted(cat_counts.items()):
            print(f"     {cat}: {cnt} Tokens aus Qualifying-Märkten")

        if not qualifying_markets:
            print("  ⚠️  Keine qualifying markets gefunden — prüfe Volume-Filter")
            return

        # ── Phase 1B: Collect wallets from those markets ───────────────────────
        print("\n[2/4] Wallets aus Kategorie-Märkten sammeln...")
        wallet_stream = await _collect_wallets_from_markets(session, qualifying_markets, semaphore)
        print(f"  → {len(wallet_stream)} unique Wallets gesammelt")

        cat_wallet_counts = {}
        for cat in CATEGORY_RE:
            cnt = sum(1 for wd in wallet_stream.values() if wd["category_counts"].get(cat, 0) > 0)
            cat_wallet_counts[cat] = cnt

        # ── Phase 2: HF-10 pre-filter on top-N wallets ────────────────────────
        sorted_wallets = sorted(
            wallet_stream.items(),
            key=lambda x: -x[1]["trade_count"]
        )[:top]

        print(f"\n[3/4] HF-10 Bot-Filter auf Top-{len(sorted_wallets)} Wallets...")

        async def _bounded_hft(wallet: str):
            async with semaphore:
                result = await _check_hft(session, wallet)
                await asyncio.sleep(RATE_DELAY)
                return wallet, result

        hft_tasks   = [_bounded_hft(w) for w, _ in sorted_wallets]
        hft_results = {}
        for coro in asyncio.as_completed(hft_tasks):
            w, hft = await coro
            hft_results[w] = hft

        surviving = [(w, wd) for w, wd in sorted_wallets if not hft_results.get(w, {}).get("is_bot")]
        excluded  = len(sorted_wallets) - len(surviving)
        print(f"  → {excluded} HFT-Bots ausgeschlossen")
        print(f"  → {len(surviving)} Wallets für Detail-Analyse")

        # ── Phase 3: Detailed stats ────────────────────────────────────────────
        print(f"\n[4/4] Detaillierte Stats + Hard-Filter für {len(surviving)} Wallets...")

        async def _bounded_stats(wallet: str):
            async with semaphore:
                stats = await _fetch_wallet_stats(session, wallet)
                await asyncio.sleep(RATE_DELAY)
                return stats

        stat_tasks = [_bounded_stats(w) for w, _ in surviving]
        stats_list = []
        for i, coro in enumerate(asyncio.as_completed(stat_tasks), 1):
            stats = await coro
            stats_list.append(stats)
            if i % 10 == 0:
                print(f"  → {i}/{len(surviving)} abgeschlossen...")

        # ── Phase 4: Apply filters + build candidates ──────────────────────────
        candidates = []
        for stats in stats_list:
            wallet    = stats["wallet"]
            stream_d  = wallet_stream.get(wallet, {})
            hft       = hft_results.get(wallet, {})
            last_ts   = stream_d.get("last_ts", 0)
            name      = stream_d.get("name", "")
            cat_cnts  = stream_d.get("category_counts", Counter())
            focus     = _compute_category_focus(cat_cnts)
            hf        = _apply_hard_filters(stats, hft, last_ts, focus)
            archetyp  = _classify_archetyp(stats, hft, focus)

            candidates.append({
                "wallet":         wallet,
                "name":           name,
                "stats":          stats,
                "hft":            hft,
                "filters":        hf["filters"],
                "verdict":        hf["verdict"],
                "fails":          hf["fails"],
                "unknowns":       hf["unknowns"],
                "category_focus": focus,
                "archetyp":       archetyp,
            })

        pass_count   = sum(1 for c in candidates if c["verdict"] == "PASS")
        review_count = sum(1 for c in candidates if c["verdict"] == "REVIEW")
        fail_count   = sum(1 for c in candidates if c["verdict"] == "FAIL")
        new_pass     = sum(1 for c in candidates if c["verdict"] == "PASS" and c["wallet"] not in CURRENT_TARGETS)

        duration = time.time() - t_start
        print(f"\n  PASS:   {pass_count}  ({new_pass} NEU)")
        print(f"  REVIEW: {review_count}")
        print(f"  FAIL:   {fail_count}")

        # Print top-5 summary
        top5 = sorted(
            [c for c in candidates if c["verdict"] in ("PASS", "REVIEW")],
            key=lambda x: -(x["stats"].get("win_rate_est") or 0),
        )[:5]
        if top5:
            print("\nTop-5 Kandidaten:")
            for c in top5:
                s    = c["stats"]
                age  = "?" if s["account_age_days"] == -1 else f"{s['account_age_days']}d"
                arch = c.get("archetyp", "?")
                tgt  = "TARGET" if c["wallet"] in CURRENT_TARGETS else "NEU"
                wr_str = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
                print(
                    f"  {c['wallet'][:8]}...{c['wallet'][-4:]} | "
                    f"WR={wr_str} | Trades60d={s['trades_60d']} | Alter={age} | "
                    f"{arch} | {tgt} | {c['verdict']}"
                )

        scan_meta = {
            "events_fetched":        max_events,
            "qualifying_markets":    len(qualifying_markets),
            "wallets_collected":     len(wallet_stream),
            "hft_excluded":          excluded,
            "analyzed":              len(surviving),
            "duration_s":            duration,
            "category_market_counts": dict(cat_counts),
            "category_wallet_counts": cat_wallet_counts,
        }

        report = _generate_report(candidates, scan_meta)
        ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
        report_path = ANALYSES_DIR / f"discovery_phase_1_5_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"\n✅ Report: {report_path}")
        print(f"   Dauer: {duration:.0f}s")


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--events", type=int, default=400)
    p.add_argument("--top",    type=int, default=80)
    args = p.parse_args()
    asyncio.run(main(max_events=args.events, top=args.top))


if __name__ == "__main__":
    _cli()
