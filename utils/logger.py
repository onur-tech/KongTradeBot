"""
logger.py — Strukturiertes Logging

Lektion aus der Community:
- Alles loggen mit Timestamp
- In Datei UND Terminal gleichzeitig
- Dry-Run Trades klar markieren
- Fehler niemals still schlucken
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "polymarket_bot", level: str = "INFO") -> logging.Logger:
    """Erstellt einen strukturierten Logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # Bereits initialisiert
    logger.propagate = False  # Verhindert Duplikate in Root-Logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Terminal Output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Output — Log-Datei pro Tag
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(log_dir / f"bot_{today}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(module: str) -> logging.Logger:
    """Holt Sub-Logger für ein Modul."""
    return logging.getLogger(f"polymarket_bot.{module}")
