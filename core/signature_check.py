"""
Signature-Type-Self-Check (Phase 2.2)

Validates at startup that PRIVATE_KEY, POLYMARKET_ADDRESS, and SIGNATURE_TYPE
are consistent. Logs warnings only — does NOT abort the bot.

SIGNATURE_TYPE:
  1 = Polymarket Magic-Link proxy wallet (default)
  0 = Direct EOA / MetaMask signing
"""
import os
import re
from typing import List, Literal
from utils.logger import get_logger

logger = get_logger("signature_check")

_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_DEFAULT_SIG_TYPE = 1
_sim_log: List[str] = []


def run_self_check(mode: Literal["live", "simulation"] = "live") -> bool:
    """
    Runs startup signature configuration check.
    Returns True if all checks pass, False if any warning was emitted.
    Never raises — warnings only.
    """
    ok = True

    private_key = os.getenv("PRIVATE_KEY", "").strip()
    poly_address = os.getenv("POLYMARKET_ADDRESS", "").strip()
    sig_type_raw = os.getenv("SIGNATURE_TYPE", str(_DEFAULT_SIG_TYPE)).strip()

    # --- Private key ---
    if not private_key:
        logger.error("[SigCheck] PRIVATE_KEY is not set")
        ok = False
    else:
        key_hex = private_key.removeprefix("0x")
        if len(key_hex) != 64 or not all(c in "0123456789abcdefABCDEF" for c in key_hex):
            logger.warning(
                f"[SigCheck] PRIVATE_KEY has unexpected format (len={len(key_hex)} chars) — "
                "expected 64 hex chars"
            )
            ok = False

    # --- Polymarket address ---
    if not poly_address:
        logger.error("[SigCheck] POLYMARKET_ADDRESS is not set")
        ok = False
    elif not _ADDR_RE.match(poly_address):
        logger.warning(
            f"[SigCheck] POLYMARKET_ADDRESS format invalid: '{poly_address[:12]}...' — "
            "expected 0x + 40 hex chars"
        )
        ok = False

    # --- Signature type ---
    try:
        sig_type = int(sig_type_raw)
    except ValueError:
        logger.warning(f"[SigCheck] SIGNATURE_TYPE='{sig_type_raw}' is not an integer")
        ok = False
        sig_type = _DEFAULT_SIG_TYPE

    if sig_type not in (0, 1):
        logger.warning(
            f"[SigCheck] SIGNATURE_TYPE={sig_type} is unexpected — valid: 0 (EOA), 1 (Magic-Link)"
        )
        ok = False
    elif sig_type != _DEFAULT_SIG_TYPE:
        logger.warning(
            f"[SigCheck] SIGNATURE_TYPE={sig_type} differs from default={_DEFAULT_SIG_TYPE}. "
            "Using EOA mode — ensure PRIVATE_KEY is the direct wallet key, not a Polymarket key."
        )

    prefix = "[SIM SigCheck]" if mode == "simulation" else "[SigCheck]"
    if ok:
        addr_short = poly_address[:10] + "..." if len(poly_address) > 10 else poly_address
        logger.info(f"{prefix} OK — address={addr_short} sig_type={sig_type}")
    else:
        logger.warning(
            f"{prefix} One or more credential checks failed. "
            "Verify .env before switching to live trading."
        )
    if mode == "simulation":
        _sim_log.append(f"{prefix} result={ok}")

    return ok
