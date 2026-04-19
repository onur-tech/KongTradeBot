"""
utils/balance_cli.py — USDC-Balance via polymarket-cli

Fallback wenn CLOB-SDK get_balance_allowance() mit
'GetBalanceAndAllowance invalid params: assetAddress invalid hex address'
fehlschlägt. Nutzt polymarket-cli binary statt py-clob-client SDK.
"""

import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def get_usdc_balance_via_cli() -> float | None:
    """
    Holt USDC-Balance (CLOB collateral) via polymarket-cli binary.
    Gibt None zurück wenn cli nicht verfügbar oder Fehler.
    """
    private_key = os.getenv("PRIVATE_KEY", "")
    if not private_key:
        logger.debug("[balance_cli] PRIVATE_KEY nicht gesetzt")
        return None

    cli_path = _find_cli()
    if not cli_path:
        logger.debug("[balance_cli] polymarket binary nicht gefunden")
        return None

    try:
        result = subprocess.run(
            [cli_path, "-o", "json", "clob", "balance", "--asset-type", "collateral"],
            env={**os.environ, "POLYMARKET_PRIVATE_KEY": private_key},
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.warning(f"[balance_cli] returncode={result.returncode}: {result.stderr[:150]}")
            return None

        raw = result.stdout.strip()
        if not raw:
            return None

        # Versuche JSON-Parse
        try:
            data = json.loads(raw)
            balance_str = str(
                data.get("balance") or data.get("value") or data.get("amount") or "0"
            )
            return float(balance_str)
        except (json.JSONDecodeError, ValueError):
            # Fallback: "Balance: $463.35" Plain-Text-Format parsen
            for line in raw.splitlines():
                if "Balance:" in line or "balance:" in line.lower():
                    parts = line.replace("$", "").replace(",", "").split()
                    for part in reversed(parts):
                        try:
                            return float(part)
                        except ValueError:
                            continue
            logger.warning(f"[balance_cli] Unbekanntes Output-Format: {raw[:100]}")
            return None

    except subprocess.TimeoutExpired:
        logger.warning("[balance_cli] Timeout nach 15s")
        return None
    except Exception as e:
        logger.warning(f"[balance_cli] Exception: {e}")
        return None


def _find_cli() -> str | None:
    """Sucht polymarket binary in PATH und bekannten Locations."""
    import shutil
    path = shutil.which("polymarket")
    if path:
        return path
    for candidate in ["/usr/local/bin/polymarket", "/usr/bin/polymarket", os.path.expanduser("~/.cargo/bin/polymarket")]:
        if os.path.isfile(candidate):
            return candidate
    return None
