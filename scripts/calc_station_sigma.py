"""
calc_station_sigma.py v2.0
==========================
Kalibriert empirische Sigma für alle 30 Städte.

Features:
  - 2 Jahre Archivdaten (archive-api.open-meteo.com / ERA5)
  - Monatliche Sigma: 12 Werte pro Stadt (saisonale Variation)
  - Horizont-Skalierung: sigma_eff = sigma_1d × sqrt(horizon_days)
  - GFS Ensemble Spread als Vergleichs-Sigma
  - METAR Lock: aktueller Temperatur-Check via aviationweather.gov
  - ICAO-Korrekturen: Paris=LFPB, NYC=KLGA, Houston=KIAH
  - Seoul April-Bias Sanity Check (≈ -5.23°C)
  - Output: data/polymarket_stations_new.json
  - Nicht-interaktiv: läuft via nohup, kein input()

Methodik (Lag-1-Autokorrelation):
  σ_1day = stdev(ΔT_daily) / sqrt(2)      # Anderson-Whittle-Approximation
  σ_n    = σ_1day × sqrt(horizon_days)     # Horizont-Skalierung
  σ_annual = stdev(σ_1day über alle Monate)

Laufzeit: ~5-8 Minuten (30 Städte × 3 API-Calls à ~1-2s)

Verwendung:
  nohup python3 scripts/calc_station_sigma.py > logs/sigma_calibration.log 2>&1 &
  tail -f logs/sigma_calibration.log
"""

import json
import math
import time
import sys
from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta
try:
    import requests
except ImportError:
    print("FEHLER: requests nicht installiert — pip install requests")
    sys.exit(1)

# ── Konfiguration ─────────────────────────────────────────────────────────────

BASE        = Path(__file__).parent.parent
DATA        = BASE / "data"
OUTPUT_FILE = DATA / "polymarket_stations_new.json"
STATIONS    = DATA / "polymarket_stations.json"
BIAS_FILE   = DATA / "station_bias.json"

ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
METAR_URL    = "https://aviationweather.gov/api/data/metar"

START_DATE   = (date.today() - timedelta(days=730)).isoformat()  # 2 Jahre
END_DATE     = (date.today() - timedelta(days=1)).isoformat()    # gestern

API_DELAY_S  = 0.6   # Rate-Limit-Puffer zwischen Calls
MIN_DAYS     = 30    # Mindest-Datenpunkte pro Monat für valide Sigma

# ICAO-Korrekturen (überschreiben stations.json wenn falsch)
ICAO_CORRECTIONS = {
    "Paris":    "LFPB",   # Le Bourget (nicht CDG=LFPG)
    "New York": "KLGA",   # LaGuardia  (nicht JFK=KJFK)
    "Houston":  "KIAH",   # Intercontinental
}

# Seoul April-Bias Sanity Check
SEOUL_APR_BIAS_EXPECTED  = -5.23
SEOUL_APR_BIAS_TOLERANCE = 1.2


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def stdev(values):
    n = len(values)
    if n < 2:
        return None
    mu = sum(values) / n
    return math.sqrt(sum((x - mu) ** 2 for x in values) / (n - 1))


def mean(values):
    return sum(values) / len(values) if values else None


def sigma_1d_from_delta(deltas: list) -> float | None:
    """
    Anderson-Whittle: σ_1day = stdev(ΔT) / sqrt(2)
    ΔT = T(d) - T(d-1) = tägliche Temperaturänderung
    """
    s = stdev(deltas)
    return round(s / math.sqrt(2), 3) if s else None


# ── API-Calls ─────────────────────────────────────────────────────────────────

def fetch_archive(lat: float, lon: float) -> dict:
    """Holt 2 Jahre tägliche Maximaltemperaturen von Open-Meteo ERA5."""
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": START_DATE,
        "end_date":   END_DATE,
        "daily":      "temperature_2m_max",
        "timezone":   "UTC",
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()
    times = d["daily"]["time"]
    temps = d["daily"]["temperature_2m_max"]
    return {t: v for t, v in zip(times, temps) if v is not None}


def fetch_ensemble_spread(lat: float, lon: float) -> float | None:
    """
    Holt GFS-Ensemble-Spread (stdev der Ensemblemitglieder) für die nächsten 7 Tage.
    Gibt Median-Spread als GFS-Sigma zurück.
    """
    params = {
        "latitude":  lat,
        "longitude": lon,
        "daily":     "temperature_2m_max",
        "models":    "gfs_seamless",
        "timezone":  "UTC",
    }
    try:
        r = requests.get(ENSEMBLE_URL, params=params, timeout=20)
        if r.status_code != 200:
            return None
        d = r.json()
        # Ensemble API gibt mehrere member-Felder zurück: temperature_2m_max_member01, ...
        members = []
        for key, vals in d.get("daily", {}).items():
            if "temperature_2m_max" in key and "member" in key:
                members.append([v for v in vals if v is not None])
        if len(members) < 4:
            return None
        # Pro Tag: Spread = stdev über alle Member
        n_days = min(len(m) for m in members)
        spreads = []
        for i in range(n_days):
            day_vals = [m[i] for m in members]
            s = stdev(day_vals)
            if s:
                spreads.append(s)
        return round(mean(spreads), 2) if spreads else None
    except Exception:
        return None


def fetch_metar_temp(icao: str) -> float | None:
    """Holt aktuelle METAR-Temperatur von aviationweather.gov."""
    try:
        r = requests.get(
            METAR_URL,
            params={"ids": icao, "format": "json", "taf": "false"},
            timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data:
            return data[0].get("temp")
    except Exception:
        return None


# ── Sigma-Berechnung aus Archivdaten ─────────────────────────────────────────

def compute_sigma(temps: dict) -> dict:
    """
    Berechnet monatliche Sigma aus täglichen Maximaltemperaturen.

    Methode: σ_1d = stdev(ΔT_daily) / sqrt(2) pro Monat
    Jahres-Sigma: Median der Monatswerte (robuster als Mean)
    """
    # ΔT pro Monat sammeln
    by_month = defaultdict(list)
    dates = sorted(temps.keys())
    for i in range(1, len(dates)):
        d0, d1 = dates[i-1], dates[i]
        # Nur konsekutive Tage (kein Gap von >2 Tagen)
        dt0 = date.fromisoformat(d0)
        dt1 = date.fromisoformat(d1)
        if (dt1 - dt0).days > 2:
            continue
        delta = temps[d1] - temps[d0]
        month = int(d1[5:7])
        by_month[month].append(delta)

    monthly_sigma = {}
    for m in range(1, 13):
        deltas = by_month.get(m, [])
        if len(deltas) >= MIN_DAYS:
            s = sigma_1d_from_delta(deltas)
            if s:
                monthly_sigma[m] = s

    if not monthly_sigma:
        return {}

    sigmas = list(monthly_sigma.values())
    sorted_s = sorted(sigmas)
    n = len(sorted_s)
    median_s = sorted_s[n // 2] if n % 2 else (sorted_s[n//2 - 1] + sorted_s[n//2]) / 2

    # Jahres-Sigma: median der Monate, geclippt auf [0.8, 5.0]
    sigma_annual = round(max(0.8, min(5.0, median_s)), 2)

    return {
        "sigma":          sigma_annual,          # Jahres-Sigma (für Bucket-Modell)
        "sigma_by_month": {m: v for m, v in monthly_sigma.items()},
        "n_days":         len(dates),
        "n_months":       len(monthly_sigma),
    }


# ── Haupt-Pipeline ────────────────────────────────────────────────────────────

def main():
    log(f"calc_station_sigma.py v2.0 — Start")
    log(f"Zeitraum: {START_DATE} → {END_DATE} ({(date.fromisoformat(END_DATE)-date.fromisoformat(START_DATE)).days} Tage)")
    log(f"Output: {OUTPUT_FILE}")
    log("")

    # Stationen und Bias laden
    stations = json.loads(STATIONS.read_text())
    try:
        bias_data = json.loads(BIAS_FILE.read_text())
    except Exception:
        bias_data = {}
        log("WARNUNG: station_bias.json nicht gefunden — Seoul-Bias-Check übersprungen")

    # ICAO-Korrekturen anwenden
    corrected_icaos = []
    for city, new_icao in ICAO_CORRECTIONS.items():
        if city in stations:
            old_icao = stations[city].get("icao", "?")
            if old_icao != new_icao:
                stations[city]["icao"] = new_icao
                corrected_icaos.append(f"{city}: {old_icao} → {new_icao}")

    if corrected_icaos:
        log(f"ICAO-Korrekturen ({len(corrected_icaos)}):")
        for c in corrected_icaos:
            log(f"  ✓ {c}")
        log("")

    # Seoul April-Bias Sanity Check
    seoul_bias = bias_data.get("Seoul", {}).get("monthly_bias", {})
    apr_bias = seoul_bias.get("04") or seoul_bias.get(4) or seoul_bias.get("4")
    if apr_bias is not None:
        diff = abs(float(apr_bias) - SEOUL_APR_BIAS_EXPECTED)
        if diff <= SEOUL_APR_BIAS_TOLERANCE:
            log(f"✅ Seoul April-Bias OK: {apr_bias}°C (erwartet ~{SEOUL_APR_BIAS_EXPECTED}°C)")
        else:
            log(f"⚠️  Seoul April-Bias ABWEICHUNG: {apr_bias}°C ≠ {SEOUL_APR_BIAS_EXPECTED}°C (Δ={diff:.2f}°C)")
    else:
        log(f"⚠️  Seoul April-Bias nicht verfügbar — manuell prüfen")
    log("")

    # Verarbeitung pro Stadt
    results = {}
    cities = list(stations.keys())
    total = len(cities)

    for i, city in enumerate(cities, 1):
        sd = stations[city]
        lat = sd.get("lat")
        lon = sd.get("lon")
        icao = sd.get("icao", "")

        if not lat or not lon:
            log(f"[{i:02d}/{total}] {city}: SKIP — keine Koordinaten")
            results[city] = {**sd, "sigma": sd.get("sigma", 1.8), "note": "no coordinates"}
            continue

        log(f"[{i:02d}/{total}] {city} ({lat:.2f},{lon:.2f}) icao={icao}")

        # 1. Archivdaten holen
        try:
            temps = fetch_archive(lat, lon)
            log(f"          Archive: {len(temps)} Tage geladen")
        except Exception as e:
            log(f"          Archive FEHLER: {e} — behalte alten Sigma {sd.get('sigma', 1.8)}")
            results[city] = {**sd}
            time.sleep(API_DELAY_S)
            continue

        time.sleep(API_DELAY_S)

        # 2. Sigma berechnen
        sigma_info = compute_sigma(temps)
        if not sigma_info:
            log(f"          WARNUNG: Zu wenig Daten für Sigma-Berechnung")
            results[city] = {**sd}
            continue

        # 3. GFS Ensemble Spread
        try:
            gfs_spread = fetch_ensemble_spread(lat, lon)
            if gfs_spread:
                log(f"          GFS Ensemble Spread: σ={gfs_spread:.2f}°C")
        except Exception:
            gfs_spread = None
        time.sleep(API_DELAY_S)

        # 4. METAR Lock — aktuelle Temperatur
        metar_temp = None
        if icao:
            try:
                metar_temp = fetch_metar_temp(icao)
                if metar_temp is not None:
                    log(f"          METAR {icao}: aktuell {metar_temp:.1f}°C")
            except Exception:
                pass
            time.sleep(0.3)

        # 5. Ergebnis zusammenführen
        new_sigma = sigma_info["sigma"]
        old_sigma = sd.get("sigma", 1.8)
        delta = new_sigma - old_sigma
        flag = " ▲" if delta > 0.2 else (" ▼" if delta < -0.2 else "  ")

        monthly = sigma_info.get("sigma_by_month", {})
        monthly_str = "  ".join(f"M{m}={v}" for m, v in sorted(monthly.items()))

        log(f"          σ: {old_sigma:.2f} → {new_sigma:.2f}{flag}  "
            f"({len(monthly)}/12 Monate)  n={sigma_info['n_days']}d")
        log(f"          Monatlich: {monthly_str}")

        entry = {**sd}
        entry["sigma"]          = new_sigma
        entry["sigma_by_month"] = monthly
        entry["n_days_archive"] = sigma_info["n_days"]
        if gfs_spread:
            entry["sigma_gfs_spread"] = gfs_spread
        if metar_temp is not None:
            entry["metar_temp_now"] = metar_temp

        results[city] = entry
        log("")

    # ── Output ──────────────────────────────────────────────────
    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    log("=" * 65)
    log(f"✅ Fertig — {len(results)} Städte → {OUTPUT_FILE}")
    log("")

    # Zusammenfassung
    log("SIGMA-VERGLEICH (σ_alt → σ_neu):")
    log(f"{'Stadt':18} {'σ_alt':>6} {'σ_neu':>6} {'Δ':>6}  Monatlich")
    log("-" * 65)
    changed = []
    for city, r in sorted(results.items(), key=lambda x: -x[1].get("sigma", 0)):
        old = stations.get(city, {}).get("sigma", 1.8)
        new = r.get("sigma", old)
        delta = new - old
        monthly = r.get("sigma_by_month", {})
        m_str = " ".join(f"M{m}:{v}" for m, v in sorted(monthly.items())) if monthly else "(keine)"
        flag = " ▲" if delta > 0.2 else (" ▼" if delta < -0.2 else "  ")
        log(f"  {city:16} {old:>5.2f}  {new:>5.2f}  {delta:>+5.2f}{flag}  {m_str}")
        if abs(delta) > 0.2:
            changed.append((city, old, new))

    log("")
    log(f"Geänderte Städte ({len(changed)}):")
    for city, old, new in changed:
        log(f"  {city}: {old} → {new}")

    log("")
    log(f"Nächster Schritt:")
    log(f"  python3 scripts/apply_calibration.py --dry-run")
    log(f"  python3 scripts/apply_calibration.py")


if __name__ == "__main__":
    main()
