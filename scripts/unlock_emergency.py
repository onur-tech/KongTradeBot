"""
Manual Emergency Unlock (Phase 2.6)

Resets EMERGENCY_STOPPED state so the main bot can restart.
CLI-only — intentionally no webhook/API to force human awareness.

Usage:
    python3 scripts/unlock_emergency.py
    python3 scripts/unlock_emergency.py --confirm   # skip interactive prompt
"""
import os
import sys
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

_BASE       = Path(__file__).parent.parent
BOT_STATUS  = _BASE / "data" / "bot_status.json"
BOT_LOCK    = _BASE / "bot.lock"
CB_STATE    = _BASE / "data" / "circuit_breaker.json"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")[0].strip()


def _telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        body = json.dumps({"chat_id": TELEGRAM_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  ⚠️  Telegram send failed: {e}")


def main():
    print("=" * 60)
    print("  KongTrade Emergency Unlock")
    print("=" * 60)

    # Show current status
    if BOT_STATUS.exists():
        try:
            status = json.loads(BOT_STATUS.read_text())
            print(f"\n  Current status: {status.get('status')}")
            print(f"  Stopped at:     {status.get('stopped_at', '?')}")
            print(f"  Reason:         {status.get('reason', '?')}")
        except Exception:
            print("  (could not read bot_status.json)")
    else:
        print("\n  No bot_status.json found — may already be unlocked.")

    if BOT_LOCK.exists():
        print(f"  bot.lock EXISTS")
    else:
        print(f"  bot.lock not present")

    # Confirm
    confirm = "--confirm" in sys.argv
    if not confirm:
        try:
            resp = input("\n  Proceed with unlock? [yes/NO] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Aborted.")
            sys.exit(0)
        if resp != "yes":
            print("  Aborted.")
            sys.exit(0)

    ts = datetime.now(timezone.utc).isoformat()

    # 1. Remove bot.lock
    if BOT_LOCK.exists():
        BOT_LOCK.unlink()
        print("  ✅ bot.lock removed")
    else:
        print("  ℹ️  bot.lock was not present")

    # 2. Reset bot_status.json
    BOT_STATUS.parent.mkdir(parents=True, exist_ok=True)
    BOT_STATUS.write_text(json.dumps({
        "status": "NORMAL",
        "unlocked_at": ts,
        "unlocked_by": "manual_unlock_script",
    }, indent=2))
    print("  ✅ bot_status.json → NORMAL")

    # 3. Reset circuit breaker if at level 3
    if CB_STATE.exists():
        try:
            cb = json.loads(CB_STATE.read_text())
            if cb.get("level", 0) == 3:
                cb["level"] = 0
                cb["reason"] = f"Manual reset at {ts}"
                CB_STATE.write_text(json.dumps(cb, indent=2))
                print("  ✅ circuit_breaker.json Level-3 reset → 0")
        except Exception as e:
            print(f"  ⚠️  Could not reset circuit breaker: {e}")

    # 4. Telegram confirmation
    msg = (
        f"✅ <b>Emergency Unlock — Bot entsperrt</b>\n"
        f"Zeit: <code>{ts}</code>\n"
        f"Entsperrt von: unlock_emergency.py\n"
        f"Bot kann jetzt neu gestartet werden:\n"
        f"<code>systemctl start kongtrade-bot</code>"
    )
    _telegram(msg)
    print("  ✅ Telegram-Bestätigung gesendet")

    print("\n  Done. Bot kann jetzt neu gestartet werden:")
    print("  $ systemctl start kongtrade-bot")
    print("=" * 60)


if __name__ == "__main__":
    main()
