"""
claim_all.py — Erkennung und Meldung von redeemable Polymarket-Positionen

Findet Positionen mit redeemable=True und benachrichtigt per Telegram.
Manuelles Einlösen auf polymarket.com → Positions → Claim erforderlich.

Hintergrund:
  Auto-Redeem erfordert entweder Builder-API-Credentials (Polymarket-Partner)
  oder den Wallet-Owner-Key. Der Bot nutzt einen separaten API-Signing-Key,
  der nur für CLOB-Orders autorisiert ist.

Verwendung:
    python3 claim_all.py              # einmalig prüfen und melden
    python3 claim_all.py --dry        # nur anzeigen, keine Telegram-Meldung
"""

import asyncio
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger

logger = get_logger("claim")

POLYMARKET_DATA_API    = "https://data-api.polymarket.com"
AUTO_CLAIM_INTERVAL_S  = int(os.getenv("AUTO_CLAIM_INTERVAL_S", "300"))
CLAIM_ERROR_COOLDOWN_S = int(os.getenv("CLAIM_ERROR_ALERT_COOLDOWN_S", "3600"))

# Rate-limit: condition_id → last alerted timestamp
_claim_notified: dict = {}


def is_claimable(pos: dict) -> bool:
    return any(pos.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable"))


async def fetch_redeemable_positions(proxy_address: str) -> list:
    """Holt alle redeemable Positionen von der Data-API."""
    try:
        import aiohttp
        url = (
            f"{POLYMARKET_DATA_API}/positions"
            f"?user={proxy_address}&sizeThreshold=.01&limit=500"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Data-API HTTP {resp.status}")
                    return []
                positions = await resp.json()
                if not isinstance(positions, list):
                    positions = (
                        positions.get("data", [])
                        if isinstance(positions, dict)
                        else []
                    )

        redeemable = [
            p for p in positions
            if is_claimable(p) and float(p.get("currentValue") or 0) > 0.01
        ]
        return redeemable
    except Exception as e:
        logger.error(f"fetch_redeemable_positions fehlgeschlagen: {e}")
        return []


async def _notify_redeemable(position: dict, dry_run: bool) -> None:
    """Sendet eine Telegram-Benachrichtigung für eine redeemable Position."""
    condition_id = str(position.get("conditionId") or "")
    cur_value = float(position.get("currentValue") or 0)
    outcome = str(position.get("outcome") or "?")
    title = str(position.get("title") or "?")

    now = time.time()
    last = _claim_notified.get(condition_id, 0)
    if not dry_run and now - last < CLAIM_ERROR_COOLDOWN_S:
        return

    if dry_run:
        logger.info(
            f"[DRY] Redeemable: {title} | {outcome} | ${cur_value:.2f} | "
            f"conditionId={condition_id[:14]}..."
        )
        return

    _claim_notified[condition_id] = now
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    cid_short = condition_id[:14] if condition_id else "?"
    msg = (
        f"💰 <b>Claimable Position</b>\n"
        f"📌 {title}\n"
        f"✅ Outcome: {outcome}\n"
        f"💵 Wert: <b>${cur_value:.2f}</b>\n"
        f"🔗 Auf <a href='https://polymarket.com'>polymarket.com</a> einlösen\n"
        f"🕐 {ts}"
    )
    try:
        from telegram_bot import send
        await send(msg)
        logger.info(f"✅ Telegram-Alert gesendet: {outcome} | ${cur_value:.2f}")
    except Exception as e:
        logger.error(f"Telegram-Benachrichtigung fehlgeschlagen: {e}")


async def claim_all(config, dry_run: bool = False) -> dict:
    """
    Hauptfunktion: Alle redeemable Positionen finden und per Telegram melden.
    Gibt {"notified": N, "total_usdc": X} zurück.
    """
    proxy = getattr(config, "polymarket_address", None)
    if not proxy:
        logger.error("Keine polymarket_address in Config")
        return {"notified": 0, "total_usdc": 0.0, "errors": 0}

    redeemable = await fetch_redeemable_positions(proxy)

    if not redeemable:
        logger.info("Keine redeemable Positionen gefunden")
        return {"notified": 0, "total_usdc": 0.0, "errors": 0}

    total_value = sum(float(p.get("currentValue") or 0) for p in redeemable)
    logger.info(
        f"🎯 {len(redeemable)} redeemable Positionen gefunden | Total: ${total_value:.2f}"
    )

    notified = 0
    for pos in redeemable:
        await _notify_redeemable(pos, dry_run=dry_run)
        notified += 1
        await asyncio.sleep(0.5)

    return {"notified": notified, "total_usdc": total_value, "errors": 0,
            "failed_positions": []}


async def claim_loop(config, interval_s: int = AUTO_CLAIM_INTERVAL_S):
    """
    Loop der alle interval_s Sekunden nach redeemable Positionen sucht und meldet.
    Aus main.py als asyncio.create_task() starten.
    """
    logger.info(f"AutoClaim-Loop gestartet | Intervall: {interval_s}s")
    while True:
        try:
            result = await claim_all(config, dry_run=False)
            if result["total_usdc"] > 0:
                logger.info(
                    f"💰 Claimable: ${result['total_usdc']:.2f} "
                    f"({result['notified']} Positionen) → Telegram-Alert gesendet"
                )
        except Exception as e:
            logger.error(f"claim_loop Fehler: {e}")
        await asyncio.sleep(interval_s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect redeemable Polymarket positions"
    )
    parser.add_argument(
        "--dry", action="store_true", help="Dry run — nur anzeigen, kein Telegram"
    )
    args = parser.parse_args()

    from utils.config import load_config
    config = load_config()

    result = asyncio.run(claim_all(config, dry_run=args.dry))
    print(
        f"\nErgebnis: {result['notified']} gemeldet | "
        f"${result['total_usdc']:.2f} | {result['errors']} Fehler"
    )
