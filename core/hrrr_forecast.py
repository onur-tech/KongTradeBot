"""
HRRR Forecast für US-Städte
3km Auflösung, stündlich updated, 0-18h Horizont
Überlegen gegenüber GFS/ECMWF für Kurzzeit-US-Forecasts
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# US-Städte die Polymarket auf KLGA/KORD/KDAL etc. auflöst
HRRR_US_CITIES = {
    "New York City": {"lat": 40.7769, "lon": -73.8740, "icao": "KLGA"},
    "Chicago":       {"lat": 41.9742, "lon": -87.9073, "icao": "KORD"},
    "Dallas":        {"lat": 32.8481, "lon": -97.0403, "icao": "KDFW"},
    "Miami":         {"lat": 25.7959, "lon": -80.2870, "icao": "KMIA"},
    "Los Angeles":   {"lat": 33.9425, "lon": -118.4081,"icao": "KLAX"},
    "Seattle":       {"lat": 47.4502, "lon": -122.3088,"icao": "KSEA"},
    "Atlanta":       {"lat": 33.6407, "lon": -84.4277, "icao": "KATL"},
    "Houston":       {"lat": 29.9844, "lon": -95.3414, "icao": "KIAH"},
}

def get_hrrr_max_temp(city: str,
                       forecast_hours: int = 12) -> Optional[float]:
    """
    Holt HRRR 2m-Temperatur für eine US-Stadt.
    Gibt vorhergesagtes Tagesmaximum zurück (°F für US-Märkte).

    Args:
        city: Stadtname (muss in HRRR_US_CITIES sein)
        forecast_hours: Wie viele Stunden voraus (0-18)

    Returns:
        Maximale Temperatur in °F oder None bei Fehler
    """
    if city not in HRRR_US_CITIES:
        logger.debug(f"[HRRR] {city} nicht in US-Liste")
        return None

    coords = HRRR_US_CITIES[city]

    try:
        from herbie import Herbie
        import numpy as np

        now = datetime.now(timezone.utc)
        run_time = now.replace(minute=0, second=0, microsecond=0)

        temps = []
        for fxx in range(0, min(forecast_hours + 1, 19), 1):
            try:
                H = Herbie(
                    run_time.strftime("%Y-%m-%d %H:%M"),
                    model="hrrr",
                    product="sfc",
                    fxx=fxx,
                    verbose=False
                )
                ds = H.xarray("TMP:2 m", remove_grib=True)

                lat_idx = int(np.argmin(
                    np.abs(ds.latitude.values - coords["lat"])
                ))
                lon_idx = int(np.argmin(
                    np.abs(ds.longitude.values - coords["lon"])
                ))

                temp_k = float(ds["t2m"].values.flat[
                    lat_idx * ds.longitude.shape[1] + lon_idx
                ])
                temp_f = (temp_k - 273.15) * 9/5 + 32
                temps.append(temp_f)

            except Exception as e:
                logger.debug(f"[HRRR] fxx={fxx} Fehler: {e}")
                continue

        if not temps:
            return None

        max_temp = max(temps)
        logger.info(
            f"[HRRR] {city}: Max {max_temp:.1f}°F "
            f"aus {len(temps)} Stunden"
        )
        return max_temp

    except Exception as e:
        logger.error(f"[HRRR] Fehler für {city}: {e}")
        return None


def hrrr_vs_openmeteo_consensus(
        city: str,
        openmeteo_forecast: float,
        threshold: float,
        unit: str = "F") -> dict:
    """
    Vergleicht HRRR mit Open-Meteo Forecast.
    Gibt Konsens-Einschätzung zurück.

    Returns:
        {
          "hrrr": float,
          "openmeteo": float,
          "consensus": bool,    # beide auf gleicher Seite?
          "delta": float,       # Differenz HRRR vs OpenMeteo
          "use_hrrr": bool      # HRRR verfügbar?
        }
    """
    hrrr_temp = get_hrrr_max_temp(city)

    result = {
        "hrrr": hrrr_temp,
        "openmeteo": openmeteo_forecast,
        "threshold": threshold,
        "unit": unit,
        "use_hrrr": hrrr_temp is not None,
        "consensus": False,
        "delta": None
    }

    if hrrr_temp is None:
        result["consensus"] = True  # Nur OpenMeteo → kein Gate
        return result

    result["delta"] = abs(hrrr_temp - openmeteo_forecast)

    hrrr_above = hrrr_temp >= threshold
    om_above = openmeteo_forecast >= threshold
    result["consensus"] = (hrrr_above == om_above)

    if not result["consensus"]:
        logger.info(
            f"[HRRR] KEIN KONSENS für {city}: "
            f"HRRR={hrrr_temp:.1f} vs OM={openmeteo_forecast:.1f} "
            f"Threshold={threshold} → Trade SKIP"
        )

    return result
