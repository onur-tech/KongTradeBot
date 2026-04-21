#!/usr/bin/env python3
"""
auto_sigma_recalibrate.py — Automatische Sigma-Nachkalibrierung.

Liest:  data/daily_datapoints/*.json  (Forecast-Snapshots)
        data/polymarket_stations.json  (aktuelle Sigma-Werte)
        trades_archive.json            (aufgelöste Weather-Trades)
Berechnet empirisches Sigma aus |forecast - actual| pro Stadt + Monat.
Output: data/analysis/sigma_recalibration_DATUM.json + Diff-Tabelle
WICHTIG: Nur Vorschläge — keine automatische Anwendung.
"""

import json
import os
import glob
import math
from datetime import date, datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ANALYSIS_DIR = os.path.join(DATA_DIR, "analysis")
DATAPOINTS_DIR = os.path.join(DATA_DIR, "daily_datapoints")
STATIONS_FILE = os.path.join(DATA_DIR, "polymarket_stations.json")
ARCHIVE_FILE = os.path.join(BASE_DIR, "trades_archive.json")
CHANGE_THRESHOLD = 0.3  # Sigma-Abweichung ab der ein Update vorgeschlagen wird


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_question_threshold(question: str):
    """Extrahiert Schwellenwert und Richtung aus Markt-Frage."""
    import re
    q = question.lower()

    # "be X°C or below" → direction=below, threshold=X
    m = re.search(r'be\s+([\d.]+)\s*°[cf]\s+or\s+below', q)
    if m:
        return float(m.group(1)), "below"
    # "be X°C or above" → direction=above, threshold=X
    m = re.search(r'be\s+([\d.]+)\s*°[cf]\s+or\s+above', q)
    if m:
        return float(m.group(1)), "above"
    # "be exactly X°C"
    m = re.search(r'be\s+([\d.]+)\s*°[cf]', q)
    if m:
        return float(m.group(1)), "exact"
    return None, None


def analyze():
    stations = load_json(STATIONS_FILE) or {}
    archive = load_json(ARCHIVE_FILE) or []
    dp_files = sorted(glob.glob(os.path.join(DATAPOINTS_DIR, "dp_*.json")))

    print(f"Datapoints verfügbar: {len(dp_files)} Tage")
    print(f"Stations geladen: {len(stations)} Städte")
    weather_closed = [
        t for t in archive
        if t.get("aufgeloest")
        and "temperature" in (t.get("markt") or "").lower()
    ]
    print(f"Aufgelöste Weather-Trades: {len(weather_closed)}")

    # Forecast-Fehler sammeln: pro Stadt pro Monat (forecast - actual)
    errors: dict = defaultdict(list)  # key = (city, month_str)

    for dp_path in dp_files:
        dp = load_json(dp_path)
        if not dp:
            continue
        dp_date_str = dp.get("date", "")
        forecasts = dp.get("forecasts", {})
        markets = dp.get("markets", {})

        for market_id, mkt in markets.items():
            city = mkt.get("city", "")
            question = mkt.get("question", "")
            end_date_str = (mkt.get("end_date") or "")[:10]
            if not city or not end_date_str:
                continue

            threshold, direction = parse_question_threshold(question)
            if threshold is None:
                continue

            # Forecast zum Zeitpunkt des Snapshots
            city_fc = forecasts.get(city, {})
            dates = city_fc.get("dates", [])
            temps = [city_fc.get("today"), city_fc.get("tomorrow"), city_fc.get("d2")]

            forecast_temp = None
            for i, d in enumerate(dates):
                if d == end_date_str and i < len(temps):
                    forecast_temp = temps[i]
                    break

            if forecast_temp is None:
                continue

            # Aufgelöste Trades für diesen Markt finden
            resolved = [
                t for t in weather_closed
                if t.get("market_id") == market_id
            ]
            if not resolved:
                continue

            # Ergebnis → actual temperature ableiten
            for rt in resolved:
                outcome = rt.get("outcome", "").upper()
                ergebnis = rt.get("ergebnis", "")

                # YES gewonnen: Bedingung war wahr
                if ergebnis == "GEWINN" and outcome == "YES":
                    actual = threshold  # mindestens threshold
                elif ergebnis == "VERLUST" and outcome == "YES":
                    actual = threshold - 1.0  # war unter threshold (approx)
                else:
                    continue

                error = abs(forecast_temp - actual)
                try:
                    month = end_date_str[5:7]
                    errors[(city, month)].append(error)
                except Exception:
                    pass

    # Sigma-Vergleich
    proposals = []
    for city, station in stations.items():
        current_sigma = station.get("sigma", 2.0)
        sigma_by_month = station.get("sigma_by_month", {})
        current_month = str(date.today().month)
        current_month_sigma = sigma_by_month.get(current_month, current_sigma)

        city_errors = errors.get((city, current_month), [])
        if len(city_errors) < 3:
            # Nicht genug Datenpunkte für diesen Monat
            proposals.append({
                "city": city,
                "current_sigma": current_sigma,
                "current_month_sigma": current_month_sigma,
                "empirical_sigma": None,
                "sample_size": len(city_errors),
                "delta": None,
                "update_recommended": False,
                "reason": f"Zu wenig Datenpunkte ({len(city_errors)}/3 min)",
            })
            continue

        # Empirisches Sigma = Standardabweichung der Fehler
        n = len(city_errors)
        mean_err = sum(city_errors) / n
        variance = sum((e - mean_err) ** 2 for e in city_errors) / (n - 1) if n > 1 else 0
        emp_sigma = math.sqrt(variance) if variance > 0 else mean_err

        delta = emp_sigma - current_month_sigma
        update = abs(delta) > CHANGE_THRESHOLD

        proposals.append({
            "city": city,
            "month": current_month,
            "current_sigma": current_sigma,
            "current_month_sigma": current_month_sigma,
            "empirical_sigma": round(emp_sigma, 3),
            "sample_size": n,
            "delta": round(delta, 3),
            "update_recommended": update,
            "reason": f"Δ={delta:+.2f} ({'> ' if abs(delta)>CHANGE_THRESHOLD else '<= '}{CHANGE_THRESHOLD} Schwelle)" if update else "Kein Update nötig",
        })

    # Stdout-Tabelle
    print(f"\nSigma-Kalibrierungs-Analyse — Monat {current_month}/2026")
    print(f"Schwelle für Update-Vorschlag: ±{CHANGE_THRESHOLD}")
    print()
    updates_needed = [p for p in proposals if p.get("update_recommended")]
    no_data = [p for p in proposals if p.get("empirical_sigma") is None]
    no_update = [p for p in proposals if not p.get("update_recommended") and p.get("empirical_sigma") is not None]

    if updates_needed:
        print("UPDATE EMPFOHLEN:")
        print(f"{'Stadt':<18} {'Aktuell':>9} {'Empirisch':>10} {'Delta':>7} {'N':>4}  Aktion")
        print("─" * 65)
        for p in sorted(updates_needed, key=lambda x: abs(x["delta"]), reverse=True):
            cur = p["current_month_sigma"]
            emp = p["empirical_sigma"]
            d = p["delta"]
            arrow = "↑" if d > 0 else "↓"
            print(f"{p['city']:<18} {cur:>9.3f} {emp:>10.3f} {d:>+7.3f} {p['sample_size']:>4}  "
                  f"{arrow} {cur:.2f} → {emp:.2f}")
        print()
    else:
        print("Keine Updates empfohlen (alle Städte innerhalb Schwelle oder Datenmangel).\n")

    print(f"Status: {len(updates_needed)} Updates | {len(no_update)} OK | {len(no_data)} zu wenig Daten")
    print(f"\nHINWEIS: Zum Anwenden → python3 scripts/apply_calibration.py")

    # JSON speichern
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    out_path = os.path.join(ANALYSIS_DIR, f"sigma_recalibration_{date.today().isoformat()}.json")
    output = {
        "date": date.today().isoformat(),
        "month_analyzed": current_month,
        "change_threshold": CHANGE_THRESHOLD,
        "datapoints_files": len(dp_files),
        "weather_closed_trades": len(weather_closed),
        "summary": {
            "updates_recommended": len(updates_needed),
            "within_threshold": len(no_update),
            "insufficient_data": len(no_data),
        },
        "proposals": proposals,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"→ Gespeichert: {out_path}")
    return output


if __name__ == "__main__":
    analyze()
