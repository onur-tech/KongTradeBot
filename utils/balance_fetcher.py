"""
balance_fetcher.py — Liest USDC-Kontostand direkt von Polygon Blockchain

Kein py-clob-client nötig — nutzt öffentlichen Polygon RPC.
USDC Contract auf Polygon: 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
"""

import asyncio
import aiohttp
import json
from utils.logger import get_logger

logger = get_logger("balance")

POLYGON_RPC_ENDPOINTS = [
    "https://rpc.ankr.com/polygon",
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
]
USDC_CONTRACT = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


def _build_balance_payload(wallet_address: str) -> dict:
    """Erstellt eth_call Payload für USDC balanceOf(address)."""
    # balanceOf(address) = 0x70a08231
    padded = wallet_address.lower().replace("0x", "").zfill(64)
    data = f"0x70a08231{padded}"
    return {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {"to": USDC_CONTRACT, "data": data},
            "latest"
        ],
        "id": 1
    }


async def fetch_usdc_balance(wallet_address: str) -> float:
    """
    Liest USDC-Kontostand von Polygon Blockchain.
    Gibt Kontostand in USDC zurück (nicht Wei).
    Gibt 0.0 zurück bei Fehler.
    """
    payload = _build_balance_payload(wallet_address)
    async with aiohttp.ClientSession() as session:
        for rpc in POLYGON_RPC_ENDPOINTS:
            try:
                async with session.post(
                    rpc,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Balance-Abfrage fehlgeschlagen ({rpc}): HTTP {resp.status}")
                        continue
                    data = await resp.json()
                    result = data.get("result", "0x0")
                    # USDC hat 6 Dezimalstellen (nicht 18 wie ETH)
                    balance_wei = int(result, 16)
                    balance_usdc = balance_wei / 1_000_000
                    if balance_usdc <= 0:
                        logger.warning(f"RPC {rpc} liefert $0.00 — versuche nächsten RPC")
                        continue
                    logger.info(f"💳 Wallet Balance: ${balance_usdc:.2f} USDC (via {rpc})")
                    return balance_usdc
            except Exception as e:
                logger.warning(f"Balance-Abfrage Fehler ({rpc}): {e}")
                continue
    return 0.0


async def update_budget_from_chain(config) -> float:
    """
    Liest echten Kontostand und aktualisiert config.portfolio_budget_usd.
    Wird beim Start und alle 5 Minuten aufgerufen.
    """
    if not config.polymarket_address or config.polymarket_address == "0xDEINE_POLYMARKET_ADRESSE":
        logger.info("Balance-Abfrage übersprungen (keine Wallet-Adresse konfiguriert)")
        return config.portfolio_budget_usd

    balance = await fetch_usdc_balance(config.polymarket_address)

    if balance > 0:
        config.portfolio_budget_usd = balance
        max_invest = config.max_total_invested_usd
        logger.info(
            f"💳 Budget aktualisiert: ${balance:.2f} USDC | "
            f"Max investierbar: ${max_invest:.2f} USDC ({config.max_portfolio_pct*100:.0f}%)"
        )
    else:
        logger.warning("Balance konnte nicht gelesen werden — benutze manuellen Wert aus .env")

    return config.portfolio_budget_usd
