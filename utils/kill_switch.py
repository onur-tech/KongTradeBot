"""
utils/kill_switch.py — Persistenter Kill-Switch

State überlebt Bot-Restarts. Supports:
  - Auto-Reset nach Timer (daily_loss: 24h, consecutive_losses: 12h)
  - Manueller Reset (kein Auto-Reset)
  - History der letzten 10 Events
  - Telegram-Alerts via error_handler.set_telegram_sender()
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kill_switch")

_DEFAULT_STATE = {
    "active": False,
    "triggered_at": None,
    "triggered_by": None,
    "reason": None,
    "auto_reset_at": None,
    "daily_pnl_at_trigger": None,
    "history": [],
}

# Auto-Reset-Zeiten je Trigger-Typ
AUTO_RESET_HOURS = {
    "daily_loss":          24,
    "consecutive_losses":  12,
    "manual":              None,  # Kein Auto-Reset
    "api_error":           6,
}


class KillSwitch:
    """
    Persistenter Kill-Switch — State überlebt Bot-Restarts.

    Verwendung:
        ks = KillSwitch()
        if ks.is_active():
            return  # keine Orders
        ks.trigger("daily_loss_limit", triggered_by="daily_loss")
        ks.reset()
    """

    def __init__(self, state_file: Optional[str] = None):
        if state_file:
            self._file = Path(state_file)
        else:
            self._file = Path(__file__).parent.parent / "data" / "kill_switch_state.json"
        self._state = self._load_state()

    # ── Persistenz ────────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        state = dict(_DEFAULT_STATE)
        state["history"] = []
        if self._file.exists():
            try:
                loaded = json.loads(self._file.read_text(encoding="utf-8"))
                state.update(loaded)
            except Exception as e:
                logger.warning(f"Kill-Switch State konnte nicht geladen werden: {e} — starte mit leerem State")
        return state

    def _save_state(self) -> None:
        try:
            self._file.parent.mkdir(exist_ok=True)
            self._file.write_text(
                json.dumps(self._state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Kill-Switch State konnte nicht gespeichert werden: {e}")

    # ── Core API ──────────────────────────────────────────────────────────────

    def is_active(self) -> bool:
        """Gibt True zurück wenn Kill-Switch aktiv. Prüft Auto-Reset-Timer."""
        if not self._state["active"]:
            return False

        reset_at = self._state.get("auto_reset_at")
        if reset_at:
            try:
                reset_dt = datetime.fromisoformat(reset_at)
                if datetime.utcnow() >= reset_dt:
                    self.reset(reason="auto_reset_expired")
                    return False
            except Exception:
                pass

        return True

    def trigger(
        self,
        reason: str,
        triggered_by: str = "system",
        auto_reset_hours: Optional[int] = None,
        daily_pnl: Optional[float] = None,
    ) -> None:
        """
        Aktiviert den Kill-Switch und persistiert den State.

        triggered_by: "daily_loss" | "consecutive_losses" | "manual" | "api_error"
        auto_reset_hours: Überschreibt AUTO_RESET_HOURS[triggered_by] falls angegeben
        """
        if auto_reset_hours is None:
            auto_reset_hours = AUTO_RESET_HOURS.get(triggered_by)

        now = datetime.utcnow()
        auto_reset_at = None
        if auto_reset_hours:
            auto_reset_at = (now + timedelta(hours=auto_reset_hours)).isoformat()

        history_entry = {
            "event": "triggered",
            "triggered_at": now.isoformat() + "Z",
            "triggered_by": triggered_by,
            "reason": reason,
            "auto_reset_at": auto_reset_at,
            "daily_pnl": daily_pnl,
        }
        history = list(self._state.get("history", []))
        history.append(history_entry)
        if len(history) > 10:
            history = history[-10:]

        self._state.update({
            "active": True,
            "triggered_at": now.isoformat() + "Z",
            "triggered_by": triggered_by,
            "reason": reason,
            "auto_reset_at": auto_reset_at,
            "daily_pnl_at_trigger": daily_pnl,
            "history": history,
        })

        reset_msg = f"Auto-Reset in {auto_reset_hours}h" if auto_reset_hours else "Manueller Reset erforderlich"
        logger.warning(f"🛑 KILL-SWITCH AKTIVIERT [{triggered_by}]: {reason} | {reset_msg}")
        self._save_state()

        # Telegram-Alert via error_handler (falls sender registriert)
        self._send_telegram_async(
            f"🛑 <b>KILL-SWITCH AKTIVIERT</b>\n"
            f"📍 Grund: <code>{reason}</code>\n"
            f"🔑 Typ: <code>{triggered_by}</code>\n"
            f"⏱️ {reset_msg}\n"
            f"📊 PnL bei Trigger: {f'${daily_pnl:+.2f}' if daily_pnl is not None else 'n/a'}"
        )

    def reset(self, reason: str = "manual") -> None:
        """Setzt Kill-Switch zurück und persistiert den State."""
        was_active = self._state["active"]
        prev_triggered_by = self._state.get("triggered_by")

        history_entry = {
            "event": "reset",
            "reset_at": datetime.utcnow().isoformat() + "Z",
            "reset_by": reason,
            "was_triggered_by": prev_triggered_by,
        }
        history = list(self._state.get("history", []))
        history.append(history_entry)
        if len(history) > 10:
            history = history[-10:]

        self._state.update({
            "active": False,
            "triggered_at": None,
            "triggered_by": None,
            "reason": None,
            "auto_reset_at": None,
            "daily_pnl_at_trigger": None,
            "history": history,
        })

        if was_active:
            logger.info(f"✅ Kill-Switch zurückgesetzt: {reason}")
        self._save_state()

        if was_active:
            self._send_telegram_async(
                f"✅ <b>Kill-Switch zurückgesetzt</b>\n"
                f"🔑 Reset-Grund: <code>{reason}</code>"
            )

    def get_state(self) -> dict:
        """Gibt aktuellen State zurück inkl. berechneter Restzeit."""
        state = dict(self._state)
        reset_at = state.get("auto_reset_at")
        if state["active"] and reset_at:
            try:
                reset_dt = datetime.fromisoformat(reset_at)
                remaining_s = (reset_dt - datetime.utcnow()).total_seconds()
                state["auto_reset_in_hours"] = round(max(0, remaining_s) / 3600, 1)
            except Exception:
                state["auto_reset_in_hours"] = None
        else:
            state["auto_reset_in_hours"] = None
        return state

    @property
    def reason(self) -> str:
        return self._state.get("reason") or ""

    # ── Telegram (via error_handler, um Circular Imports zu vermeiden) ─────────

    def _send_telegram_async(self, msg: str) -> None:
        """Sendet Telegram-Alert falls error_handler.set_telegram_sender() gesetzt."""
        try:
            from utils.error_handler import _telegram_send
            if _telegram_send is not None:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_telegram_send(msg))
                except RuntimeError:
                    pass  # Kein laufender Event-Loop (z.B. in Tests)
        except ImportError:
            pass
