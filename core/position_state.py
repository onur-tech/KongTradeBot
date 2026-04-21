"""
core/position_state.py — T-M08 Phase 1: Position State Machine

States:
  OPEN           — Position gehalten, Markt läuft noch
  PENDING_CLOSE  — Markt aufgelöst, Shares noch nicht geclaimed
  RESOLVED       — Position geschlossen (Sell oder Claim)
  EXPIRED        — Markt abgelaufen, Position nie aufgelöst (abschreiben)
  RESOLVED_LOST  — Markt aufgelöst, Position wertlos (0¢ bestätigt)

Absichtlich als str-Enum damit JSON-Serialisierung ohne Konvertierung funktioniert.
"""
from enum import Enum


class PositionState(str, Enum):
    OPEN          = "OPEN"
    PENDING_CLOSE = "PENDING_CLOSE"
    RESOLVED      = "RESOLVED"
    EXPIRED       = "EXPIRED"
    RESOLVED_LOST = "RESOLVED_LOST"
