"""
Polymarket Insider Pattern Analyzer — 12 Monate
=================================================
Analysiert alle Polymarket-Trades der letzten 365 Tage.
Unterscheidet echte Insider von Pump & Dump.
Keine Trading-Logik — nur Datenanalyse.

Datenquellen (alle kostenlos, kein Key nötig):
- Polymarket Data API
- Polymarket Gamma API
- Polygonscan API
"""

import asyncio
import aiohttp
import json
import csv
import time
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ── Konfiguration ──────────────────────────────────
OUTPUT_DIR = Path("/root/KongTradeBot/data/insider_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

POLYMARKET_API   = "https://data-api.polymarket.com"
GAMMA_API        = "https://gamma-api.polymarket.com"
POLYGONSCAN_API  = "https://api.polygonscan.com/api"
POLYGONSCAN_KEY  = os.getenv("POLYGONSCAN_KEY", "IAYXP5NMRQCUHWF3T3346U277JD1YDUJD6")

# ── Insider-Erkennungs-Parameter ───────────────────
MAX_WALLET_AGE_DAYS   = 999
MIN_TRADE_USD         = 500
MAX_LIFETIME_TRADES   = 10
MAX_ENTRY_PRICE       = 0.20
ANALYSIS_DAYS         = 365

# Geopolitik-Keywords
GEO_KEYWORDS = [
    "iran","israel","trump","ceasefire","war",
    "military","sanctions","nuclear","ukraine",
    "russia","china","taiwan","election","president",
    "minister","congress","senate","fed","rate",
    "assassination","coup","attack","strike",
    "kim","putin","xi","netanyahu","erdogan"
]

# ── Polygon Blockchain: Wallet-Alter ───────────────
async def get_wallet_age_days(
        wallet: str,
        session: aiohttp.ClientSession) -> float:
    try:
        async with session.get(
            POLYGONSCAN_API,
            params={
                "module": "account",
                "action": "txlist",
                "address": wallet,
                "page": 1, "offset": 1,
                "sort": "asc",
                "apikey": POLYGONSCAN_KEY
            },
            timeout=aiohttp.ClientTimeout(total=8)
        ) as r:
            data = await r.json()
        txs = data.get("result", [])
        if not txs or not isinstance(txs, list):
            return 999.0
        first_ts = int(txs[0].get("timeStamp", 0))
        return round((time.time() - first_ts) / 86400, 1)
    except:
        return 999.0


# ── Polymarket: Wallet-Trade-Historie ─────────────
async def get_wallet_trades(
        wallet: str,
        session: aiohttp.ClientSession) -> list:
    try:
        async with session.get(
            f"{POLYMARKET_API}/trades",
            params={"user": wallet, "limit": 50},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            data = await r.json()
        return data if isinstance(data, list) else []
    except:
        return []


# ── Polymarket: Aufgelöste Märkte (Streaming-Filter) ──
async def get_resolved_markets(
        session: aiohttp.ClientSession) -> list:
    """Lädt Märkte seitenweise und filtert sofort — kein Gesamt-RAM-Aufbau."""
    geo_markets = []
    niche_markets = []
    offset = 0
    total_seen = 0
    since = datetime.now(timezone.utc) - \
            timedelta(days=ANALYSIS_DAYS)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(
        f"Lade+filtere Märkte streaming "
        f"(letzte {ANALYSIS_DAYS} Tage, seit {since_str})...")

    while True:
        try:
            async with session.get(
                f"{GAMMA_API}/markets",
                params={
                    "closed": "true",
                    "limit": 100,
                    "offset": offset,
                    "end_date_min": since_str
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                batch = await r.json()

            if not batch:
                break
            if isinstance(batch, dict):
                batch = batch.get("markets", [])
            if not batch:
                break

            # Streaming-Filter: sofort klassifizieren, nicht alles speichern
            for m in batch:
                vol = float(m.get("volume", "0") or 0)
                if vol < 500:
                    continue
                total_seen += 1
                q = (m.get("question","") + " " +
                     m.get("description","")).lower()
                is_geo = any(k in q for k in GEO_KEYWORDS)
                if is_geo and len(geo_markets) < 3000:
                    geo_markets.append(m)
                elif not is_geo and vol < 100000 \
                        and len(niche_markets) < 500:
                    niche_markets.append(m)

            offset += 100
            if offset % 1000 == 0:
                logger.info(
                    f"  {offset} Seiten, {total_seen} vol-ok, "
                    f"geo={len(geo_markets)} niche={len(niche_markets)}")
            await asyncio.sleep(0.3)
            if len(geo_markets) >= 3000 and len(niche_markets) >= 500:
                logger.info("  ✅ Beide Buckets voll — Laden abgeschlossen")
                break

        except Exception as e:
            logger.error(f"Markt-Fehler: {e}")
            break

    # Nach Volumen sortieren, beste Geo-Märkte zuerst
    geo_markets = sorted(
        geo_markets,
        key=lambda m: float(m.get("volume","0") or 0),
        reverse=True
    )
    result = geo_markets + niche_markets
    logger.info(
        f"  Fertig: {len(result)} Märkte gefiltert "
        f"(geo={len(geo_markets)}, niche={len(niche_markets)})")
    return result


# ── Verdächtige Trades in einem Markt ─────────────
async def get_suspicious_trades(
        market: dict,
        session: aiohttp.ClientSession) -> list:

    condition_id = market.get("conditionId","")
    question = market.get("question","")[:60]
    end_date = market.get("endDate","")

    if not condition_id or not end_date:
        return []

    try:
        resolution_ts = datetime.fromisoformat(
            end_date.replace("Z","+00:00")
        ).timestamp()
    except:
        return []

    window_start = resolution_ts - (48 * 3600)

    try:
        async with session.get(
            f"{POLYMARKET_API}/trades",
            params={
                "market": condition_id,
                "limit": 500
            },
            timeout=aiohttp.ClientTimeout(total=15)
        ) as r:
            trades = await r.json()

        if not isinstance(trades, list):
            return []

    except:
        return []

    suspicious = []
    for t in trades:
        if t.get("side","").upper() in \
                ["SELL","SHORT"]:
            continue

        ts = float(t.get("timestamp", 0))
        if not ts:
            continue

        if not (window_start <= ts <= resolution_ts):
            continue

        price = float(t.get("price", 1))
        size = float(t.get("size", 0))
        wallet = t.get("proxyWallet", "")

        if (price <= MAX_ENTRY_PRICE and
                size >= MIN_TRADE_USD and
                wallet):
            suspicious.append({
                "wallet": wallet,
                "question": question,
                "condition_id": condition_id,
                "price": round(price, 4),
                "size_usd": round(size, 2),
                "trade_ts": ts,
                "trade_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "resolution_ts": resolution_ts,
                "hours_before": round(
                    (resolution_ts - ts) / 3600, 1)
            })

    return suspicious


# ── Pump & Dump vs. Insider ────────────────────────
async def classify_behavior(
        trade: dict,
        wallet_trades: list,
        resolution_ts: float) -> str:
    for t in wallet_trades:
        if t.get("side","").upper() not in \
                ["SELL","SHORT"]:
            continue
        if t.get("market","") != \
                trade["condition_id"]:
            continue
        ts_str = t.get(
            "timestamp", t.get("createdAt",""))
        try:
            sell_ts = datetime.fromisoformat(
                ts_str.replace("Z","+00:00")
            ).timestamp()
            if sell_ts < resolution_ts:
                return "SOLD_BEFORE_RESOLUTION"
        except:
            continue
    return "HELD_TO_RESOLUTION"


# ── Insider Score ──────────────────────────────────
def calculate_score(
        wallet_age: float,
        lifetime_trades: int,
        price: float,
        size_usd: float,
        hours_before: float,
        question: str = "") -> int:

    score = 0

    # Timing — Haupt-Signal (max 35)
    if hours_before < 0.5:    score += 35
    elif hours_before < 2:    score += 25
    elif hours_before < 6:    score += 15
    elif hours_before < 12:   score += 10
    elif hours_before < 24:   score += 5

    # Trade-Größe (max 20)
    if size_usd >= 5000:      score += 20
    elif size_usd >= 2000:    score += 15
    elif size_usd >= 1000:    score += 10
    elif size_usd >= 500:     score += 5

    # Preis (max 20)
    if price < 0.05:          score += 20
    elif price < 0.10:        score += 15
    elif price < 0.15:        score += 10
    elif price < 0.20:        score += 5

    # Geopolitik-Bonus (max 10)
    if question and any(k in question.lower() for k in GEO_KEYWORDS):
        score += 10

    # Wallet-Alter — nur Bonus, kein Pflicht-Kriterium (max 15)
    if wallet_age < 7:        score += 15
    elif wallet_age < 30:     score += 10
    elif wallet_age < 90:     score += 5

    # Wenig Trades = suspicious (max 10)
    if lifetime_trades == 1:  score += 10
    elif lifetime_trades <= 3: score += 7
    elif lifetime_trades <= 10: score += 3

    return score


# ── Multi-Wallet Cluster Detection ────────────────
def detect_wallet_clusters(all_suspicious: list) -> list:
    """
    Sucht koordinierte Multi-Wallet-Cluster:
    - 2-8 Wallets kaufen denselben Markt
    - Innerhalb von 60 Minuten
    - Ähnliche Größe (±20%)
    - Preis < 20¢
    """
    from collections import defaultdict

    by_market = defaultdict(list)
    for t in all_suspicious:
        by_market[t["condition_id"]].append(t)

    clusters = []
    for market_id, trades in by_market.items():
        trades_sorted = sorted(
            trades, key=lambda t: float(t.get("trade_ts", 0)))

        seen_keys = set()
        for i, t1 in enumerate(trades_sorted):
            cluster = [t1]
            t1_time = float(t1.get("trade_ts", 0))
            t1_size = float(t1.get("size_usd", 0))

            for t2 in trades_sorted[i + 1:]:
                t2_time = float(t2.get("trade_ts", 0))
                t2_size = float(t2.get("size_usd", 0))

                if t2_time - t1_time > 3600:
                    break

                if t2.get("wallet") == t1.get("wallet"):
                    continue

                if t1_size > 0:
                    size_diff = abs(t2_size - t1_size) / t1_size
                    if size_diff <= 0.20:
                        cluster.append(t2)

            if len(cluster) < 2:
                continue

            wallets_key = frozenset(t["wallet"] for t in cluster)
            dedup_key = (market_id, wallets_key)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            total_invested = sum(
                float(t.get("size_usd", 0)) for t in cluster)
            avg_price = (
                sum(float(t.get("price", 0.01)) for t in cluster)
                / len(cluster))
            if avg_price < 0.05:
                continue  # Last-Minute-Arb (<5¢), kein echter Insider

            potential_profit = round(
                total_invested * (1 / max(avg_price, 0.001) - 1), 2)
            hours = round(float(cluster[0].get("hours_before", 0)), 1)

            clusters.append({
                "market_id": market_id,
                "market": cluster[0].get("question", "Unknown"),
                "wallets": len(cluster),
                "total_invested": round(total_invested, 2),
                "potential_profit": potential_profit,
                "avg_price": round(avg_price, 4),
                "hours_before": hours,
                "wallets_list": [
                    t.get("wallet", "")[:20] for t in cluster],
                "confidence": (
                    "HIGH_CLUSTER"
                    if len(cluster) >= 3
                    else "MEDIUM_CLUSTER"),
            })

    # Besten Cluster pro Markt behalten
    best = {}
    for c in clusters:
        mid = c["market_id"]
        if mid not in best or c["wallets"] > best[mid]["wallets"]:
            best[mid] = c

    return sorted(
        best.values(),
        key=lambda x: x["potential_profit"],
        reverse=True)


# ── Haupt-Analyse ──────────────────────────────────
async def run_analysis():
    print("=" * 65)
    print("POLYMARKET INSIDER PATTERN ANALYZER")
    print(f"Zeitraum: Letzte {ANALYSIS_DAYS} Tage (12 Monate)")
    print(f"Gestartet: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 65)

    connector = aiohttp.TCPConnector(limit=8)
    async with aiohttp.ClientSession(
            connector=connector) as session:

        # get_resolved_markets filtert jetzt streaming — direkt nutzen
        target_markets = await get_resolved_markets(session)
        print(f"\n✅ {len(target_markets)} Märkte nach Streaming-Filter"
              f"\n→ Analysiere {len(target_markets)} Märkte total\n")

        # Fix 1: Checkpoint-System
        checkpoint_path = OUTPUT_DIR / "checkpoint.json"
        start_idx = 0
        all_suspicious = []
        if checkpoint_path.exists():
            try:
                cp = json.loads(checkpoint_path.read_text())
                start_idx = cp.get("last_idx", 0)
                all_suspicious = cp.get("suspicious", [])
                print(f"  ♻️  Checkpoint: Weiter ab Markt {start_idx} "
                      f"({len(all_suspicious)} Verdächtige bisher)")
            except Exception as e:
                print(f"  Checkpoint-Fehler: {e} — Neustart")

        for i, market in enumerate(target_markets):
            if i < start_idx:
                continue
            if i % 20 == 0:
                print(
                    f"  Fortschritt: {i}/"
                    f"{len(target_markets)} Märkte, "
                    f"{len(all_suspicious)} Verdächtige")
            trades = await get_suspicious_trades(
                market, session)
            all_suspicious.extend(trades)
            # Fix 1: Checkpoint alle 500 Märkte
            if i % 500 == 0 and i > 0:
                checkpoint_path.write_text(json.dumps(
                    {"last_idx": i, "suspicious": all_suspicious},
                    default=str))
                print(f"  💾 Checkpoint gespeichert @ Markt {i}")
            await asyncio.sleep(0.15)

        print(
            f"\n✅ {len(all_suspicious)} verdächtige "
            f"Trades gefunden")

        wallet_market_key = {}
        for t in all_suspicious:
            key = f"{t['wallet']}_{t['condition_id']}"
            if key not in wallet_market_key or \
                    t['size_usd'] > \
                    wallet_market_key[key]['size_usd']:
                wallet_market_key[key] = t

        unique_trades = list(wallet_market_key.values())
        print(
            f"✅ {len(unique_trades)} unique "
            f"Wallet+Markt Kombinationen")

        print("\nAnalysiere Wallet-Profile...")

        semaphore = asyncio.Semaphore(5)
        results = []

        async def analyze_wallet(trade):
            async with semaphore:
                wallet = trade["wallet"]

                age, wallet_trades = \
                    await asyncio.gather(
                        get_wallet_age_days(
                            wallet, session),
                        get_wallet_trades(
                            wallet, session)
                    )

                lifetime = len(wallet_trades)

                behavior = await classify_behavior(
                    trade,
                    wallet_trades,
                    trade["resolution_ts"]
                )

                score = calculate_score(
                    age,
                    lifetime,
                    trade["price"],
                    trade["size_usd"],
                    trade["hours_before"],
                    trade.get("question", "")
                )

                classification = (
                    "PUMP_DUMP"
                    if behavior == "SOLD_BEFORE_RESOLUTION"
                    else "HIGH_CONFIDENCE_INSIDER"
                    if score >= 60
                    else "MEDIUM_CONFIDENCE_INSIDER"
                    if score >= 35
                    else "LOW_SIGNAL"
                )

                await asyncio.sleep(0.2)

                return {
                    **trade,
                    "wallet_age_days": age,
                    "lifetime_trades": lifetime,
                    "behavior": behavior,
                    "insider_score": score,
                    "classification": classification
                }

        for batch_start in range(
                0, min(len(unique_trades), 1000), 50):
            batch = unique_trades[batch_start:batch_start+50]
            batch_results = await asyncio.gather(
                *[analyze_wallet(t) for t in batch])
            results.extend(batch_results)
            print(
                f"  {len(results)} Wallets analysiert...")
            await asyncio.sleep(1)

        clusters = detect_wallet_clusters(all_suspicious)

        insider_high = sorted(
            [r for r in results
             if r["classification"] ==
             "HIGH_CONFIDENCE_INSIDER"],
            key=lambda x: x["insider_score"],
            reverse=True
        )
        insider_mid = [
            r for r in results
            if r["classification"] ==
            "MEDIUM_CONFIDENCE_INSIDER"
        ]
        pump_dump = [
            r for r in results
            if r["classification"] == "PUMP_DUMP"
        ]

        ts = datetime.now().strftime("%Y%m%d_%H%M")

        csv_path = OUTPUT_DIR / \
            f"insider_full_{ts}.csv"
        if results:
            with open(csv_path, "w",
                      newline="",
                      encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=list(
                        results[0].keys()))
                writer.writeheader()
                writer.writerows(results)

        json_path = OUTPUT_DIR / \
            f"insider_top_{ts}.json"
        with open(json_path, "w") as f:
            json.dump({
                "generated": datetime.now().isoformat(),
                "analysis_period_days": ANALYSIS_DAYS,
                "total_markets_scanned": len(target_markets),
                "total_suspicious_trades": len(all_suspicious),
                "total_wallets_analyzed": len(results),
                "summary": {
                    "high_confidence_insider": len(insider_high),
                    "medium_confidence": len(insider_mid),
                    "pump_and_dump": len(pump_dump),
                    "low_signal": len(results) -
                        len(insider_high) -
                        len(insider_mid) -
                        len(pump_dump)
                },
                "top_50_insider_wallets": insider_high[:50],
                "top_clusters": clusters[:20],
            }, f, indent=2)

        print("\n" + "=" * 65)
        print("ANALYSE-ERGEBNIS — 12 MONATE")
        print("=" * 65)
        print(f"Gescannte Märkte:       {len(target_markets)}")
        print(f"Verdächtige Trades:     {len(all_suspicious)}")
        print(f"Analysierte Wallets:    {len(results)}")
        print()
        print(f"🔴 HIGH-CONFIDENCE INSIDER: {len(insider_high)}")
        print(f"🟡 MEDIUM-CONFIDENCE:       {len(insider_mid)}")
        print(f"⚡ PUMP & DUMP:             {len(pump_dump)}")
        print(f"🕸️  WALLET-CLUSTER:         {len(clusters)}")
        print()

        if insider_high:
            avg_score = sum(
                r["insider_score"]
                for r in insider_high
            ) / len(insider_high)
            avg_age = sum(
                r["wallet_age_days"]
                for r in insider_high
            ) / len(insider_high)
            avg_size = sum(
                r["size_usd"]
                for r in insider_high
            ) / len(insider_high)
            avg_price = sum(
                r["price"]
                for r in insider_high
            ) / len(insider_high)
            avg_hours = sum(
                r["hours_before"]
                for r in insider_high
            ) / len(insider_high)

            print("INSIDER-MUSTER (Durchschnitt):")
            print(f"  Wallet-Alter:  {avg_age:.1f} Tage")
            print(f"  Einsatz:       ${avg_size:,.0f}")
            print(f"  Einstieg:      {avg_price*100:.1f}¢")
            print(
                f"  Vor Resolution:{avg_hours:.1f}h")
            print(f"  Insider-Score: {avg_score:.0f}/100")

        if pump_dump:
            print()
            print("PUMP & DUMP MUSTER:")
            avg_pd_hours = sum(
                r["hours_before"]
                for r in pump_dump
            ) / len(pump_dump)
            print(
                f"  Ø Stunden vor Verkauf: "
                f"{avg_pd_hours:.1f}h")
            print(
                f"  Ø Einsatz: "
                f"${sum(r['size_usd'] for r in pump_dump)/len(pump_dump):,.0f}")

        if clusters:
            print()
            print("TOP-10 WALLET-CLUSTER:")
            print(f"  {'Wallets':>7} {'Invested':>10} {'Pot.Profit':>12} "
                  f"{'Price':>7} {'h.before':>8}  Markt")
            print("  " + "-" * 63)
            for c in clusters[:10]:
                conf = "🔴" if c["confidence"] == "HIGH_CLUSTER" else "🟡"
                print(
                    f"  {conf} {c['wallets']:>5}  "
                    f"${c['total_invested']:>9,.0f}  "
                    f"${c['potential_profit']:>11,.0f}  "
                    f"{c['avg_price']*100:>5.1f}¢  "
                    f"{c['hours_before']:>6.1f}h  "
                    f"{c['market'][:45]}")

        print()
        print(f"📁 CSV: {csv_path}")
        print(f"📁 JSON: {json_path}")
        print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_analysis())
