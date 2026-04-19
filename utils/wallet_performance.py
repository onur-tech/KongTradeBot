"""
utils/wallet_performance.py — Per-Wallet-Performance-Metriken

Datenquellen:
  - trades_archive.json  → Trade-Historie, ergebnis, gewinn_verlust_usdc
  - /api/portfolio       → Unrealisierter PnL für offene Positionen
  - slippage_log.jsonl   → Slippage-Daten (seit 2026-04-19)

Hinweis: Wenn ergebnis=='' und aufgeloest==False → Trade ist noch offen.
Unrealisierter PnL wird aus Portfolio-API geladen (condition_id == market_id).
"""
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR      = Path(__file__).parent.parent
ARCHIVE_FILE  = BASE_DIR / "trades_archive.json"
SLIPPAGE_FILE = BASE_DIR / "data" / "slippage_log.jsonl"

LOW_SAMPLE_THRESHOLD = 5

WALLET_NAMES = {
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": "Gambler1968",
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": "kcnyekchno",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": "HOOK",
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": "sovereign2013",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": "denizz",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": "wan123",
    "0x019782cab5d844f02bafb71f512758be78579f3c": "majorexploiter",
    "0x492442eab586f242b53bda933fd5de859c8a3782": "April#1 Sports",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": "HorizonSplendidView",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": "reachingthesky",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",
    "0xbddf61af533ff524d27154e589d2d7a81510c684": "Countryside",
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": "Crypto Spezialist",
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": "BoneReader",
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": "DrPufferfish",
}


def _short(addr: str) -> str:
    return addr[:6] + "..." + addr[-4:] if len(addr) > 12 else addr


def _load_archive(since_days: int) -> list[dict]:
    if not ARCHIVE_FILE.exists():
        return []
    try:
        raw = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        trades = raw if isinstance(raw, list) else raw.get("trades", [])
    except Exception:
        return []

    if since_days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
        trades = [t for t in trades if t.get("datum", "9999") >= cutoff]

    return [t for t in trades if t.get("modus") == "LIVE"]


def _load_portfolio_pnl() -> dict[str, dict]:
    """Lädt unrealisierten PnL aus /api/portfolio. Key = condition_id."""
    try:
        data = json.loads(urllib.request.urlopen("http://localhost:5000/api/portfolio", timeout=3).read())
        return {p["condition_id"]: p for p in data.get("positions", []) if p.get("condition_id")}
    except Exception:
        return {}


def _load_slippage() -> dict[str, list[float]]:
    """Lädt Slippage-Daten; Key = whale_wallet[:20]... prefix."""
    result: dict[str, list[float]] = defaultdict(list)
    if not SLIPPAGE_FILE.exists():
        return result
    try:
        for line in SLIPPAGE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if not e.get("dry_run"):
                    result[e["whale_wallet"]].append(e["delta_cents"])
            except Exception:
                pass
    except Exception:
        pass
    return result


def _timeframe_bucket(closes_in_label: str) -> str:
    """
    Klassifiziert anhand des Portfolio-Feldes closes_in_label
    ('10d 17h', '2d 4h', '0d 8h', ...) in Zeitfenster-Buckets.
    Fallback wenn kein Label: 'unknown'.
    """
    if not closes_in_label or closes_in_label == "—":
        return "unknown"
    label = closes_in_label.lower()
    days = 0
    if "d" in label:
        try:
            days = int(label.split("d")[0].strip())
        except ValueError:
            pass
    if days == 0:
        return "same_day"
    elif days <= 3:
        return "short"
    elif days <= 10:
        return "medium"
    else:
        return "long"


def _empty_stats(wallet: str) -> dict:
    name = WALLET_NAMES.get(wallet.lower(), _short(wallet))
    return {
        "wallet":           wallet,
        "name":             name,
        "trades_count":     0,
        "wins_count":       0,
        "losses_count":     0,
        "pending_count":    0,
        "hit_rate":         None,
        "roi_pct":          None,
        "avg_position_size": None,
        "total_invested_usdc": 0.0,
        "total_return_usdc":   0.0,
        "net_pnl_usdc":       0.0,
        "unrealized_pnl_usdc": 0.0,
        "low_sample":          True,
        "note":               "n/a",
    }


def compute_wallet_stats(wallet_address: str, since_days: int = 30) -> dict:
    wallet = wallet_address.lower()
    trades = [t for t in _load_archive(since_days)
              if (t.get("source_wallet") or "").lower() == wallet]

    portfolio_pnl = _load_portfolio_pnl()
    slippage_map  = _load_slippage()

    name = WALLET_NAMES.get(wallet, _short(wallet_address))

    wins = losses = 0
    total_invested = total_return = unrealized_pnl = 0.0

    for t in trades:
        invested = float(t.get("einsatz_usdc") or 0)
        total_invested += invested
        ergebnis = (t.get("ergebnis") or "").upper()

        if ergebnis == "GEWINN":
            wins += 1
            total_return += invested + float(t.get("gewinn_verlust_usdc") or 0)
        elif ergebnis == "VERLUST":
            losses += 1
            total_return += invested + float(t.get("gewinn_verlust_usdc") or 0)
        else:
            # Offen: unrealisierten PnL aus Portfolio laden
            mid = (t.get("market_id") or "").lower()
            port = portfolio_pnl.get(mid)
            if port:
                unrealized_pnl += float(port.get("pnl_usdc") or 0)

    pending    = len(trades) - wins - losses
    hit_rate   = (wins / (wins + losses) * 100) if (wins + losses) > 0 else None
    net_pnl    = total_return - total_invested
    # ROI only meaningful when at least one trade is resolved (no division over pending-only)
    resolved_invested = sum(
        float(t.get("einsatz_usdc") or 0) for t in trades
        if (t.get("ergebnis") or "").upper() in ("GEWINN", "VERLUST")
    )
    roi_pct  = (net_pnl / resolved_invested * 100) if (wins + losses) > 0 and resolved_invested > 0 else None
    avg_size = (total_invested / len(trades)) if trades else None

    # Slippage: wallet key ist "0x1234...abcd" (ersten 20 + "..." Format aus slippage_tracker)
    slip_key = wallet_address[:20] + "..."
    slippage_vals = slippage_map.get(slip_key, [])
    avg_slippage = (sum(slippage_vals) / len(slippage_vals)) if slippage_vals else None

    low_sample = len(trades) < LOW_SAMPLE_THRESHOLD

    note_parts = []
    if low_sample:
        note_parts.append(f"low_sample ({len(trades)} trades)")
    if (wins + losses) == 0 and pending > 0:
        note_parts.append("alle Trades noch offen — unrealisierter PnL als Proxy")

    return {
        "wallet":              wallet_address,
        "name":                name,
        "trades_count":        len(trades),
        "wins_count":          wins,
        "losses_count":        losses,
        "pending_count":       pending,
        "hit_rate":            round(hit_rate, 1) if hit_rate is not None else None,
        "roi_pct":             round(roi_pct, 1) if roi_pct is not None else None,
        "avg_position_size":   round(avg_size, 2) if avg_size is not None else None,
        "total_invested_usdc": round(total_invested, 2),
        "total_return_usdc":   round(total_return, 2),
        "net_pnl_usdc":        round(net_pnl, 2),
        "unrealized_pnl_usdc": round(unrealized_pnl, 2),
        "avg_slippage_cents":  round(avg_slippage, 2) if avg_slippage is not None else None,
        "slippage_trades":     len(slippage_vals),
        "low_sample":          low_sample,
        "note":                "; ".join(note_parts) if note_parts else "ok",
    }


def compute_by_category(wallet_address: str, since_days: int = 30) -> dict[str, dict]:
    wallet = wallet_address.lower()
    trades = [t for t in _load_archive(since_days)
              if (t.get("source_wallet") or "").lower() == wallet]
    portfolio_pnl = _load_portfolio_pnl()

    by_cat: dict[str, dict] = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0, "pending": 0,
        "invested": 0.0, "pnl": 0.0, "unrealized_pnl": 0.0,
    })

    for t in trades:
        cat      = (t.get("kategorie") or "sonstiges").lower()
        invested = float(t.get("einsatz_usdc") or 0)
        ergebnis = (t.get("ergebnis") or "").upper()
        by_cat[cat]["trades"]   += 1
        by_cat[cat]["invested"] += invested

        if ergebnis == "GEWINN":
            by_cat[cat]["wins"] += 1
            by_cat[cat]["pnl"]  += float(t.get("gewinn_verlust_usdc") or 0)
        elif ergebnis == "VERLUST":
            by_cat[cat]["losses"] += 1
            by_cat[cat]["pnl"]    += float(t.get("gewinn_verlust_usdc") or 0)
        else:
            by_cat[cat]["pending"] += 1
            mid  = (t.get("market_id") or "").lower()
            port = portfolio_pnl.get(mid)
            if port:
                by_cat[cat]["unrealized_pnl"] += float(port.get("pnl_usdc") or 0)

    result = {}
    for cat, d in sorted(by_cat.items()):
        w_l = d["wins"] + d["losses"]
        result[cat] = {
            "trades":           d["trades"],
            "wins":             d["wins"],
            "losses":           d["losses"],
            "pending":          d["pending"],
            "hit_rate":         round(d["wins"] / w_l * 100, 1) if w_l > 0 else None,
            "invested":         round(d["invested"], 2),
            "pnl":              round(d["pnl"], 2),
            "unrealized_pnl":   round(d["unrealized_pnl"], 2),
            "low_sample":       d["trades"] < LOW_SAMPLE_THRESHOLD,
        }
    return result


def compute_by_timeframe(wallet_address: str, since_days: int = 30) -> dict[str, dict]:
    wallet = wallet_address.lower()
    trades = [t for t in _load_archive(since_days)
              if (t.get("source_wallet") or "").lower() == wallet]
    portfolio_pnl = _load_portfolio_pnl()

    by_tf: dict[str, dict] = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0, "pending": 0,
        "invested": 0.0, "pnl": 0.0, "unrealized_pnl": 0.0,
    })

    for t in trades:
        mid      = (t.get("market_id") or "").lower()
        port     = portfolio_pnl.get(mid)
        label    = port.get("closes_in_label", "") if port else ""
        tf       = _timeframe_bucket(label)
        invested = float(t.get("einsatz_usdc") or 0)
        ergebnis = (t.get("ergebnis") or "").upper()

        by_tf[tf]["trades"]   += 1
        by_tf[tf]["invested"] += invested

        if ergebnis == "GEWINN":
            by_tf[tf]["wins"] += 1
            by_tf[tf]["pnl"]  += float(t.get("gewinn_verlust_usdc") or 0)
        elif ergebnis == "VERLUST":
            by_tf[tf]["losses"] += 1
            by_tf[tf]["pnl"]    += float(t.get("gewinn_verlust_usdc") or 0)
        else:
            by_tf[tf]["pending"] += 1
            if port:
                by_tf[tf]["unrealized_pnl"] += float(port.get("pnl_usdc") or 0)

    result = {}
    order  = ["same_day", "short", "medium", "long", "unknown"]
    for tf in order:
        if tf not in by_tf:
            continue
        d   = by_tf[tf]
        w_l = d["wins"] + d["losses"]
        result[tf] = {
            "trades":         d["trades"],
            "wins":           d["wins"],
            "losses":         d["losses"],
            "pending":        d["pending"],
            "hit_rate":       round(d["wins"] / w_l * 100, 1) if w_l > 0 else None,
            "invested":       round(d["invested"], 2),
            "pnl":            round(d["pnl"], 2),
            "unrealized_pnl": round(d["unrealized_pnl"], 2),
            "low_sample":     d["trades"] < LOW_SAMPLE_THRESHOLD,
        }
    return result


def compute_all_wallets(since_days: int = 30) -> list[dict]:
    trades_all = _load_archive(since_days)
    seen_wallets = {(t.get("source_wallet") or "").lower() for t in trades_all if t.get("source_wallet")}
    # Include all configured wallets even if 0 trades
    all_wallets = seen_wallets | {w.lower() for w in WALLET_NAMES}

    results = []
    for wallet in all_wallets:
        # Find original-case address
        original = next((w for w in WALLET_NAMES if w.lower() == wallet), wallet)
        stats = compute_wallet_stats(original, since_days)
        results.append(stats)

    # Sort by: trades_count desc, then unrealized_pnl desc
    results.sort(key=lambda x: (x["trades_count"], x["unrealized_pnl_usdc"]), reverse=True)
    return results
