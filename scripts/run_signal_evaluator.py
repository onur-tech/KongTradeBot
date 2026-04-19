#!/usr/bin/env python3
"""scripts/run_signal_evaluator.py — Taeglich 02:00 UTC via systemd."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from utils.signal_tracker import evaluate_skipped_signals

results = asyncio.run(evaluate_skipped_signals(days_back=30))
print(f"Evaluiert: {len(results)} neue Outcomes")
