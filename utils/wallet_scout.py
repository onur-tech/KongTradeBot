"""
wallet_scout.py — Automatischer Wallet Scout

Läuft täglich um 09:00 Uhr.
Scrapt polymonit.com/leaderboard, findet neue Top-Wallets (>60% Win Rate, >$500K Profit)
die noch nicht in TARGET_WALLETS sind, und schickt Telegram-Benachrichtigung.

Verwendung in main.py:
    from utils.wallet_scout import scout_loop
    asyncio.create_task(scout_loop(config))
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger("wallet_scout")

LEADERBOARD_URL = "https://polymonit.com/leaderboard"
MIN_WIN_RATE    = 0.60        # 60% Mindest-Win-Rate
MIN_PROFIT_USD  = 500_000.0   # $500K Mindest-Profit
SCOUT_HOUR      = 9           # Täglich um 09:00 Uhr


@dataclass
class ScoutedWallet:
    address: str
    name: str
    win_rate: float    # 0.0 – 1.0
    profit_usd: float
    total_trades: int

    def __str__(self):
        return (
            f"{self.name} | Win Rate: {self.win_rate:.0%} | "
            f"Profit: ${self.profit_usd:,.0f} | Trades: {self.total_trades}"
        )


# ── Scraper ───────────────────────────────────────────────────────────────────

def _parse_money(text: str) -> float:
    """Parst '$1.2M', '$500K', '$1,234,567' → float."""
    text = text.strip().replace(",", "").replace("$", "").upper()
    try:
        if text.endswith("M"):
            return float(text[:-1]) * 1_000_000
        if text.endswith("K"):
            return float(text[:-1]) * 1_000
        return float(text)
    except (ValueError, AttributeError):
        return 0.0


def _parse_pct(text: str) -> float:
    """Parst '73.4%' → 0.734."""
    try:
        return float(text.strip().replace("%", "")) / 100
    except (ValueError, AttributeError):
        return 0.0


def _is_eth_address(text: str) -> bool:
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", text.strip()))


def scrape_leaderboard() -> List[ScoutedWallet]:
    """
    Scrapt polymonit.com/leaderboard.
    Gibt eine Liste von ScoutedWallet zurück, sortiert nach Profit (absteigend).
    Gibt [] zurück wenn Scraping fehlschlägt — niemals werfen.
    """
    if not SCRAPING_AVAILABLE:
        logger.warning("requests/beautifulsoup4 nicht installiert — Scout deaktiviert")
        return []

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(LEADERBOARD_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Leaderboard-Abruf fehlgeschlagen: {e}")
        return []

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        wallets = _parse_html(soup)
        logger.info(f"Leaderboard geparst: {len(wallets)} Wallets gefunden")
        return sorted(wallets, key=lambda w: w.profit_usd, reverse=True)
    except Exception as e:
        logger.warning(f"Leaderboard-Parsing fehlgeschlagen: {e}")
        return []


def _parse_html(soup: BeautifulSoup) -> List[ScoutedWallet]:
    """
    Versucht mehrere Parsing-Strategien für polymonit.com.
    Polymonit kann sein Layout ändern — daher mehrere Fallbacks.
    """
    wallets: List[ScoutedWallet] = []

    # Strategie 1: Standard HTML-Tabelle
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        for row in rows[1:]:  # Header überspringen
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            w = _extract_from_row(cols, row)
            if w:
                wallets.append(w)
        if wallets:
            return wallets

    # Strategie 2: Zeilen mit data-address Attribut
    rows = soup.find_all(attrs={"data-address": True})
    for row in rows:
        address = row.get("data-address", "").strip()
        if not _is_eth_address(address):
            continue
        texts = [el.get_text(strip=True) for el in row.find_all(["td", "div", "span"])]
        w = _extract_from_texts(address, texts)
        if w:
            wallets.append(w)
    if wallets:
        return wallets

    # Strategie 3: Links mit Ethereum-Adressen + umliegende Zahlen
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        address_match = re.search(r"0x[0-9a-fA-F]{40}", href)
        if not address_match:
            address_match = re.search(r"0x[0-9a-fA-F]{40}", link.get_text())
        if not address_match:
            continue

        address = address_match.group(0).lower()
        name    = link.get_text(strip=True)
        if _is_eth_address(name):
            name = address[:10] + "..."

        # Alle Zahlen im Elternelement sammeln
        parent = link.parent
        texts  = [el.get_text(strip=True) for el in parent.find_all(["td", "div", "span"])]
        w = _extract_from_texts(address, texts, name=name)
        if w:
            wallets.append(w)

    return wallets


def _extract_from_row(cols: List[str], row) -> Optional[ScoutedWallet]:
    """Extrahiert Wallet-Daten aus einer Tabellenzeile."""
    address = ""
    name    = ""

    # Adresse aus Link oder Text
    for link in row.find_all("a", href=True):
        m = re.search(r"0x[0-9a-fA-F]{40}", link.get("href", "") + link.get_text())
        if m:
            address = m.group(0).lower()
            txt = link.get_text(strip=True)
            name = txt if not _is_eth_address(txt) else address[:10] + "..."
            break

    if not address:
        for col in cols:
            m = re.search(r"0x[0-9a-fA-F]{40}", col)
            if m:
                address = m.group(0).lower()
                break

    if not address:
        return None

    return _extract_from_texts(address, cols, name=name)


def _extract_from_texts(
    address: str, texts: List[str], name: str = ""
) -> Optional[ScoutedWallet]:
    """Extrahiert Win Rate, Profit, Trades aus einer Liste von Text-Fragmenten."""
    win_rate = 0.0
    profit   = 0.0
    trades   = 0

    for text in texts:
        text = text.strip()
        if not text:
            continue

        # Adresse als Name überspringen
        if _is_eth_address(text):
            if not name:
                name = text[:10] + "..."
            continue

        # Name: erster nicht-numerischer, nicht-%-Block
        if not name and re.match(r"^[A-Za-z]", text) and len(text) < 40:
            name = text

        # Win Rate
        if "%" in text and not win_rate:
            win_rate = _parse_pct(text)

        # Profit ($-Wert oder M/K-Suffix)
        if re.search(r"[\$\d].*[MK]?$", text) and not profit:
            candidate = _parse_money(text)
            if candidate > 1000:  # Profit ist immer > $1K
                profit = candidate

        # Trade-Anzahl (ganze Zahl ohne Sonderzeichen)
        if re.match(r"^\d+$", text) and not trades:
            n = int(text)
            if 1 <= n <= 100_000:
                trades = n

    if not address or not _is_eth_address(address):
        return None

    return ScoutedWallet(
        address=address.lower(),
        name=name or address[:10] + "...",
        win_rate=win_rate,
        profit_usd=profit,
        total_trades=trades,
    )


# ── Vergleich mit bekannten Wallets ───────────────────────────────────────────

def find_new_top_wallets(
    scraped: List[ScoutedWallet],
    known_addresses: List[str],
    top_n: int = 10,
) -> List[ScoutedWallet]:
    """
    Gibt Wallets zurück die:
    - Unter den Top-N nach Profit sind
    - Win Rate > MIN_WIN_RATE
    - Profit > MIN_PROFIT_USD
    - Noch NICHT in known_addresses sind
    """
    known_lower = {a.lower() for a in known_addresses}
    candidates  = scraped[:top_n]

    new_wallets = []
    for w in candidates:
        if w.address in known_lower:
            continue
        if w.win_rate < MIN_WIN_RATE:
            continue
        if w.profit_usd < MIN_PROFIT_USD:
            continue
        new_wallets.append(w)

    return new_wallets


# ── Telegram-Nachricht ────────────────────────────────────────────────────────

def build_scout_message(wallet: ScoutedWallet) -> str:
    rank_emoji = "🔥" if wallet.win_rate >= 0.70 else "🔍"
    lines = [
        f"{rank_emoji} <b>NEUE TOP-WALLET GEFUNDEN</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 Name: <b>{wallet.name}</b>",
        f"📊 Win Rate: <b>{wallet.win_rate:.0%}</b>",
        f"💰 Profit: <b>${wallet.profit_usd:,.0f}</b>",
        f"🔢 Trades: <b>{wallet.total_trades}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📋 Adresse:",
        f"<code>{wallet.address}</code>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"➕ Hinzufügen? Antworte mit:",
        f"<code>/add {wallet.address}</code>",
    ]
    return "\n".join(lines)


# ── Täglicher Loop ────────────────────────────────────────────────────────────

async def scout_loop(config):
    """
    Hauptschleife: läuft täglich um SCOUT_HOUR Uhr.
    Wird als asyncio.Task in main.py gestartet.
    """
    logger.info(f"WalletScout gestartet — läuft täglich um {SCOUT_HOUR:02d}:00 Uhr")

    if not SCRAPING_AVAILABLE:
        logger.warning(
            "WalletScout: requests/beautifulsoup4 fehlen — "
            "bitte 'pip install requests beautifulsoup4' ausführen"
        )
        return

    while True:
        try:
            now      = datetime.now()
            next_run = now.replace(hour=SCOUT_HOUR, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)

            wait_s = (next_run - now).total_seconds()
            logger.info(
                f"WalletScout: nächster Scan in "
                f"{wait_s/3600:.1f}h ({next_run.strftime('%d.%m. %H:%M')})"
            )
            await asyncio.sleep(wait_s)

            await _run_scout(config)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"WalletScout Loop Fehler: {e} — versuche erneut in 1h")
            await asyncio.sleep(3600)


async def run_scout_now(config):
    """Für manuellen Aufruf / Tests."""
    await _run_scout(config)


async def _run_scout(config):
    """Führt einen Scout-Durchlauf durch."""
    logger.info("WalletScout: Starte Leaderboard-Scan...")

    # Scraping im Thread-Pool (requests ist sync)
    loop    = asyncio.get_event_loop()
    scraped = await loop.run_in_executor(None, scrape_leaderboard)

    if not scraped:
        logger.warning("WalletScout: Keine Wallet-Daten gescrapt — überspringe")
        return

    new_wallets = find_new_top_wallets(
        scraped=scraped,
        known_addresses=config.target_wallets,
        top_n=10,
    )

    if not new_wallets:
        logger.info("WalletScout: Keine neuen Top-Wallets gefunden")
        return

    logger.info(f"WalletScout: {len(new_wallets)} neue Top-Wallet(s) gefunden!")

    # Telegram-Import hier um zirkuläre Imports zu vermeiden
    from telegram_bot import send
    for wallet in new_wallets:
        logger.info(f"  → {wallet}")
        await send(build_scout_message(wallet))
