"""Read-Only Kalshi Weather Markets Scraper.

Benoetigt keinen Account, keinen API-Key. Liest oeffentliche Marktdaten fuer
Signal-Generierung und Cross-Market-Comparison mit Polymarket.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import time
import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Die bekannten Daily-Temperature Series-Tickers (High & Low)
WEATHER_SERIES_HIGH = [
    "KXHIGHNY", "KXHIGHMIA", "KXHIGHLAX", "KXHIGHAUS", "KXHIGHCHI",
    "KXHIGHTPHX", "KXHIGHTSFO", "KXHIGHTGATL", "KXHIGHPHIL", "KXHIGHTDC",
    "KXHIGHDEN", "KXHIGHTSEA", "KXHIGHTHOU", "KXHIGHTMIN", "KXHIGHTBOS",
    "KXHIGHTLV", "KXHIGHTOKC",
]
WEATHER_SERIES_LOW = [
    "KXLOWTCHI", "KXLOWTNYC", "KXLOWTAUS", "KXLOWTMIA",
    "KXLOWTDEN", "KXLOWTPHIL", "KXLOWTLAX",
]


@dataclass
class KalshiMarket:
    ticker: str
    title: str
    yes_bid: float
    yes_ask: float
    last_price: float | None
    volume: int
    status: str


def _get(path: str, params: dict | None = None, retries: int = 3) -> dict:
    url = f"{BASE}{path}"
    for i in range(retries):
        r = requests.get(url, params=params, timeout=15,
                         headers={"User-Agent": "KongTrade-ReadOnly/1.0"})
        if r.status_code == 429:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Kalshi API failed after {retries} retries: {url}")


def fetch_series_markets(series_ticker: str, status: str = "open") -> list[KalshiMarket]:
    data = _get("/markets", params={"series_ticker": series_ticker,
                                    "status": status, "limit": 100})
    out = []
    for m in data.get("markets", []):
        out.append(KalshiMarket(
            ticker=m["ticker"],
            title=m.get("title", ""),
            yes_bid=float(m.get("yes_bid_dollars") or m.get("yes_bid", 0) / 100),
            yes_ask=float(m.get("yes_ask_dollars") or m.get("yes_ask", 0) / 100),
            last_price=(float(m["last_price_dollars"])
                        if m.get("last_price_dollars") else None),
            volume=int(m.get("volume", 0)),
            status=m.get("status", ""),
        ))
    return out


def fetch_orderbook(ticker: str) -> dict:
    return _get(f"/markets/{ticker}/orderbook").get("orderbook_fp", {})


def snapshot_all_weather(series: Iterable[str] | None = None) -> dict[str, list[KalshiMarket]]:
    series = list(series or WEATHER_SERIES_HIGH)
    out = {}
    for s in series:
        try:
            out[s] = fetch_series_markets(s)
        except Exception as e:
            print(f"[kalshi] {s} failed: {e}")
            out[s] = []
        time.sleep(0.05)   # <20 req/s hold
    return out


if __name__ == "__main__":
    nyc = fetch_series_markets("KXHIGHNY")
    print(f"KXHIGHNY: {len(nyc)} open markets")
    for m in nyc[:5]:
        print(f"  {m.ticker:35} bid={m.yes_bid:.2f} ask={m.yes_ask:.2f} vol={m.volume}")
