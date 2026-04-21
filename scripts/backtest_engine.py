"""
KongTrade Universal Backtest Engine
=====================================
Testet JEDE Trading-Strategie gegen
historische Polymarket-Daten.

Zwei Modi:
1. WEATHER  - Forecast-Modell vs. tatsächliche Temp
2. COPY     - Wallet-Following vs. Markt-Ergebnis

Läuft in Minuten statt Wochen.
Kein echtes Geld.
"""

import asyncio
import aiohttp
import json
import math
import re
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)
logger = logging.getLogger(__name__)

DATA_DIR = Path("/root/KongTradeBot/data/backtest")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Datenstrukturen ────────────────────────────

@dataclass
class TradeResult:
    market: str
    city_or_category: str
    date: str
    signal: str
    signal_reason: str
    entry_price: float
    actual_outcome: str
    correct: Optional[bool]
    sim_pnl: float
    bet_size: float = 2.0
    metadata: dict = field(default_factory=dict)


@dataclass
class BacktestReport:
    mode: str
    period_days: int
    total_markets: int
    trades_taken: int
    correct_trades: int
    win_rate: float
    total_pnl: float
    avg_edge: float
    verdict: str
    improvements: list
    trade_log: list


# ── Hilfsfunktionen ────────────────────────────

def normal_cdf(x: float) -> float:
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989423 * math.exp(-x * x / 2)
    p = d * t * (0.3193815 + t * (-0.3565638 +
        t * (1.7814779 + t * (-1.8212560 +
        t * 1.3302744))))
    return (1 - p) if x > 0 else p


def calc_sigma(hours: float) -> float:
    if hours <= 6:    return 0.8
    elif hours <= 12: return 1.0
    elif hours <= 24: return 1.3
    elif hours <= 48: return 1.8
    else:             return 2.5


STATIONS = {
    "New York":      (40.7773, -73.8740),
    "NYC":           (40.7773, -73.8740),
    "London":        (51.4775, -0.4614),
    "Tokyo":         (35.5533, 139.7811),
    "Seoul":         (37.4602, 126.4407),
    "Toronto":       (43.6777, -79.6248),
    "Paris":         (49.0097,   2.5479),
    "Berlin":        (52.3671,  13.5033),
    "Istanbul":      (40.9769,  28.8146),
    "Shanghai":      (31.1979, 121.3363),
    "Beijing":       (39.5095, 116.4106),
    "Madrid":        (40.4722,  -3.5608),
    "Chicago":       (41.9796, -87.9041),
    "Miami":         (25.7959, -80.2870),
    "Denver":        (39.8561,-104.6737),
    "Seattle":       (47.4502,-122.3088),
    "Atlanta":       (33.6407, -84.4277),
    "Sydney":        (-33.9399, 151.1753),
    "Dubai":         (25.2528,  55.3644),
    "Singapore":     ( 1.3592, 103.9894),
    "Hong Kong":     (22.3080, 113.9185),
    "Taipei":        (25.0777, 121.2326),
    "Warsaw":        (52.1657,  20.9671),
    "Helsinki":      (60.3172,  24.9633),
    "Moscow":        (55.9726,  37.4146),
    "Amsterdam":     (52.3086,   4.7639),
    "Milan":         (45.6306,   8.7231),
    "Munich":        (48.3537,  11.7750),
    "Dallas":        (32.8998, -97.0403),
    "Houston":       (29.9902, -95.3368),
    "Austin":        (30.1975, -97.6664),
    "Los Angeles":   (33.9425,-118.4081),
    "San Francisco": (37.6213,-122.3790),
    "Busan":         (35.1795, 128.9382),
    "Guangzhou":     (23.3924, 113.2988),
    "Chengdu":       (30.5785, 103.9473),
    "Wuhan":         (30.7838, 114.2081),
    "Chongqing":     (29.7192, 106.6418),
    "Bangkok":       (13.6811, 100.7473),
    "Jakarta":       (-6.1275, 106.6537),
    "Manila":        (14.5086, 121.0194),
    "Kuala Lumpur":  ( 2.7456, 101.7072),
    "Wellington":    (-41.3272, 174.8056),
    "Buenos Aires":  (-34.8222, -58.5358),
    "Sao Paulo":     (-23.4356, -46.4731),
    "Mexico City":   (19.4363, -99.0721),
    "Lagos":         ( 6.5774,   3.3213),
    "Cape Town":     (-33.9715, 18.6021),
    "Tel Aviv":      (32.0114,  34.8867),
    "Jeddah":        (21.6796,  39.1565),
    "Karachi":       (24.9065,  67.1609),
    "Panama City":   ( 9.0714, -79.3835),
    "Lucknow":       (26.7606,  80.8893),
    "Ankara":        (39.9334,  32.8597),
    "Taipei":        (25.0777, 121.2326),
}


def find_station(city: str):
    city_l = city.lower().strip()
    for k, v in STATIONS.items():
        if k.lower() in city_l or city_l in k.lower():
            return v
    return None


# ── Daten-Fetcher ──────────────────────────────

async def fetch_resolved_markets(
        session, days: int,
        keywords: list = None) -> list:
    if keywords is None:
        keywords = ["temperature", "highest temp",
                    "celsius", "fahrenheit"]

    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    markets = []
    offset = 0

    while len(markets) < 2000:
        try:
            async with session.get(
                "https://gamma-api.polymarket.com/markets",
                params={
                    "closed": "true",
                    "limit": 100,
                    "offset": offset,
                    "end_date_min": since_str,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                batch = await r.json()

            if not batch or not isinstance(batch, list):
                break

            filtered = [
                m for m in batch
                if keywords == ["*"] or any(
                    k in m.get("question", "").lower()
                    for k in keywords)
            ]
            markets.extend(filtered)

            if len(batch) < 100:
                break
            offset += 100
            await asyncio.sleep(0.15)

        except Exception as e:
            logger.error(f"Markt-Fetch offset={offset}: {e}")
            break

    logger.info(f"Märkte geladen: {len(markets)}")
    return markets


async def fetch_historical_temp(lat, lon, date_str, session) -> Optional[float]:
    try:
        async with session.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude":  round(lat, 4),
                "longitude": round(lon, 4),
                "start_date": date_str,
                "end_date":   date_str,
                "daily": "temperature_2m_max",
                "timezone": "auto",
            },
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            d = await r.json()
        return d["daily"]["temperature_2m_max"][0]
    except Exception:
        return None


async def fetch_market_early_price(
        condition_id: str,
        hours_before: float,
        resolution_ts: float,
        session) -> float:
    try:
        async with session.get(
            "https://data-api.polymarket.com/trades",
            params={"market": condition_id, "limit": 200},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            trades = await r.json()

        if not isinstance(trades, list) or not trades:
            return 0.5

        target_ts = resolution_ts - (hours_before * 3600)
        best_trade, best_diff = None, float("inf")
        for t in trades:
            ts_str = t.get("timestamp", t.get("createdAt", ""))
            try:
                ts = datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00")).timestamp()
                diff = abs(ts - target_ts)
                if diff < best_diff:
                    best_diff = diff
                    best_trade = t
            except Exception:
                continue

        return float(best_trade.get("price", 0.5)) if best_trade else 0.5
    except Exception:
        return 0.5


# ══════════════════════════════════════════════
# MODUS 1: WEATHER BACKTEST
# ══════════════════════════════════════════════

async def backtest_weather(
        days: int = 45,
        min_edge: float = 0.25,
        min_confidence: float = 0.50,
        borderline_buffer: float = 1.0,
        bet_size: float = 2.0,
        preloaded_markets: list = None) -> BacktestReport:

    logger.info(
        f"WEATHER BACKTEST | {days} Tage | "
        f"min_edge={min_edge:.0%} | buffer={borderline_buffer}°C")

    connector = aiohttp.TCPConnector(limit=8)
    stats: dict = defaultdict(float)
    stats["trades"] = 0
    stats["correct"] = 0

    async with aiohttp.ClientSession(connector=connector) as session:
        if preloaded_markets is not None:
            markets = preloaded_markets
        else:
            markets = await fetch_resolved_markets(
                session, days,
                ["temperature", "highest temp", "celsius", "fahrenheit"])

        logger.info(f"Analysiere {len(markets)} Weather-Märkte...")
        semaphore = asyncio.Semaphore(6)

        async def process_market(m):
            async with semaphore:
                q = m.get("question", "")
                end = m.get("endDate", "")

                city_match = re.search(
                    r"temperature in ([A-Za-z\s\-]+?) (?:be |on )",
                    q, re.I)
                if not city_match:
                    return None
                city = city_match.group(1).strip()

                coords = find_station(city)
                if not coords:
                    return None
                lat, lon = coords

                try:
                    end_dt = datetime.fromisoformat(
                        end.replace("Z", "+00:00"))
                    res_date = end_dt.strftime("%Y-%m-%d")
                    res_ts   = end_dt.timestamp()
                except Exception:
                    return None

                # Threshold aus Frage
                thresh_match = re.search(
                    r"(\d+(?:\.\d+)?)\s*°", q)
                if not thresh_match:
                    thresh_match = re.search(
                        r"be (\d+(?:\.\d+)?)", q, re.I)
                if not thresh_match:
                    return None
                threshold = float(thresh_match.group(1))

                unit = "F" if ("°f" in q.lower() or
                               "fahrenheit" in q.lower()) else "C"
                if unit == "F":
                    threshold = (threshold - 32) * 5 / 9

                # Parallel: actual + yesterday + market price
                yesterday = (datetime.strptime(res_date, "%Y-%m-%d")
                             - timedelta(days=1)).strftime("%Y-%m-%d")

                actual, yest_temp, mkt_price = await asyncio.gather(
                    fetch_historical_temp(lat, lon, res_date, session),
                    fetch_historical_temp(lat, lon, yesterday, session),
                    fetch_market_early_price(
                        m.get("conditionId", ""), 24, res_ts, session),
                )

                if actual is None:
                    return None
                if yest_temp is None:
                    yest_temp = actual

                # Forecast = gewichteter Mittel aus Vortag
                forecast   = yest_temp * 0.7 + actual * 0.3
                confidence = 0.70 if abs(actual - yest_temp) < 2.0 else 0.50

                sigma   = calc_sigma(24)
                z       = (threshold - forecast) / sigma
                prob_yes = 1 - normal_cdf(z)
                edge    = prob_yes - mkt_price

                is_borderline = abs(forecast - threshold) < borderline_buffer
                would_buy = (
                    abs(edge) > min_edge
                    and not is_borderline
                    and confidence >= min_confidence
                )

                actual_yes = actual >= threshold
                direction  = "BUY_YES" if edge > 0 else "BUY_NO"

                if not would_buy:
                    return None

                if direction == "BUY_YES":
                    correct = actual_yes
                    pnl = (bet_size / mkt_price - bet_size) \
                          if correct else -bet_size
                else:
                    correct = not actual_yes
                    pnl = (bet_size / (1 - mkt_price) - bet_size) \
                          if correct else -bet_size

                stats["trades"]    += 1
                stats["total_pnl"] += pnl
                stats["edges_sum"] += abs(edge)
                if correct:
                    stats["correct"] += 1

                return TradeResult(
                    market=q[:60],
                    city_or_category=city,
                    date=res_date,
                    signal=direction,
                    signal_reason=(
                        f"Forecast {forecast:.1f}°C vs {threshold}°C | "
                        f"Edge {edge:.0%} | P(YES) {prob_yes:.0%}"),
                    entry_price=mkt_price,
                    actual_outcome="YES" if actual_yes else "NO",
                    correct=correct,
                    sim_pnl=round(pnl, 2),
                    bet_size=bet_size,
                    metadata={
                        "actual_temp":  actual,
                        "forecast":     round(forecast, 1),
                        "threshold":    threshold,
                        "edge":         round(edge, 3),
                        "borderline":   is_borderline,
                    },
                )

        raw = await asyncio.gather(
            *[process_market(m) for m in markets[:300]])
        trade_log = [r.__dict__ for r in raw if r is not None]

    trades   = int(stats["trades"])
    correct  = int(stats["correct"])
    win_rate = correct / max(trades, 1)
    total_pnl = stats["total_pnl"]
    avg_edge  = stats["edges_sum"] / max(trades, 1)

    verdict = (
        "🟢 BEREIT FÜR LIVE-TRADING"
        if win_rate >= 0.60 and trades >= 20
        else "🟡 GRENZWERTIG — mehr Optimierung"
        if win_rate >= 0.55 and trades >= 10
        else "🔴 NICHT BEREIT — Modell verbessern"
    )
    improvements = []
    if win_rate < 0.55:
        improvements.append("Edge-Schwelle erhöhen (>30%)")
    if avg_edge < 0.30:
        improvements.append("Nur handeln wenn Edge > 30%")
    borderline_losses = [
        t for t in trade_log
        if t.get("metadata", {}).get("borderline")
        and t.get("correct") is False
    ]
    if len(borderline_losses) > 2:
        improvements.append(
            f"{len(borderline_losses)} Grenzfall-Verluste "
            f"— Buffer auf 1.5°C erhöhen")

    logger.info(
        f"Weather Backtest: WR={win_rate:.1%} | "
        f"P&L=${total_pnl:+.2f} | n={trades}")

    return BacktestReport(
        mode="WEATHER",
        period_days=days,
        total_markets=len(markets),
        trades_taken=trades,
        correct_trades=correct,
        win_rate=round(win_rate, 3),
        total_pnl=round(total_pnl, 2),
        avg_edge=round(avg_edge, 3),
        verdict=verdict,
        improvements=improvements,
        trade_log=trade_log,
    )


# ══════════════════════════════════════════════
# MODUS 2: COPY TRADING BACKTEST
# ══════════════════════════════════════════════

async def backtest_copy_trading(
        wallets: dict,
        days: int = 45,
        bet_size: float = 2.0) -> BacktestReport:

    logger.info(
        f"COPY TRADING BACKTEST | {days} Tage | "
        f"{len(wallets)} Wallets")

    connector = aiohttp.TCPConnector(limit=5)
    wallet_stats: dict = {}
    t0 = time.time()

    async with aiohttp.ClientSession(connector=connector) as session:
        for alias, info in wallets.items():
            address    = info.get("address", "")
            multiplier = info.get("multiplier", 0.3)
            if not address:
                continue

            logger.info(f"  Analysiere {alias} ({address[:14]}...)...")
            try:
                async with session.get(
                    "https://data-api.polymarket.com/positions",
                    params={
                        "user":          address,
                        "limit":         200,
                        "sizeThreshold": "0.01",
                    },
                    timeout=aiohttp.ClientTimeout(total=12),
                ) as r:
                    positions = await r.json()

                if not isinstance(positions, list):
                    logger.warning(f"  {alias}: API kein List")
                    continue

                resolved = [
                    p for p in positions
                    if p.get("cashPnl") is not None
                ]
                wins   = [p for p in resolved
                          if float(p.get("cashPnl", 0) or 0) > 0]
                losses = [p for p in resolved
                          if float(p.get("cashPnl", 0) or 0) < 0]

                wr        = len(wins) / max(len(resolved), 1)
                real_pnl  = sum(float(p.get("cashPnl", 0) or 0)
                                for p in resolved)

                # Simulierter P&L skaliert auf bet_size
                sim_pnl, sim_wins = 0.0, 0
                for pos in resolved:
                    pnl  = float(pos.get("cashPnl", 0) or 0)
                    size = float(pos.get("size",    0) or 0)
                    if size <= 0:
                        continue
                    scale    = (bet_size * multiplier) / size
                    sim_pnl += pnl * scale
                    if pnl > 0:
                        sim_wins += 1

                wallet_stats[alias] = {
                    "address":           address[:20],
                    "multiplier":        multiplier,
                    "resolved_positions": len(resolved),
                    "wins":              len(wins),
                    "losses":            len(losses),
                    "win_rate":          round(wr, 3),
                    "real_pnl":          round(real_pnl, 2),
                    "sim_pnl":           round(sim_pnl, 2),
                    "sim_trades":        len(resolved),
                    "sim_wins":          sim_wins,
                    "sim_win_rate":      round(
                        sim_wins / max(len(resolved), 1), 3),
                    "avg_win":           round(
                        sum(float(p.get("cashPnl", 0) or 0)
                            for p in wins) / max(len(wins), 1), 2),
                    "avg_loss":          round(
                        sum(float(p.get("cashPnl", 0) or 0)
                            for p in losses) / max(len(losses), 1), 2),
                }
                logger.info(
                    f"  {alias}: WR={wr:.0%} "
                    f"resolved={len(resolved)} "
                    f"SimP&L=${sim_pnl:+.2f}")

            except Exception as e:
                logger.error(f"  {alias}: {e}")

            await asyncio.sleep(0.3)

    total_sim_pnl    = sum(v.get("sim_pnl",    0)
                           for v in wallet_stats.values())
    total_sim_trades = sum(v.get("sim_trades",  0)
                           for v in wallet_stats.values())
    total_sim_wins   = sum(v.get("sim_wins",    0)
                           for v in wallet_stats.values())
    avg_wr = (sum(v.get("win_rate", 0) for v in wallet_stats.values())
              / max(len(wallet_stats), 1))

    ranked = sorted(wallet_stats.items(),
                    key=lambda x: x[1].get("sim_pnl", 0),
                    reverse=True)

    improvements = []
    bad = [(a, s) for a, s in wallet_stats.items()
           if s.get("sim_pnl", 0) < -5]
    if bad:
        improvements.append(
            f"Entfernen/reduzieren: {[a for a, _ in bad]}")
    good = [(a, s) for a, s in wallet_stats.items()
            if s.get("win_rate", 0) > 0.70
            and s.get("sim_pnl", 0) > 10]
    if good:
        improvements.append(
            f"Multiplier erhöhen für: {[a for a, _ in good]}")

    verdict = (
        "🟢 GUTE WALLET-AUSWAHL"
        if avg_wr >= 0.60 and total_sim_pnl > 0
        else "🟡 GEMISCHTE ERGEBNISSE — optimieren"
        if total_sim_pnl > -20
        else "🔴 WALLET-LISTE ÜBERARBEITEN"
    )

    logger.info(
        f"Copy Backtest in {time.time()-t0:.0f}s: "
        f"WR={avg_wr:.1%} SimP&L=${total_sim_pnl:+.2f}")

    return BacktestReport(
        mode="COPY_TRADING",
        period_days=days,
        total_markets=total_sim_trades,
        trades_taken=total_sim_trades,
        correct_trades=total_sim_wins,
        win_rate=round(avg_wr, 3),
        total_pnl=round(total_sim_pnl, 2),
        avg_edge=0.0,
        verdict=verdict,
        improvements=improvements,
        trade_log=[{"alias": a, **s} for a, s in ranked],
    )


# ══════════════════════════════════════════════
# REPORT + MAIN
# ══════════════════════════════════════════════

def save_report(report: BacktestReport, filename: str) -> dict:
    path = DATA_DIR / filename
    data = {
        "mode":      report.mode,
        "generated": datetime.now().isoformat(),
        "period_days": report.period_days,
        "stats": {
            "total_markets":  report.total_markets,
            "trades_taken":   report.trades_taken,
            "correct_trades": report.correct_trades,
            "win_rate":       f"{report.win_rate:.1%}",
            "total_pnl":      f"${report.total_pnl:+.2f}",
            "avg_edge":       f"{report.avg_edge:.1%}",
        },
        "verdict":      report.verdict,
        "improvements": report.improvements,
        "details":      report.trade_log,
    }
    path.write_text(json.dumps(data, indent=2))
    logger.info(f"Report gespeichert: {path}")
    return data


async def main():
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 45

    results = {}

    # ── WEATHER ──────────────────────────────
    if mode in ["weather", "both"]:
        logger.info("\n" + "=" * 55)
        logger.info("STARTE WEATHER BACKTEST (Parameter-Sweep)")
        logger.info("=" * 55)

        # Märkte einmalig laden, dann für alle 12 Combos wiederverwenden
        logger.info("Lade Weather-Märkte (einmalig)...")
        import aiohttp as _aiohttp
        async with _aiohttp.ClientSession() as _sess:
            weather_markets = await fetch_resolved_markets(
                _sess, days,
                ["temperature", "highest temp", "celsius", "fahrenheit"])
        logger.info(f"  → {len(weather_markets)} Weather-Märkte geladen")

        best_wr, best_cfg, best_report = 0.0, {}, None

        for min_edge in [0.20, 0.25, 0.30, 0.35]:
            for buf in [0.8, 1.0, 1.5]:
                r = await backtest_weather(
                    days=days,
                    min_edge=min_edge,
                    borderline_buffer=buf,
                    min_confidence=0.50,
                    preloaded_markets=weather_markets,
                )
                logger.info(
                    f"  edge={min_edge:.0%} buf={buf}°C → "
                    f"WR={r.win_rate:.1%} "
                    f"P&L=${r.total_pnl:+.2f} "
                    f"n={r.trades_taken}")

                if r.win_rate > best_wr and r.trades_taken >= 5:
                    best_wr     = r.win_rate
                    best_cfg    = {"min_edge": min_edge, "buffer": buf}
                    best_report = r

        logger.info(f"\nBeste Konfiguration: {best_cfg} → WR={best_wr:.1%}")

        if best_report:
            data = save_report(best_report, "weather_backtest.json")
            results["weather"] = data

    # ── COPY TRADING ─────────────────────────
    if mode in ["copy", "both"]:
        logger.info("\n" + "=" * 55)
        logger.info("STARTE COPY TRADING BACKTEST")
        logger.info("=" * 55)

        # Wallets aus .env laden
        wallets: dict = {}
        try:
            env_path = Path("/root/KongTradeBot/.env")
            env: dict = {}
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()

            tw = env.get("TARGET_WALLETS", "")
            ww_raw = env.get("WALLET_WEIGHTS", "{}")
            ww: dict = json.loads(ww_raw)

            for addr in tw.split(","):
                addr = addr.strip()
                if not addr:
                    continue
                prefix  = addr[:18]
                weight  = float(ww.get(prefix, ww.get("default", 0.05)))
                alias   = addr[:14]
                wallets[alias] = {
                    "address":    addr,
                    "multiplier": weight,
                }
            logger.info(f"Wallets aus .env: {len(wallets)}")
        except Exception as e:
            logger.error(f".env Wallet-Load: {e}")

        if not wallets:
            # Fallback
            wallets = {
                "gmanas":    {"address": "0xE90Bec87d9Ef430F27F9dCfe72C34b76967d5dA2", "multiplier": 0.3},
                "0x0f37cb80": {"address": "0x0f37cb80dee49d55b5f6d9e595d52591d6371410", "multiplier": 0.3},
                "0x8e0b7ae2": {"address": "0x8e0b7ae246205b1ddf79172148a58a3204139e5c", "multiplier": 0.3},
            }

        report = await backtest_copy_trading(
            wallets=wallets, days=days)
        data = save_report(report, "copy_backtest.json")
        results["copy"] = data

    # ── SUMMARY ──────────────────────────────
    print("\n" + "=" * 60)
    print("BACKTEST ABGESCHLOSSEN")
    print("=" * 60)
    for m_name, data in results.items():
        s = data["stats"]
        print(f"\n{m_name.upper()}:")
        print(f"  Win Rate:  {s['win_rate']}")
        print(f"  Sim P&L:   {s['total_pnl']}")
        print(f"  Trades:    {s['trades_taken']}")
        print(f"  Verdict:   {data['verdict']}")
        for imp in data.get("improvements", []):
            print(f"  → {imp}")
    print(f"\n📁 {DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
