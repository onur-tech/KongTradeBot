"""
utils/slippage_analyzer.py — Slippage-Statistiken aus slippage_log.jsonl
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional
from utils.slippage_tracker import load_entries, ALERT_THRESHOLD_CENTS


def _stats(values: list) -> dict:
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "max": 0.0, "min": 0.0, "total": 0.0}
    s = sorted(values)
    n = len(s)
    mid = n // 2
    median = (s[mid - 1] + s[mid]) / 2 if n % 2 == 0 else s[mid]
    total = sum(s)
    return {
        "count": n,
        "mean":   round(total / n, 3),
        "median": round(median, 3),
        "max":    round(max(s), 3),
        "min":    round(min(s), 3),
        "total":  round(total, 3),
    }


def compute_daily_stats(date_filter: Optional[str] = None) -> dict:
    """
    Aggregiert Slippage pro Tag (YYYY-MM-DD).
    Ohne date_filter: alle verfügbaren Tage.
    Mit date_filter: nur dieser Tag.
    """
    entries = load_entries(date_filter)
    by_day: dict[str, list] = defaultdict(list)
    for e in entries:
        day = e.get("timestamp", "")[:10]
        by_day[day].append(e["delta_cents"])

    result = {}
    for day, vals in sorted(by_day.items()):
        st = _stats(vals)
        st["alert"] = st["mean"] > ALERT_THRESHOLD_CENTS
        result[day] = st
    return result


def compute_weekly_stats(weeks_back: int = 4) -> dict:
    """Aggregiert Slippage pro Kalenderwoche der letzten `weeks_back` Wochen."""
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
    entries = [
        e for e in load_entries()
        if datetime.fromisoformat(e["timestamp"]) >= cutoff
    ]
    by_week: dict[str, list] = defaultdict(list)
    for e in entries:
        ts = datetime.fromisoformat(e["timestamp"])
        week_key = ts.strftime("%Y-W%V")
        by_week[week_key].append(e["delta_cents"])

    result = {}
    for week, vals in sorted(by_week.items()):
        st = _stats(vals)
        st["alert"] = st["mean"] > ALERT_THRESHOLD_CENTS
        result[week] = st
    return result


def compute_by_wallet() -> dict:
    """Slippage gruppiert nach Whale-Wallet."""
    entries = load_entries()
    by_wallet: dict[str, list] = defaultdict(list)
    for e in entries:
        by_wallet[e.get("whale_wallet", "unknown")].append(e["delta_cents"])

    return {w: _stats(vals) for w, vals in sorted(by_wallet.items(), key=lambda x: -len(x[1]))}


def compute_by_market_category() -> dict:
    """Slippage gruppiert nach Markt-Kategorie."""
    entries = load_entries()
    by_cat: dict[str, list] = defaultdict(list)
    for e in entries:
        by_cat[e.get("category", "unknown")].append(e["delta_cents"])

    return {c: _stats(vals) for c, vals in sorted(by_cat.items(), key=lambda x: -len(x[1]))}


def compute_by_signal_type() -> dict:
    """
    Slippage nach Signal-Typ:
      - single: is_multi_signal == False
      - multi:  is_multi_signal == True
    """
    entries = load_entries()
    groups: dict[str, list] = {"single": [], "multi": []}
    for e in entries:
        key = "multi" if e.get("is_multi_signal") else "single"
        groups[key].append(e["delta_cents"])

    return {k: _stats(v) for k, v in groups.items()}


def get_today_alert_status() -> dict:
    """Gibt zurück ob der heutige Tages-Mittelwert über dem Alert-Threshold liegt."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily = compute_daily_stats(date_filter=today)
    today_stats = daily.get(today, {"count": 0, "mean": 0.0, "alert": False})
    return {
        "date":      today,
        "mean_cents": today_stats.get("mean", 0.0),
        "count":     today_stats.get("count", 0),
        "alert":     today_stats.get("alert", False),
        "threshold": ALERT_THRESHOLD_CENTS,
    }
