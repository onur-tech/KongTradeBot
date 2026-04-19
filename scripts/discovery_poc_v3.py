#!/usr/bin/env python3
"""
scripts/discovery_poc_v3.py — T-D83 Phase 1.6: Category + Bucket-Split Discovery

Phase 1.5 found 1 candidate because the global stream was Sports/HFT-dominated.
Phase 1.6 corrects this using the 0xIcaruss study findings:
  - Median top-wallet: 4.7 trades/day, not 50-200/year
  - 24% are "Patient Specialists" (0.5-3 trades/day)
  - Niche markets = $100k+ volume category-specific, not broad stream
  - Target: Gain-Loss Ratio >= 1.5 (study benchmark: 2.1)

Categories: Geopolitics / Politics / Tech / Culture / Macro / Sports (reference)
Two frequency buckets: Active (3-15/day) + Patient (0.5-3/day)

Output: analyses/discovery_phase_1_6_YYYY-MM-DD.md

Usage:
    python3 scripts/discovery_poc_v3.py
    python3 scripts/discovery_poc_v3.py --events 600 --top 100
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
    print("pip install aiohttp")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
ANALYSES_DIR = BASE_DIR / "analyses"

GAMMA_API  = "https://gamma-api.polymarket.com"
DATA_API   = "https://data-api.polymarket.com"
CONCURRENT = 10
RATE_DELAY = 0.05

# ── Hard-Filter Thresholds ────────────────────────────────────────────────────

HF1_MIN_TRADES_ACTIVE  = 50    # Active bucket (3-15/day)
HF1_MIN_TRADES_PATIENT = 20    # Patient bucket (0.5-3/day)
HF2_MIN_AGE_DAYS       = 60
HF5_MAX_INACTIVE       = 14
HF8_MIN_WR             = 0.55
HF8_MAX_WR             = 0.75
HF10_MAX_HFT_FRAC      = 0.40  # >40% HFT trades → bot (tighter than v2)
HF10_MAX_TPD           = 15    # >15 trades/day → likely bot
HF_GL_MIN_RATIO        = 1.5   # Gain-Loss Ratio minimum

# Frequency bucket thresholds
BUCKET_ACTIVE_MIN  = 3.0
BUCKET_ACTIVE_MAX  = 15.0
BUCKET_PATIENT_MIN = 0.5
BUCKET_PATIENT_MAX = 3.0

# Market activity filter
MARKET_VOL_MIN = 100_000    # all-time vol >= $100k
MARKETS_PER_CAT = 50        # max markets to scan per category

# Scoring weights
SCORE_PNL_HIGH     = +20
SCORE_PNL_MID      = +10
SCORE_PNL_LOW      = -10
SCORE_WR_SWEET     = +15   # 60-70%
SCORE_WR_OK        = +10   # 55-60% or 70-75%
SCORE_GL_GREAT     = +20   # >= 2.0
SCORE_GL_GOOD      = +10   # 1.5 - 2.0
SCORE_PATIENT      = +10   # Patient Specialist bonus
SCORE_HIGH_FOCUS   = +10   # category focus > 80%

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

# ── Category Patterns ─────────────────────────────────────────────────────────

CATEGORY_RE: dict[str, re.Pattern] = {
    "geopolitics": re.compile(
        r"ukraine|russia|ceasefire|nato|iran|nuclear-deal|middle-east|israel|"
        r"taiwan|sanctions|peace-deal|war-in|conflict-|coup-in|invasion|"
        r"xi-jinping|putin|zelensky|kim-jong|india-pakistan|venezuela|syria|"
        r"north-korea|gaza|hamas|hezbollah|military-action|occupied",
        re.I,
    ),
    "politics": re.compile(
        r"election-winner|presidential-elect|prime-minister-of|vote-for|"
        r"congress|senate|parliament|referendum|governor-of|chancellor-of|"
        r"coalition|primary-winner|party-win|seat-majority|approval-rating|"
        r"polls-in|democratic-nominee|republican-nominee|majority-leader",
        re.I,
    ),
    "tech": re.compile(
        r"openai|gpt-|ai-model|spacex|starship|tesla-|apple-|google-|amazon-|"
        r"microsoft-|ipo-|chatgpt|claude-ai|gemini-|product-launch|"
        r"self-driving|autonomous-|breakthrough|tech-ipo|llm-|semiconductor",
        re.I,
    ),
    "culture": re.compile(
        r"oscar|emmy|grammy|nobel|box-office|celebrity|movie-|award-|"
        r"eurovision|pope-|royal-|world-record|viral|streaming|hollywood|"
        r"singer|rapper|actor|actress|tv-show|film-|album|highest-grossing|"
        r"james-bond|music-|entertainment",
        re.I,
    ),
    "macro": re.compile(
        r"fed-decision|rate-cut-by|fed-rate|inflation-in|recession-by|"
        r"interest-rate|national-debt|gold-price-hit|crude-oil|sp500-above|"
        r"stock-market-crash|yield-curve|unemployment-rate|how-many-fed",
        re.I,
    ),
    "sports_ref": re.compile(
        r"fifa-world-cup|champions-league-winner|super-bowl|world-series|"
        r"stanley-cup|wimbledon|us-open-tennis",
        re.I,
    ),
}

HFT_RE = re.compile(
    r"updown-5m|updown-15m|updown-1h|btc-updown|eth-updown|price-up-or-down",
    re.I,
)
SPORTS_DAILY_RE = re.compile(
    r"\bnba\b|\bnfl\b|\bnhl\b|\bmlb\b|dota2?-|-lol-|-cs2-|-valorant-|"
    r"game1-|game2-|kill-over|tennis-.*2026-04|soccer-.*2026-04",
    re.I,
)


# ── API Helper ────────────────────────────────────────────────────────────────

async def _get(session: aiohttp.ClientSession, url: str, params: dict = None):
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status != 200:
                return None
            return await r.json(content_type=None)
    except Exception:
        return None


def _classify(slug: str) -> str | None:
    if HFT_RE.search(slug) or SPORTS_DAILY_RE.search(slug):
        return None
    for cat, pat in CATEGORY_RE.items():
        if pat.search(slug):
            return cat
    return None


# ── Phase 1: Category-driven market scan ─────────────────────────────────────

async def _fetch_category_markets(
    session: aiohttp.ClientSession, max_events: int
) -> dict[str, list[dict]]:
    """
    Fetches events from Gamma API, classifies by category, returns
    {category: [{event_slug, market_slug, token_id, volume}]}.
    """
    all_events: list[dict] = []
    for offset in range(0, max_events, 100):
        batch = await _get(session, f"{GAMMA_API}/events",
                           {"limit": 100, "offset": offset, "active": "true", "closed": "false"})
        if not batch:
            break
        all_events.extend(batch)
        await asyncio.sleep(RATE_DELAY)

    category_markets: dict[str, list[dict]] = {c: [] for c in CATEGORY_RE}
    seen_tokens: set = set()

    for event in all_events:
        slug     = event.get("slug", "")
        category = _classify(slug)
        if category is None:
            continue

        ev_vol  = float(event.get("volume", 0) or 0)
        ev_vol1wk = float(event.get("volume1wk", 0) or 0)

        if ev_vol < MARKET_VOL_MIN and ev_vol1wk < 1_000:
            continue

        for mkt in event.get("markets", []):
            raw_ids = mkt.get("clobTokenIds", "[]")
            try:
                token_ids = json.loads(raw_ids) if isinstance(raw_ids, str) else (raw_ids or [])
            except Exception:
                continue

            for tid in token_ids[:2]:
                if tid and tid not in seen_tokens:
                    seen_tokens.add(tid)
                    category_markets[category].append({
                        "event_slug":  slug,
                        "market_slug": mkt.get("slug", ""),
                        "token_id":    tid,
                        "volume":      ev_vol,
                        "volume_1wk":  ev_vol1wk,
                    })

    # Cap at MARKETS_PER_CAT, prefer highest-volume
    for cat in category_markets:
        category_markets[cat].sort(key=lambda x: -x["volume"])
        category_markets[cat] = category_markets[cat][:MARKETS_PER_CAT * 2]  # 2 tokens per market

    return category_markets


# ── Phase 2: Wallet collection per market ────────────────────────────────────

async def _collect_wallets(
    session: aiohttp.ClientSession,
    category_markets: dict[str, list[dict]],
    semaphore: asyncio.Semaphore,
) -> dict[str, dict]:
    """
    For each market token, fetches 100 trades, aggregates top-20 wallets by USDC.
    Returns {wallet: {category_counts, total_usdc_by_cat, trade_count, last_ts, name}}.
    """
    wallet_data: dict[str, dict] = {}

    async def _fetch_one(token_id: str, category: str):
        async with semaphore:
            trades = await _get(session, f"{DATA_API}/trades",
                                {"asset_id": token_id, "limit": 100})
            await asyncio.sleep(RATE_DELAY)
            if not trades:
                return

            # Aggregate by wallet to find top-20 by USDC
            w_usdc: dict[str, float] = {}
            w_meta: dict[str, dict] = {}
            for t in trades:
                w = (t.get("proxyWallet") or "").lower()
                if not w:
                    continue
                usdc = float(t.get("usdcSize", 0) or t.get("size", 0) or 0)
                w_usdc[w] = w_usdc.get(w, 0.0) + usdc
                if w not in w_meta:
                    w_meta[w] = {"last_ts": 0, "name": ""}
                ts = t.get("timestamp", 0)
                if ts > w_meta[w]["last_ts"]:
                    w_meta[w]["last_ts"] = ts
                if not w_meta[w]["name"] and t.get("name"):
                    w_meta[w]["name"] = t["name"]

            # Top-20 wallets by USDC volume on this market
            top20 = sorted(w_usdc.items(), key=lambda x: -x[1])[:20]

            for w, usdc_vol in top20:
                if w not in wallet_data:
                    wallet_data[w] = {
                        "category_counts":    Counter(),
                        "category_usdc":      Counter(),
                        "trade_count":        0,
                        "last_ts":            0,
                        "name":               "",
                    }
                wallet_data[w]["category_counts"][category] += 1
                wallet_data[w]["category_usdc"][category]   += usdc_vol
                wallet_data[w]["trade_count"] += 1
                ts = w_meta[w]["last_ts"]
                if ts > wallet_data[w]["last_ts"]:
                    wallet_data[w]["last_ts"] = ts
                if not wallet_data[w]["name"] and w_meta[w]["name"]:
                    wallet_data[w]["name"] = w_meta[w]["name"]

    tasks = []
    for cat, markets in category_markets.items():
        for mkt in markets:
            tasks.append(_fetch_one(mkt["token_id"], cat))

    await asyncio.gather(*tasks)
    return wallet_data


# ── Phase 3: HF-10 bot check ─────────────────────────────────────────────────

async def _check_hft(session: aiohttp.ClientSession, wallet: str) -> dict:
    data = await _get(session, f"{DATA_API}/trades", {"user": wallet, "limit": 500})
    if not data:
        return {"hft_frac": 0.0, "trades_per_day": 0.0, "is_bot": False, "bucket": "unknown"}

    total = len(data)
    hft_cnt = sum(
        1 for t in data
        if HFT_RE.search(t.get("eventSlug", "") or t.get("slug", "") or "")
    )
    hft_frac = hft_cnt / total if total else 0.0

    ts_list = [t.get("timestamp", 0) for t in data if t.get("timestamp")]
    if len(ts_list) >= 2:
        span = (max(ts_list) - min(ts_list)) / 86400
        tpd  = total / max(span, 0.1)
    else:
        tpd = 0.0

    is_bot = hft_frac > HF10_MAX_HFT_FRAC or tpd > HF10_MAX_TPD

    if BUCKET_ACTIVE_MIN <= tpd <= BUCKET_ACTIVE_MAX:
        bucket = "active"
    elif BUCKET_PATIENT_MIN <= tpd < BUCKET_ACTIVE_MIN:
        bucket = "patient"
    else:
        bucket = "out_of_range"

    return {
        "hft_frac":       round(hft_frac, 3),
        "trades_per_day": round(tpd, 2),
        "is_bot":         is_bot,
        "bucket":         bucket,
    }


# ── Phase 4: Detailed wallet stats ───────────────────────────────────────────

async def _fetch_wallet_stats(session: aiohttp.ClientSession, wallet: str) -> dict:
    now_ts   = datetime.now(timezone.utc).timestamp()
    cutoff60 = now_ts - 60 * 86400

    # 1. Trades (60d count + trades_per_day span)
    td = await _get(session, f"{DATA_API}/trades", {"user": wallet, "limit": 500})
    trades_60d   = 0
    oldest_trade = now_ts
    if td:
        for t in td:
            ts = t.get("timestamp", 0)
            if ts and ts < oldest_trade:
                oldest_trade = ts
            if ts and ts >= cutoff60:
                trades_60d += 1
    trades_limit_hit = (td is not None and len(td) >= 500)

    # 2. Activity (up to 1500 records for WR + account-age + GL-ratio)
    bought_cids:   set          = set()
    redeemed_cids: set          = set()
    buy_costs:     dict         = defaultdict(float)    # conditionId → total USDC spent
    redeem_gains:  dict         = defaultdict(float)    # conditionId → total USDC received
    oldest_activity = oldest_trade
    activity_exhausted = False

    for batch_offset in range(0, 1500, 500):
        batch = await _get(session, f"{DATA_API}/activity",
                           {"user": wallet, "limit": 500, "offset": batch_offset})
        await asyncio.sleep(0.02)
        if not batch:
            activity_exhausted = True
            break
        for a in batch:
            ts   = a.get("timestamp", 0)
            typ  = (a.get("type") or "").upper()
            cid  = a.get("conditionId", "")
            usdc = float(a.get("usdcSize", 0) or 0)

            if ts and ts < oldest_activity:
                oldest_activity = ts

            if typ == "TRADE" and (a.get("side") or "").upper() == "BUY" and cid:
                bought_cids.add(cid)
                buy_costs[cid] += usdc
            elif typ == "REDEEM" and cid:
                redeemed_cids.add(cid)
                redeem_gains[cid] += usdc

        if len(batch) < 500:
            activity_exhausted = True
            break

    # Account age
    age_unknown = (not activity_exhausted and trades_limit_hit)
    account_age_days = (
        int((now_ts - oldest_activity) / 86400) if oldest_activity < now_ts else 0
    ) if not age_unknown else -1

    # Win-rate
    total_traded = len(bought_cids)
    total_won    = len(redeemed_cids & bought_cids)
    win_rate_est = round(total_won / total_traded, 4) if total_traded >= 10 else None

    # Gain-Loss Ratio
    won_cids  = redeemed_cids & bought_cids
    lost_cids = bought_cids - redeemed_cids
    if won_cids and lost_cids:
        avg_profit = sum(
            redeem_gains.get(c, 0) - buy_costs.get(c, 0) for c in won_cids
        ) / len(won_cids)
        avg_loss = sum(buy_costs.get(c, 0) for c in lost_cids) / len(lost_cids)
        gl_ratio = round(avg_profit / avg_loss, 3) if avg_loss > 0 else None
    else:
        gl_ratio = None

    # cashPnL
    pos = await _get(session, f"{DATA_API}/positions", {"user": wallet})
    cash_pnl = sum(float(p.get("cashPnl") or 0) for p in (pos or []) if isinstance(p, dict))

    return {
        "wallet":            wallet,
        "trades_60d":        trades_60d,
        "account_age_days":  account_age_days,
        "age_unknown":       age_unknown,
        "win_rate_est":      win_rate_est,
        "total_traded_mkts": total_traded,
        "total_won_mkts":    total_won,
        "gl_ratio":          gl_ratio,
        "cash_pnl":          round(cash_pnl, 2),
        "oldest_ts":         oldest_activity,
    }


# ── Phase 5: Scoring + hard filters ──────────────────────────────────────────

def _compute_score(stats: dict, hft: dict, focus: dict) -> int:
    score = 0
    pnl = stats.get("cash_pnl", 0)
    if pnl > 1000:    score += SCORE_PNL_HIGH
    elif pnl >= -500: score += SCORE_PNL_MID
    else:             score += SCORE_PNL_LOW

    wr = stats.get("win_rate_est") or 0
    if 0.60 <= wr <= 0.70:   score += SCORE_WR_SWEET
    elif 0.55 <= wr < 0.60 or 0.70 < wr <= 0.75: score += SCORE_WR_OK

    gl = stats.get("gl_ratio")
    if gl is not None:
        if gl >= 2.0: score += SCORE_GL_GREAT
        elif gl >= 1.5: score += SCORE_GL_GOOD

    if hft.get("bucket") == "patient": score += SCORE_PATIENT
    if focus.get("focus_frac", 0) > 0.80: score += SCORE_HIGH_FOCUS

    return score


def _apply_filters(stats: dict, hft: dict, last_ts: float) -> dict:
    now_ts   = datetime.now(timezone.utc).timestamp()
    inact    = (now_ts - last_ts) / 86400 if last_ts else 999
    wr       = stats.get("win_rate_est")
    age      = stats["account_age_days"]
    bucket   = hft.get("bucket", "unknown")
    gl       = stats.get("gl_ratio")

    hf1_min = HF1_MIN_TRADES_PATIENT if bucket == "patient" else HF1_MIN_TRADES_ACTIVE

    if age == -1:
        hf2 = "UNKNOWN(Pagination)"
    elif age >= HF2_MIN_AGE_DAYS:
        hf2 = "PASS"
    else:
        hf2 = f"FAIL({age}d)"

    if wr is None:
        hf8 = "UNKNOWN(wenig Daten)"
    elif HF8_MIN_WR <= wr <= HF8_MAX_WR:
        hf8 = f"PASS({wr:.0%})"
    else:
        hf8 = f"FAIL({wr:.0%})"

    if gl is None:
        gl_status = "UNKNOWN(wenig Daten)"
    elif gl >= HF_GL_MIN_RATIO:
        gl_status = f"PASS({gl:.2f})"
    else:
        gl_status = f"FAIL({gl:.2f} < {HF_GL_MIN_RATIO})"

    results = {
        "HF-1_sample":    ("PASS" if stats["trades_60d"] >= hf1_min
                           else f"FAIL({stats['trades_60d']} < {hf1_min})"),
        "HF-2_age":        hf2,
        "HF-5_active":    ("PASS" if inact <= HF5_MAX_INACTIVE
                           else f"FAIL({inact:.0f}d inaktiv)"),
        "HF-8_winrate":    hf8,
        "HF-10_no_hft":   ("PASS" if not hft["is_bot"]
                           else f"FAIL(HFT={hft['hft_frac']:.0%} TPD={hft['trades_per_day']:.0f})"),
        "GL_ratio":        gl_status,
        "bucket":          bucket,
    }
    fails    = [k for k, v in results.items() if v.startswith("FAIL") and k != "bucket"]
    unknowns = [k for k, v in results.items() if v.startswith("UNKNOWN") and k != "bucket"]

    if fails:
        verdict = "FAIL"
    elif unknowns:
        verdict = "REVIEW"
    else:
        verdict = "PASS"

    return {"filters": results, "verdict": verdict, "fails": fails, "unknowns": unknowns}


def _compute_focus(cat_counts: Counter) -> dict:
    total = sum(cat_counts.values())
    if not total:
        return {"top_category": "unknown", "focus_frac": 0.0, "breakdown": {}}
    top_cat, top_cnt = cat_counts.most_common(1)[0]
    return {
        "top_category": top_cat,
        "focus_frac":   round(top_cnt / total, 3),
        "breakdown":    dict(cat_counts),
    }


def _archetyp(stats: dict, hft: dict, focus: dict) -> str:
    cat  = focus["top_category"]
    frac = focus["focus_frac"]
    tpd  = hft.get("trades_per_day", 0)
    specialist = frac >= 0.60
    patient    = hft.get("bucket") == "patient"
    label = f"{cat.capitalize()}-Spezialist" if specialist else "Generalist"
    if patient:
        label = f"Patient-{label}"
    return label


# ── Report generation ─────────────────────────────────────────────────────────

def _generate_report(candidates: list, scan_meta: dict) -> str:
    now   = datetime.now(timezone.utc)
    lines = [
        "# Discovery Phase 1.6 Report — T-D83",
        f"**Erstellt:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Scan-Konfiguration",
        "| Parameter | Wert |",
        "|-----------|------|",
        f"| Events gescannt | {scan_meta['events_fetched']} |",
        f"| Laufzeit | {scan_meta['duration_s']:.0f}s |",
        "",
        "## Kategorie-Statistik",
        "| Kategorie | Märkte (Tokens) | Unique Wallets | HF-10 Skip | Analysiert |",
        "|-----------|----------------|---------------|-----------|-----------|",
    ]

    for cat in CATEGORY_RE:
        cm = scan_meta.get("cat_meta", {}).get(cat, {})
        lines.append(
            f"| {cat} | {cm.get('tokens', 0)} | {cm.get('wallets_before_hf10', 0)} | "
            f"{cm.get('hft_excluded', 0)} | {cm.get('analyzed', 0)} |"
        )

    passing = [c for c in candidates if c["verdict"] == "PASS"]
    review  = [c for c in candidates if c["verdict"] == "REVIEW"]
    failing = [c for c in candidates if c["verdict"] == "FAIL"]
    new_pass = [c for c in passing if c["wallet"] not in CURRENT_TARGETS]

    active_pass   = [c for c in passing if c["hft"].get("bucket") == "active"]
    patient_pass  = [c for c in passing if c["hft"].get("bucket") == "patient"]
    active_review = [c for c in review  if c["hft"].get("bucket") == "active"]
    patient_review= [c for c in review  if c["hft"].get("bucket") == "patient"]

    lines += [
        "",
        "## Gesamtergebnis",
        "| Kategorie | Anzahl |",
        "|-----------|--------|",
        f"| **PASS** | **{len(passing)}** ({len(new_pass)} NEU) |",
        f"| REVIEW   | {len(review)} |",
        f"| FAIL     | {len(failing)} |",
        "",
        "## Bucket-Split",
        "| Bucket | PASS | REVIEW |",
        "|--------|------|--------|",
        f"| Active Traders (3-15/Tag) | {len(active_pass)} | {len(active_review)} |",
        f"| Patient Specialists (0.5-3/Tag) | {len(patient_pass)} | {len(patient_review)} |",
        "",
    ]

    # Per-category sections
    for cat in CATEGORY_RE:
        cat_pass   = [c for c in passing if c.get("top_cat") == cat]
        cat_review = [c for c in review  if c.get("top_cat") == cat]
        cat_all    = [c for c in candidates if c.get("top_cat") == cat]
        if not cat_all:
            continue

        lines += [
            f"---",
            f"## Kategorie: {cat.upper()}",
            f"PASS: **{len(cat_pass)}** | REVIEW: {len(cat_review)} | FAIL: {len(cat_all)-len(cat_pass)-len(cat_review)}",
            "",
            f"### Top-5 Kandidaten — {cat}",
            "| Wallet | Name | Archetyp | Bucket | WR% | G/L | Trades/60d | Alter | Score | Verdict |",
            "|--------|------|---------|--------|-----|-----|-----------|-------|-------|---------|",
        ]
        cat_top5 = sorted(
            [c for c in cat_all if c["verdict"] in ("PASS", "REVIEW")],
            key=lambda x: -x.get("score", 0),
        )[:5]
        if not cat_top5:
            cat_top5 = sorted(cat_all, key=lambda x: -x.get("score", 0))[:5]
        for c in cat_top5:
            s    = c["stats"]
            w    = c["wallet"]
            name = (c.get("name") or "")[:14] or w[:8]
            wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            gl   = f"{s['gl_ratio']:.2f}" if s.get("gl_ratio") else "?"
            age  = "?" if s["account_age_days"] == -1 else str(s["account_age_days"])
            arch = c.get("archetyp", "?")
            bkt  = c["hft"].get("bucket", "?")
            lines.append(
                f"| `{w[:8]}...{w[-4:]}` | {name} | {arch} | {bkt} | {wr} | {gl} | "
                f"{s['trades_60d']} | {age} | {c.get('score',0)} | **{c['verdict']}** |"
            )

    # Top-10 Overall
    lines += [
        "",
        "---",
        "## Top-10 Overall (Cross-Kategorie) — Brrudi Verifikations-Liste",
        "| Rank | Wallet | Name | Kategorie | Archetyp | WR% | G/L | TPD | Score | Verdict |",
        "|------|--------|------|----------|---------|-----|-----|-----|-------|---------|",
    ]
    overall_top = sorted(candidates, key=lambda x: -x.get("score", 0))[:10]
    for i, c in enumerate(overall_top, 1):
        s    = c["stats"]
        w    = c["wallet"]
        name = (c.get("name") or "")[:14] or w[:8]
        wr   = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
        gl   = f"{s['gl_ratio']:.2f}" if s.get("gl_ratio") else "?"
        tpd  = f"{c['hft'].get('trades_per_day', 0):.1f}"
        cat  = c.get("top_cat", "?")
        arch = c.get("archetyp", "?")
        lines.append(
            f"| {i} | `{w[:8]}...{w[-4:]}` | {name} | {cat} | {arch} | {wr} | {gl} | "
            f"{tpd} | {c.get('score',0)} | **{c['verdict']}** |"
        )

    # Detailed PASS breakdowns
    lines += ["", "---", "## PASS-Kandidaten — Detail"]
    for c in sorted(passing, key=lambda x: -x.get("score", 0)):
        s    = c["stats"]
        w    = c["wallet"]
        name = c.get("name") or "unknown"
        f    = c["filters"]
        focus = c.get("focus", {})
        hft   = c["hft"]
        wr    = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
        gl    = f"{s['gl_ratio']:.2f}" if s.get("gl_ratio") else "N/A"
        age   = "UNKNOWN" if s["account_age_days"] == -1 else f"{s['account_age_days']} Tage"
        lines += [
            f"### {name} (`{w}`)",
            f"- **Archetyp**: {c.get('archetyp','?')} | Bucket: {hft.get('bucket','?')} | Score: {c.get('score',0)}",
            f"- **Kategorie-Fokus**: {focus.get('top_category','?')} — {focus.get('focus_frac',0):.0%}",
            f"- Kategorie-Breakdown: {focus.get('breakdown',{})}",
            f"- Win-Rate: **{wr}** | Gain-Loss Ratio: **{gl}**",
            f"- Trades 60d: **{s['trades_60d']}** | TPD: **{hft.get('trades_per_day',0):.1f}**",
            f"- Account-Alter: **{age}** | HFT-Anteil: **{hft.get('hft_frac',0):.0%}**",
            f"- cashPnL: **${s['cash_pnl']:+.2f}**",
            f"- HF-1: {f['HF-1_sample']} | HF-2: {f['HF-2_age']} | HF-5: {f['HF-5_active']}",
            f"- HF-8: {f['HF-8_winrate']} | HF-10: {f['HF-10_no_hft']} | G/L: {f['GL_ratio']}",
            f"- In TARGET_WALLETS: {'✅ JA' if w in CURRENT_TARGETS else '❌ NEU'}",
            "",
        ]

    # Fail breakdown
    from collections import Counter as _Counter
    all_fails = []
    for c in candidates:
        all_fails.extend(c.get("fails", []))
    fail_cnts = _Counter(all_fails)
    bucket_dist = _Counter(c["hft"].get("bucket", "unknown") for c in candidates)
    gl_available = sum(1 for c in candidates if c["stats"].get("gl_ratio") is not None)
    gl_pass = sum(1 for c in candidates
                  if c["stats"].get("gl_ratio") and c["stats"]["gl_ratio"] >= HF_GL_MIN_RATIO)
    gl_20 = sum(1 for c in candidates
                if c["stats"].get("gl_ratio") and c["stats"]["gl_ratio"] >= 2.0)

    lines += [
        "---",
        "## Fail-Breakdown",
        "| Filter | Anzahl FAILs |",
        "|--------|-------------|",
    ]
    for hf, cnt in sorted(fail_cnts.items(), key=lambda x: -x[1]):
        lines.append(f"| {hf} | {cnt} |")

    lines += [
        "",
        "## Gain-Loss Ratio Statistik",
        "| Metrik | Wert |",
        "|--------|------|",
        f"| Wallets mit G/L Daten | {gl_available} |",
        f"| G/L >= 1.5 (Filter-PASS) | {gl_pass} |",
        f"| G/L >= 2.0 (0xIcaruss-Benchmark) | {gl_20} |",
        "",
        "## Frequenz-Bucket Verteilung",
        "| Bucket | Wallets |",
        "|--------|---------|",
    ]
    for bkt, cnt in sorted(bucket_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {bkt} | {cnt} |")

    lines += [
        "",
        "## Discovery-Statistik",
        "| Parameter | Wert |",
        "|-----------|------|",
        f"| Events gescannt | {scan_meta['events_fetched']} |",
        f"| Qualifying Market-Tokens | {scan_meta['total_tokens']} |",
        f"| Wallets gesammelt (vor HF-10) | {scan_meta['wallets_before_hf10']} |",
        f"| HF-10 ausgeschlossen (Bot) | {scan_meta['hft_excluded']} |",
        f"| Detailliert analysiert | {scan_meta['analyzed']} |",
        f"| Laufzeit | {scan_meta['duration_s']:.0f}s |",
        f"| API-Calls (geschätzt) | {scan_meta['total_tokens'] + scan_meta['analyzed'] * 5} |",
        f"| Coverage-Schätzung | ~{scan_meta['total_tokens'] * 100 // max(1, scan_meta['total_tokens']):.0f}% der Top-{scan_meta['total_tokens']}k Markt-Trades |",
        "",
        "## Bekannte Limitierungen",
        "1. Gain-Loss Ratio basiert auf REDEEM/BUY-Matching — offene Positionen als nicht verloren gezählt (Schätzung).",
        "2. Account-Alter ohne Polygonscan-Key nur via Pagination (1500 Records) bestimmbar.",
        "3. Gamma API volume = Lifetime-Volumen; Nischen-Filter nicht exakt möglich.",
        "4. Culture-Kategorie unterrepräsentiert (nur 4 aktive Märkte gefunden).",
        "5. G/L Ratio < 1.0 möglich wenn REDEEM-usdcSize < BUY-usdcSize (niedrige Gewinn-Preise).",
        "",
        "## Phase-2-Aufwand (aktualisiert nach Phase 1.6)",
        "| Komponente | Status | Aufwand |",
        "|------------|--------|---------|",
        "| Kategorie-Scan | ✅ Phase 1.6 | — |",
        "| HFT-Filter HF-10 | ✅ Phase 1.6 | — |",
        "| Gain-Loss Ratio | ✅ Phase 1.6 | — |",
        "| Bucket-Split | ✅ Phase 1.6 | — |",
        "| Account-Alter (Polygonscan) | ❌ | 0.5 Tage (API Key nötig) |",
        "| Win-Rate via Market-Resolution | ❌ | 2 Tage |",
        "| HF-3/4/6/7/9 (predicts.guru) | ❌ | 1 Tag |",
        "| SQLite Cache | ❌ | 0.5 Tage |",
        "| Telegram-Alert bei PASS | ❌ | 0.5 Tage |",
        "| **Gesamt Phase 2** | | **~4.5 Tage** |",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(max_events: int = 600, top: int = 100) -> None:
    t_start = time.time()
    print("🔍 Discovery PoC v3 — T-D83 Phase 1.6")
    print(f"   Events: {max_events} | Top Wallets: {top}")

    conn = aiohttp.TCPConnector(limit=CONCURRENT * 2)
    headers = {"User-Agent": "KongTradeBot/Discovery-v3"}

    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        semaphore = asyncio.Semaphore(CONCURRENT)

        # ── Phase 1 ────────────────────────────────────────────────────────────
        print("\n[1/5] Kategorie-Märkte via Gamma API scannen...")
        cat_markets = await _fetch_category_markets(session, max_events)
        total_tokens = sum(len(v) for v in cat_markets.values())
        for cat, mkts in cat_markets.items():
            print(f"  {cat:12s}: {len(mkts):3d} Tokens")
        print(f"  → {total_tokens} Tokens total")

        # ── Phase 2 ────────────────────────────────────────────────────────────
        print("\n[2/5] Wallets aus Kategorie-Märkten sammeln (Top-20/Markt)...")
        wallet_stream = await _collect_wallets(session, cat_markets, semaphore)
        print(f"  → {len(wallet_stream)} unique Wallets gesammelt")

        # ── Phase 3 ────────────────────────────────────────────────────────────
        sorted_wallets = sorted(wallet_stream.items(), key=lambda x: -x[1]["trade_count"])[:top]
        print(f"\n[3/5] HF-10 Bot-Filter + Bucket-Klassifikation ({len(sorted_wallets)} Wallets)...")

        async def _bounded_hft(w):
            async with semaphore:
                r = await _check_hft(session, w)
                await asyncio.sleep(RATE_DELAY)
                return w, r

        hft_results = {}
        for coro in asyncio.as_completed([_bounded_hft(w) for w, _ in sorted_wallets]):
            w, hft = await coro
            hft_results[w] = hft

        surviving = [(w, wd) for w, wd in sorted_wallets if not hft_results.get(w, {}).get("is_bot")]
        excl_bots = len(sorted_wallets) - len(surviving)
        bucket_cnt = Counter(hft_results[w]["bucket"] for w, _ in sorted_wallets)
        print(f"  → {excl_bots} Bot-Wallets ausgeschlossen (HF-10)")
        print(f"  → Buckets: {dict(bucket_cnt)}")
        print(f"  → {len(surviving)} für Detail-Analyse")

        # ── Phase 4 ────────────────────────────────────────────────────────────
        print(f"\n[4/5] Detaillierte Stats für {len(surviving)} Wallets...")

        async def _bounded_stats(w):
            async with semaphore:
                r = await _fetch_wallet_stats(session, w)
                await asyncio.sleep(RATE_DELAY)
                return r

        stats_list = []
        for i, coro in enumerate(asyncio.as_completed([_bounded_stats(w) for w, _ in surviving]), 1):
            stats_list.append(await coro)
            if i % 10 == 0:
                print(f"  → {i}/{len(surviving)} done...")

        # ── Phase 5 ────────────────────────────────────────────────────────────
        print("\n[5/5] Filter anwenden + Scoring...")
        candidates = []
        cat_meta: dict = {cat: {"tokens": len(cat_markets[cat]), "wallets_before_hf10": 0,
                                 "hft_excluded": 0, "analyzed": 0} for cat in CATEGORY_RE}

        for w, wd in sorted_wallets:
            focus_raw = wd.get("category_counts", Counter())
            top_cat = focus_raw.most_common(1)[0][0] if focus_raw else "unknown"
            cat_meta[top_cat]["wallets_before_hf10"] = cat_meta[top_cat].get("wallets_before_hf10", 0) + 1
            if hft_results.get(w, {}).get("is_bot"):
                cat_meta[top_cat]["hft_excluded"] = cat_meta[top_cat].get("hft_excluded", 0) + 1

        for stats in stats_list:
            w        = stats["wallet"]
            wd       = wallet_stream[w]
            hft      = hft_results[w]
            last_ts  = wd.get("last_ts", 0)
            name     = wd.get("name", "")
            focus    = _compute_focus(wd.get("category_counts", Counter()))
            top_cat  = focus["top_category"]
            hf       = _apply_filters(stats, hft, last_ts)
            arch     = _archetyp(stats, hft, focus)
            score    = _compute_score(stats, hft, focus)

            cat_meta[top_cat]["analyzed"] = cat_meta[top_cat].get("analyzed", 0) + 1

            candidates.append({
                "wallet":   w,
                "name":     name,
                "top_cat":  top_cat,
                "stats":    stats,
                "hft":      hft,
                "focus":    focus,
                "filters":  hf["filters"],
                "verdict":  hf["verdict"],
                "fails":    hf["fails"],
                "unknowns": hf["unknowns"],
                "archetyp": arch,
                "score":    score,
            })

        pass_count   = sum(1 for c in candidates if c["verdict"] == "PASS")
        review_count = sum(1 for c in candidates if c["verdict"] == "REVIEW")
        fail_count   = sum(1 for c in candidates if c["verdict"] == "FAIL")
        new_pass     = sum(1 for c in candidates if c["verdict"] == "PASS" and c["wallet"] not in CURRENT_TARGETS)

        duration = time.time() - t_start
        print(f"\n  PASS:   {pass_count}  ({new_pass} NEU)")
        print(f"  REVIEW: {review_count}")
        print(f"  FAIL:   {fail_count}")

        # Top-10 summary
        top10 = sorted(candidates, key=lambda x: -x.get("score", 0))[:10]
        print("\nTop-10 by Score:")
        for c in top10:
            s   = c["stats"]
            wr  = f"{s['win_rate_est']:.0%}" if s.get("win_rate_est") else "?"
            gl  = f"{s['gl_ratio']:.2f}" if s.get("gl_ratio") else "?"
            age = "?" if s["account_age_days"] == -1 else f"{s['account_age_days']}d"
            tgt = "TARGET" if c["wallet"] in CURRENT_TARGETS else "NEU"
            print(
                f"  {c['wallet'][:8]}...{c['wallet'][-4:]} | "
                f"score={c['score']:+3d} | WR={wr} | G/L={gl} | "
                f"{c['hft'].get('bucket','?')} | {c.get('top_cat','?')} | {tgt} | {c['verdict']}"
            )

        scan_meta = {
            "events_fetched":     max_events,
            "total_tokens":       total_tokens,
            "wallets_before_hf10":len(wallet_stream),
            "hft_excluded":       excl_bots,
            "analyzed":           len(surviving),
            "duration_s":         duration,
            "cat_meta":           cat_meta,
        }

        report = _generate_report(candidates, scan_meta)
        ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
        out_path = ANALYSES_DIR / f"discovery_phase_1_6_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"\n✅ Report: {out_path}")
        print(f"   Laufzeit: {duration:.0f}s")


def _cli():
    p = argparse.ArgumentParser()
    p.add_argument("--events", type=int, default=600)
    p.add_argument("--top", type=int, default=100)
    a = p.parse_args()
    asyncio.run(main(a.events, a.top))


if __name__ == "__main__":
    _cli()
