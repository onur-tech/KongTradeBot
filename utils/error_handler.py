"""
utils/error_handler.py — Zentrale Fehler-Behandlung

Keine Silent-Fails mehr: jeder Fehler wird geloggt, in
data/error_log.jsonl archiviert, und bei severity >= WARNING
als Telegram-Alert gesendet (rate-limited: 1 pro error_type pro Stunde).
"""
import json
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("error_handler")

_SEVERITY_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
_RATE_LIMIT_SECONDS = 3600  # 1h zwischen gleichartigen Alerts
_error_rate_limit: dict[str, float] = {}

DATA_DIR   = Path(__file__).parent.parent / "data"
ERROR_LOG  = DATA_DIR / "error_log.jsonl"
ERROR_STATS = DATA_DIR / "error_stats.json"

_telegram_send = None


def set_telegram_sender(fn) -> None:
    """Registriert die send()-Funktion aus telegram_bot.py."""
    global _telegram_send
    _telegram_send = fn


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def _write_to_log(entry: dict) -> None:
    _ensure_data_dir()
    try:
        with ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _update_stats(error_type: str, severity: str) -> None:
    _ensure_data_dir()
    try:
        stats: dict = {}
        if ERROR_STATS.exists():
            stats = json.loads(ERROR_STATS.read_text(encoding="utf-8"))
        key = f"{severity}:{error_type}"
        stats[key] = stats.get(key, 0) + 1
        stats["_total"] = stats.get("_total", 0) + 1
        stats["_last_updated"] = datetime.utcnow().isoformat() + "Z"
        ERROR_STATS.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


async def handle_error(
    error: Exception,
    context: str,
    severity: str = "WARNING",
    telegram_alert: bool = True,
    reraise: bool = False,
) -> None:
    """
    Zentrale Fehler-Behandlung.

    severity: DEBUG | INFO | WARNING | ERROR | CRITICAL
    telegram_alert: Sendet Telegram-Alert bei severity >= WARNING (rate-limited)
    reraise: Nach Handling Exception weiterreichen
    """
    etype = type(error).__name__
    msg = str(error)
    tb = traceback.format_exc()
    now = datetime.utcnow()

    # 1. Log mit full traceback
    log_fn = getattr(logger, severity.lower(), logger.error)
    log_fn(f"[{context}] {etype}: {msg}", exc_info=True)

    # 2. Archivieren
    entry = {
        "timestamp": now.isoformat() + "Z",
        "context": context,
        "error_type": etype,
        "error_message": msg,
        "stack_trace": tb,
        "severity": severity,
    }
    _write_to_log(entry)

    # 3. Statistiken aktualisieren
    _update_stats(etype, severity)

    # 4. Telegram-Alert (rate-limited)
    if (
        telegram_alert
        and _telegram_send is not None
        and _SEVERITY_ORDER.get(severity, 0) >= _SEVERITY_ORDER["WARNING"]
    ):
        last = _error_rate_limit.get(etype, 0)
        if time.time() - last >= _RATE_LIMIT_SECONDS:
            _error_rate_limit[etype] = time.time()
            sev_emoji = {"WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🚨"}.get(severity, "⚠️")
            try:
                await _telegram_send(
                    f"{sev_emoji} <b>{severity}: {etype}</b>\n"
                    f"📍 <code>{context[:100]}</code>\n"
                    f"💬 <code>{msg[:200]}</code>"
                )
            except Exception:
                pass  # Telegram-Fehler dürfen keine Folgefehler auslösen

    if reraise:
        raise error


def safe_call_transparent(func_name: str, severity_default: str = "WARNING") -> Callable:
    """
    Decorator der Exceptions loggt statt schluckt.

    Verwendung:
        @safe_call_transparent("on_copy_order", severity_default="ERROR")
        async def on_copy_order(order): ...

    Oder nach der Definition:
        on_copy_order = safe_call_transparent("on_copy_order", "ERROR")(on_copy_order)
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                first_arg = repr(args[0])[:60] if args else ""
                await handle_error(
                    error=e,
                    context=f"{func_name}({first_arg})",
                    severity=severity_default,
                    telegram_alert=True,
                    reraise=False,
                )
                return None
        wrapper.__name__ = func.__name__
        wrapper.__doc__  = func.__doc__
        return wrapper
    return decorator
