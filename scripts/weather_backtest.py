#!/usr/bin/env python3
"""
Weather Backtest — Wertet DRY-RUN Opportunities aus bot.log aus.
Prüft ob die Forecasts gestimmt hätten und berechnet erwarteten Profit.
"""
import json
import re
from pathlib import Path
from datetime import datetime

LOG   = Path("/root/KongTradeBot/logs/bot.log")
ARCH  = Path("/root/KongTradeBot/trades_archive.json")

# Opportunitäten aus Log parsen
OPP_PATTERN = re.compile(
    r'\[WeatherScout\].*?Opportunity.*?:\s*'
    r'(YES|NO)\s+([\w\s\-]+?)\s+'
    r'Forecast\s+([\d.]+)°([FC])\s+'
    r'Edge\s+(\d+)%',
    re.IGNORECASE
)

# Älteres Format aus analyze_opportunity
OLD_OPP_PATTERN = re.compile(
    r'\[WeatherScout\]\s+.*?(YES|NO)\s+(.+?)\s+@\s+([\d.]+)\s+\(Edge:\s+([\d.]+%)\)',
    re.IGNORECASE
)


def parse_dry_run_opportunities():
    if not LOG.exists():
        print(f"Log nicht gefunden: {LOG}")
        return []
    opps = []
    for line in LOG.read_text(errors="replace").splitlines():
        if "[WeatherScout]" not in line:
            continue

        # Neues v2-Format
        m = OPP_PATTERN.search(line)
        if m:
            opps.append({
                "time":      line[:19],
                "direction": m.group(1).upper(),
                "city":      m.group(2).strip(),
                "forecast":  float(m.group(3)),
                "unit":      m.group(4).upper(),
                "edge":      int(m.group(5)) / 100,
                "raw":       line[20:120].strip(),
            })
            continue

        # Altes Format (→ Roh-Zeile)
        if "Edge" in line and ("→" in line or "YES" in line or "NO" in line):
            opps.append({
                "time": line[:19],
                "direction": None,
                "city": None,
                "forecast": None,
                "unit": None,
                "edge": None,
                "raw": line[20:120].strip(),
            })

    return opps


def load_resolved_markets():
    """Lädt abgeschlossene Trades aus dem Archiv für Auflösungsvergleich."""
    if not ARCH.exists():
        return {}
    try:
        archive = json.loads(ARCH.read_text())
        resolved = {}
        for entry in (archive if isinstance(archive, list) else []):
            cid = entry.get("condition_id", "")
            if cid:
                resolved[cid] = entry.get("result", entry.get("pnl_usd", 0))
        return resolved
    except Exception:
        return {}


def main():
    opps = parse_dry_run_opportunities()
    print(f"\nDRY-RUN Opportunities gefunden: {len(opps)}")

    if not opps:
        print("\nNoch keine WeatherScout-Opportunities im Log.")
        print("Warte auf den nächsten Scout-Lauf (stündlich).")
        print("\nAktive Polymarket Weather-Märkte:")
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from core.weather_scout import get_all_polymarket_weather_markets
            markets = get_all_polymarket_weather_markets()
            print(f"  {len(markets)} Märkte aktiv")
            for m in markets[:10]:
                print(f"  {m['city']:18s} YES={m['yes_price']:.2f} "
                      f"NO={m['no_price']:.2f}  Vol=${m['volume']:.0f}  "
                      f"{m['question'][:55]}")
        except Exception as e:
            print(f"  (Fehler beim Laden: {e})")
        return

    print("\nLetzte 10 Opportunities:")
    for o in opps[-10:]:
        if o['direction']:
            print(f"  {o['time']}  {o['direction']:3s}  "
                  f"{str(o['city']):15s}  "
                  f"Forecast {str(o['forecast'])+'°'+str(o['unit']):10s}  "
                  f"Edge {o['edge']:.0%}")
        else:
            print(f"  {o['time']}  {o['raw'][:80]}")

    # Stats für strukturierte Einträge
    structured = [o for o in opps if o['direction'] is not None]
    if structured:
        yes_count = sum(1 for o in structured if o['direction'] == 'YES')
        no_count  = sum(1 for o in structured if o['direction'] == 'NO')
        avg_edge  = sum(o['edge'] for o in structured) / len(structured)
        cities    = list({o['city'] for o in structured})
        print(f"\nStats:")
        print(f"  Total Opportunities: {len(structured)}")
        print(f"  YES: {yes_count}  |  NO: {no_count}")
        print(f"  Ø Edge: {avg_edge:.1%}")
        print(f"  Städte: {', '.join(cities[:8])}")
        print(f"\nHinweis: Backtest-Auflösung benötigt historische "
              f"Wetterdaten-Verifikation (TODO: OpenMeteo Historical API)")


if __name__ == "__main__":
    main()
