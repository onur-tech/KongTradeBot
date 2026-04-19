"""
core/position_state.py — T-M08 Phase 1: Position State Machine

States:
  OPEN           — Position gehalten, Markt läuft noch
  PENDING_CLOSE  — Markt aufgelöst, Shares noch nicht geclaimed
  RESOLVED       — Position geschlossen (Sell oder Claim)

Absichtlich als str-Enum damit JSON-Serialisierung ohne Konvertierung funktioniert.
"""
from enum import Enum


class PositionState(str, Enum):
    OPEN          = "OPEN"
    PENDING_CLOSE = "PENDING_CLOSE"
    RESOLVED      = "RESOLVED"
