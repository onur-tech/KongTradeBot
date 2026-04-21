"""
apply_calibration.py
====================
Übernimmt kalibrierte Sigma-Werte von Windows CC in das Server-Repo.

Workflow:
  Windows CC führt calc_station_sigma.py aus und speichert das Ergebnis
  als data/polymarket_stations_new.json (z.B. via SCP oder git push).
  Dieses Script validiert und übernimmt die Werte.

Verwendung:
  python3 scripts/apply_calibration.py [--dry-run]

Flags:
  --dry-run   Zeigt nur was geändert würde, schreibt nichts.
"""

import json
import re
import sys
from pathlib import Path

BASE        = Path(__file__).parent.parent
NEW_FILE    = BASE / "data" / "polymarket_stations_new.json"
TARGET_FILE = BASE / "data" / "polymarket_stations.json"
SCOUT_FILE  = BASE / "core" / "weather_scout.py"

DRY_RUN = "--dry-run" in sys.argv

# Seoul April-Bias Sanity-Check-Toleranz
SEOUL_APR_BIAS_EXPECTED = -5.23
SEOUL_APR_BIAS_TOLERANCE = 1.0

# Städte mit sigma_annual >= dieses Limit kommen NICHT in CALIBRATED_CITIES
SIGMA_ANNUAL_LIMIT = 4.0


# ── 1. Neue Kalibrierungsdatei laden ─────────────────────────────────────────

def load_new(path: Path) -> dict:
    if not path.exists():
        print(f"❌ {path} nicht gefunden.")
        print("   Erwarteter Pfad: data/polymarket_stations_new.json")
        print("   Erstelle die Datei mit calc_station_sigma.py auf Windows CC,")
        print("   dann per SCP oder git auf den Server übertragen.")
        sys.exit(1)
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ JSON-Fehler in {path}: {e}")
        sys.exit(1)


# ── 2. Validierung ────────────────────────────────────────────────────────────

def validate(new: dict) -> list[str]:
    errors = []

    for city, data in new.items():
        if not isinstance(data, dict):
            errors.append(f"{city}: Wert ist kein Dict")
            continue

        # sigma_annual muss vorhanden sein
        if "sigma" not in data and "sigma_annual" not in data:
            errors.append(f"{city}: Kein sigma/sigma_annual-Feld")

        # sigma_by_month (12 Werte) — optional aber erwünscht
        monthly = data.get("sigma_by_month") or data.get("sigma_monthly") or {}
        if monthly and len(monthly) < 12:
            errors.append(
                f"{city}: sigma_by_month hat nur {len(monthly)} Monate (erwartet 12)"
            )

    # Seoul April-Bias Sanity Check
    seoul = new.get("Seoul") or new.get("seoul")
    if seoul:
        bias_map = seoul.get("monthly_bias") or seoul.get("bias") or {}
        apr_bias = bias_map.get("04") or bias_map.get(4) or bias_map.get("4")
        if apr_bias is not None:
            diff = abs(float(apr_bias) - SEOUL_APR_BIAS_EXPECTED)
            if diff > SEOUL_APR_BIAS_TOLERANCE:
                errors.append(
                    f"Seoul April-Bias Sanity-Check FAIL: "
                    f"erwartet ~{SEOUL_APR_BIAS_EXPECTED}°C, "
                    f"gefunden {apr_bias}°C (Δ={diff:.2f}°C > ±{SEOUL_APR_BIAS_TOLERANCE}°C)"
                )
            else:
                print(f"✅ Seoul April-Bias OK: {apr_bias}°C (erwartet ~{SEOUL_APR_BIAS_EXPECTED}°C)")
        else:
            print(f"⚠️  Seoul April-Bias nicht in neuen Daten — Sanity-Check übersprungen")
    else:
        print(f"⚠️  Seoul nicht in neuen Daten — Sanity-Check übersprungen")

    return errors


# ── 3. Merge in target stations.json ─────────────────────────────────────────

def merge(new: dict, target: dict) -> tuple[dict, list[str]]:
    """Übernimmt sigma + empirische Felder aus new in target. Gibt (merged, changed_cities)."""
    changed = []
    merged = {k: v for k, v in target.items()}  # Kopie

    for city, ndata in new.items():
        old_sigma = merged.get(city, {}).get("sigma", 1.8) if city in merged else None
        new_sigma = ndata.get("sigma") or ndata.get("sigma_annual")
        if new_sigma is None:
            continue

        if city not in merged:
            merged[city] = {}

        merged[city]["sigma"] = new_sigma
        if "sigma_raw" in ndata or "sigma_empirical" in ndata:
            merged[city]["sigma_empirical"] = ndata.get("sigma_raw") or ndata.get("sigma_empirical")
        if "mae" in ndata or "sigma_mae" in ndata:
            merged[city]["sigma_mae"] = ndata.get("mae") or ndata.get("sigma_mae")
        if "sigma_by_month" in ndata:
            merged[city]["sigma_by_month"] = ndata["sigma_by_month"]

        delta = abs(float(new_sigma) - float(old_sigma)) if old_sigma else 9999
        if delta > 0.05:
            changed.append((city, old_sigma, new_sigma))

    return merged, changed


# ── 4. CALIBRATED_CITIES in weather_scout.py aktualisieren ───────────────────

def update_calibrated_cities(new: dict, scout_path: Path, dry_run: bool):
    """
    Erweitert CALIBRATED_CITIES um alle Städte mit sigma_annual < SIGMA_ANNUAL_LIMIT,
    sofern sie noch nicht in der Liste stehen.
    """
    src = scout_path.read_text()

    # Aktuelle Liste parsen
    m = re.search(
        r'CALIBRATED_CITIES\s*=\s*\[(.*?)\]',
        src, re.DOTALL
    )
    if not m:
        print("⚠️  CALIBRATED_CITIES nicht in weather_scout.py gefunden — überspringe")
        return

    current_raw = m.group(1)
    current_cities = set(re.findall(r'"([^"]+)"', current_raw))

    # Neue qualifizierte Städte
    newly_qualified = []
    for city, data in new.items():
        sigma = data.get("sigma") or data.get("sigma_annual")
        if sigma is None:
            continue
        if float(sigma) < SIGMA_ANNUAL_LIMIT and city not in current_cities:
            newly_qualified.append(city)

    if not newly_qualified:
        print("ℹ️  Keine neuen Städte für CALIBRATED_CITIES (alle bereits drin oder σ ≥ Limit)")
        return

    print(f"\nNeu qualifiziert für CALIBRATED_CITIES ({len(newly_qualified)} Städte):")
    for c in sorted(newly_qualified):
        sigma = new[c].get("sigma") or new[c].get("sigma_annual")
        print(f"  + {c} (σ={sigma})")

    if dry_run:
        print("  [DRY-RUN] Keine Änderungen geschrieben")
        return

    # Liste neu aufbauen
    all_cities = sorted(current_cities | set(newly_qualified))
    new_list = ",\n    ".join(f'"{c}"' for c in all_cities)
    new_block = f'CALIBRATED_CITIES = [\n    {new_list}\n]'

    updated = re.sub(
        r'CALIBRATED_CITIES\s*=\s*\[.*?\]',
        new_block,
        src,
        flags=re.DOTALL
    )

    if updated == src:
        print("⚠️  Regex-Ersetzung hat nichts verändert — manuell prüfen")
        return

    scout_path.write_text(updated)
    print(f"✅ CALIBRATED_CITIES aktualisiert: {len(all_cities)} Städte gesamt")


# ── 5. Hauptprogramm ─────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"apply_calibration.py {'[DRY-RUN]' if DRY_RUN else '[LIVE]'}")
    print(f"{'='*60}\n")

    # Laden
    new = load_new(NEW_FILE)
    print(f"Geladen: {len(new)} Städte aus {NEW_FILE.name}")

    # Validieren
    errors = validate(new)
    if errors:
        print(f"\n❌ {len(errors)} Validierungsfehler:")
        for e in errors:
            print(f"   • {e}")
        if not DRY_RUN:
            ans = input("\nTrotzdem fortfahren? [j/N] ").strip().lower()
            if ans != "j":
                print("Abgebrochen.")
                sys.exit(1)
    else:
        print("✅ Validierung OK")

    # Ziel laden
    try:
        target = json.loads(TARGET_FILE.read_text())
    except Exception:
        target = {}
    print(f"Ziel: {len(target)} Städte in {TARGET_FILE.name}")

    # Merge
    merged, changed = merge(new, target)

    print(f"\nGeänderte Sigma-Werte ({len(changed)}):")
    if changed:
        for city, old, new_s in sorted(changed):
            arrow = "▲" if new_s > old else "▼"
            print(f"  {city:18} {old} → {new_s} {arrow}")
    else:
        print("  (keine Änderungen)")

    if not DRY_RUN:
        TARGET_FILE.write_text(json.dumps(merged, indent=2))
        print(f"\n✅ {TARGET_FILE.name} geschrieben ({len(merged)} Städte)")
    else:
        print(f"\n[DRY-RUN] {TARGET_FILE.name} nicht verändert")

    # CALIBRATED_CITIES updaten
    print(f"\nPrüfe CALIBRATED_CITIES (σ < {SIGMA_ANNUAL_LIMIT})...")
    update_calibrated_cities(new, SCOUT_FILE, DRY_RUN)

    print(f"\n{'='*60}")
    print(f"Fertig.{' (DRY-RUN — keine Änderungen geschrieben)' if DRY_RUN else ''}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
