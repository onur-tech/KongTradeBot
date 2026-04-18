"""
claim_all.py — Automatisches Einlösen aller redeemable Polymarket-Positionen

Ruft alle redeemable=True Positionen über die Data-API ab und löst sie
via py-clob-client redeem() ein. Kann manuell oder aus main.py aufgerufen werden.

Verwendung:
    python3 claim_all.py              # einmalig ausführen
    python3 claim_all.py --dry        # nur anzeigen, nicht einlösen
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger
from utils.config import Config

logger = get_logger("claim")

POLYMARKET_DATA_API = "https://data-api.polymarket.com"
AUTO_CLAIM_INTERVAL_S = int(os.getenv("AUTO_CLAIM_INTERVAL_S", "300"))


def is_claimable(pos: dict) -> bool:
    return any(pos.get(k) for k in ("redeemable", "isRedeemable", "is_redeemable"))


async def fetch_redeemable_positions(proxy_address: str) -> list:
    """Holt alle redeemable Positionen von der Data-API."""
    try:
        import aiohttp
        url = f"{POLYMARKET_DATA_API}/positions?user={proxy_address}&sizeThreshold=.01&limit=500"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"Data-API HTTP {resp.status}")
                    return []
                positions = await resp.json()
                if not isinstance(positions, list):
                    positions = positions.get("data", []) if isinstance(positions, dict) else []

        redeemable = []
        for p in positions:
            cur_value = float(p.get("currentValue") or p.get("value") or 0)
            if is_claimable(p) and cur_value > 0.01:
                redeemable.append(p)

        return redeemable
    except Exception as e:
        logger.error(f"fetch_redeemable_positions fehlgeschlagen: {e}")
        return []


async def redeem_position(config: Config, position: dict, dry_run: bool = False) -> bool:
    """Löst eine einzelne Position ein."""
    try:
        from py_clob_client.client import ClobClient

        condition_id = str(position.get("conditionId") or position.get("market") or "")
        token_id = str(position.get("asset_id") or position.get("tokenId") or "")
        cur_value = float(position.get("currentValue") or 0)
        outcome = str(position.get("outcome") or "?")

        if not condition_id:
            logger.warning(f"Kein conditionId für Position: {outcome}")
            return False

        if dry_run:
            logger.info(f"[DRY] Würde einlösen: {outcome} | ${cur_value:.2f}")
            return True

        client = ClobClient(
            host=getattr(config, 'clob_host', 'https://clob.polymarket.com'),
            key=config.private_key,
            chain_id=137,
            signature_type=1,
            funder=config.polymarket_address,
        )
        client.set_api_creds(client.derive_api_key())

        # redeem() takes condition_id
        result = client.redeem(condition_id)
        logger.info(f"✅ Eingelöst: {outcome} | ${cur_value:.2f} | tx={str(result)[:20]}")
        return True

    except Exception as e:
        logger.error(f"redeem fehlgeschlagen für {position.get('outcome','?')}: {e}")
        return False


async def claim_all(config: Config, dry_run: bool = False) -> dict:
    """
    Hauptfunktion: Alle redeemable Positionen einlösen.
    Gibt {"claimed": N, "total_usdc": X, "errors": M} zurück.
    """
    proxy = getattr(config, 'polymarket_address', None)
    if not proxy:
        logger.error("Keine polymarket_address in Config")
        return {"claimed": 0, "total_usdc": 0.0, "errors": 0}

    redeemable = await fetch_redeemable_positions(proxy)

    if not redeemable:
        logger.info("Keine redeemable Positionen gefunden")
        return {"claimed": 0, "total_usdc": 0.0, "errors": 0}

    total_value = sum(float(p.get("currentValue") or 0) for p in redeemable)
    logger.info(f"🎯 {len(redeemable)} redeemable Positionen gefunden | Total: ${total_value:.2f}")

    claimed = 0
    errors = 0
    claimed_usdc = 0.0

    for pos in redeemable:
        success = await redeem_position(config, pos, dry_run=dry_run)
        if success:
            claimed += 1
            claimed_usdc += float(pos.get("currentValue") or 0)
        else:
            errors += 1
        # Small delay between redemptions
        await asyncio.sleep(1.0)

    if not dry_run and claimed > 0:
        logger.info(f"✅ Claim abgeschlossen: {claimed}/{len(redeemable)} | ${claimed_usdc:.2f} zurück in Balance")

    return {"claimed": claimed, "total_usdc": claimed_usdc, "errors": errors}


async def claim_loop(config: Config, interval_s: int = AUTO_CLAIM_INTERVAL_S):
    """
    Loop der alle interval_s Sekunden nach redeemable Positionen sucht und sie einlöst.
    Aus main.py als asyncio.create_task() starten.
    """
    logger.info(f"AutoClaim-Loop gestartet | Intervall: {interval_s}s")
    while True:
        try:
            result = await claim_all(config, dry_run=False)
            if result["claimed"] > 0:
                logger.info(f"💰 AutoClaim: ${result['total_usdc']:.2f} eingelöst ({result['claimed']} Positionen)")
                # Telegram-Notification
                try:
                    from telegram_bot import send
                    await send(f"💰 Auto-Claim: ${result['total_usdc']:.2f} eingelöst ({result['claimed']} Positionen) — Cash wiederhergestellt!")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"claim_loop Fehler: {e}")
        await asyncio.sleep(interval_s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claim all redeemable Polymarket positions")
    parser.add_argument("--dry", action="store_true", help="Dry run — nur anzeigen, nicht einlösen")
    args = parser.parse_args()

    config = Config()

    result = asyncio.run(claim_all(config, dry_run=args.dry))
    print(f"\nErgebnis: {result['claimed']} eingelöst | ${result['total_usdc']:.2f} | {result['errors']} Fehler")
