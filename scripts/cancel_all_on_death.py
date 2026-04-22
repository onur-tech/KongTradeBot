"""
Dead-Man-Switch Emergency Stop Webhook (Phase 2.6)

Separate process from the main bot.
Listens on 127.0.0.1:8888 for POST /emergency-stop from Healthchecks.io.

On valid webhook:
  1. cancel_all() open orders via CLOB (3× retry with backoff)
  2. Telegram critical alert (timestamp + reason)
  3. data/bot_status.json → EMERGENCY_STOPPED
  4. Create bot.lock so main bot does not auto-restart

Security: X-Healthchecks-Secret header must match HEALTHCHECKS_WEBHOOK_SECRET.

Nginx proxies kong-trade.com/emergency-stop → 127.0.0.1:8888/emergency-stop
so Healthchecks.io can reach this from the public internet.
"""
import os
import sys
import json
import time
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE         = Path(__file__).parent.parent
BOT_STATUS    = _BASE / "data" / "bot_status.json"
BOT_LOCK      = _BASE / "bot.lock"

# ── Config from .env ──────────────────────────────────────────────────────────
WEBHOOK_SECRET  = os.getenv("HEALTHCHECKS_WEBHOOK_SECRET", "")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT   = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")[0].strip()
PRIVATE_KEY     = os.getenv("PRIVATE_KEY", "")
POLY_ADDRESS    = os.getenv("POLYMARKET_ADDRESS", "")
CLOB_HOST       = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
CHAIN_ID        = int(os.getenv("CHAIN_ID", "137"))
SIG_TYPE        = int(os.getenv("SIGNATURE_TYPE", "1"))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DEADMAN] %(levelname)s %(message)s",
)
log = logging.getLogger("deadman")

app = Flask(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        log.warning("Telegram not configured — skipping alert")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        body = json.dumps({"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        log.error(f"Telegram send failed: {e}")
        return False


def _cancel_all_with_retry(max_retries: int = 3) -> tuple[bool, str]:
    """
    Attempts to cancel all open orders via CLOB client.
    Returns (success, message).
    """
    try:
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds
    except ImportError:
        return False, "py-clob-client not installed"

    if not PRIVATE_KEY or not POLY_ADDRESS:
        return False, "PRIVATE_KEY or POLYMARKET_ADDRESS not set"

    for attempt in range(1, max_retries + 1):
        try:
            client = ClobClient(
                host=CLOB_HOST,
                chain_id=CHAIN_ID,
                key=PRIVATE_KEY,
                signature_type=SIG_TYPE,
                funder=POLY_ADDRESS,
            )
            client.set_api_creds(client.create_or_derive_api_creds())
            result = client.cancel_all()
            canceled = (result or {}).get("canceled", []) if isinstance(result, dict) else []
            log.info(f"cancel_all() attempt {attempt}: canceled {len(canceled)} orders")
            return True, f"Canceled {len(canceled)} open orders"
        except Exception as exc:
            log.warning(f"cancel_all() attempt {attempt}/{max_retries} failed: {exc}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # 2s, 4s backoff

    return False, f"cancel_all() failed after {max_retries} attempts"


def _set_emergency_status(reason: str):
    """Write EMERGENCY_STOPPED status to data/bot_status.json."""
    try:
        BOT_STATUS.parent.mkdir(parents=True, exist_ok=True)
        BOT_STATUS.write_text(json.dumps({
            "status": "EMERGENCY_STOPPED",
            "reason": reason,
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))
    except Exception as e:
        log.error(f"Could not write bot_status.json: {e}")


def _create_lock(reason: str):
    """Create bot.lock to prevent main bot from auto-restarting."""
    try:
        BOT_LOCK.write_text(json.dumps({
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "locked_by": "deadman_switch",
        }))
        log.info(f"Created bot.lock: {reason}")
    except Exception as e:
        log.error(f"Could not create bot.lock: {e}")


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@app.route("/emergency-stop", methods=["POST"])
def emergency_stop():
    # Authenticate
    if WEBHOOK_SECRET:
        provided = request.headers.get("X-Healthchecks-Secret", "")
        if provided != WEBHOOK_SECRET:
            log.warning(f"Rejected /emergency-stop: invalid secret from {request.remote_addr}")
            return jsonify({"error": "unauthorized"}), 401

    reason = request.json.get("reason", "Healthchecks.io — check went down") if request.is_json else "Healthchecks.io — check went down"
    ts = datetime.now(timezone.utc).isoformat()

    log.critical(f"⛔ EMERGENCY STOP triggered: {reason}")

    # 1. Cancel all orders
    cancel_ok, cancel_msg = _cancel_all_with_retry()

    # 2. Set DB / status flag
    _set_emergency_status(reason)

    # 3. Create lock file
    _create_lock(reason)

    # 4. Telegram alert
    if cancel_ok:
        alert = (
            f"🚨 <b>EMERGENCY STOP — Dead-Man-Switch ausgelöst</b>\n"
            f"Zeit: <code>{ts}</code>\n"
            f"Grund: {reason}\n"
            f"Orders: {cancel_msg}\n"
            f"Status: EMERGENCY_STOPPED gesetzt\n"
            f"Bot.lock erstellt — Auto-Restart deaktiviert\n"
            f"Manueller Unlock: <code>python3 scripts/unlock_emergency.py</code>"
        )
    else:
        alert = (
            f"🚨🚨 <b>EMERGENCY STOP — MANUAL INTERVENTION REQUIRED</b>\n"
            f"Zeit: <code>{ts}</code>\n"
            f"Grund: {reason}\n"
            f"⚠️ cancel_all() FEHLGESCHLAGEN: {cancel_msg}\n"
            f"❗ OFFENE ORDERS MÜSSEN MANUELL GECANCELT WERDEN!\n"
            f"Polymarket: https://polymarket.com/portfolio"
        )
    _telegram(alert)

    return jsonify({
        "status": "EMERGENCY_STOPPED",
        "cancel_ok": cancel_ok,
        "cancel_msg": cancel_msg,
        "timestamp": ts,
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "kongtrade-deadman"}), 200


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not WEBHOOK_SECRET:
        log.warning("⚠️  HEALTHCHECKS_WEBHOOK_SECRET not set — webhook is UNAUTHENTICATED")

    log.info("Dead-Man-Switch listening on 127.0.0.1:8888")
    app.run(host="127.0.0.1", port=8888, debug=False)
