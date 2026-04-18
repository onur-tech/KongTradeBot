"""
wallet_scout.py — Automatischer Wallet Scout + Wallet Decay Tracker

Scout: Läuft täglich um 09:00 Uhr.
Scrapt polymonit.com/leaderboard, findet neue Top-Wallets (>60% Win Rate, >$500K Profit)
die noch nicht in TARGET_WALLETS sind, und schickt Telegram-Benachrichtigung.

Decay Tracker: Überwacht Win Rate Rückgang pro Wallet über mehrere Tage.
Wenn Win Rate >10% unter Gesamt-Win Rate für 3+ Tage → Multiplikator halbieren + Alert.

Verwendung in main.py:
    from utils.wallet_scout import scout_loop, WalletDecayTracker
    asyncio.create_task(scout_loop(config))
"""

import asyncio
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger("wallet_scout")

LEADERBOARD_URL  = "https://polymonit.com/leaderboard"
SCOUT_DB_FILE    = os.getenv("WALLET_SCOUT_DB", "data/wallet_scout.db")


# ── SQLite Init ───────────────────────────────────────────────────────────────

def _init_scout_db(db_path: str = SCOUT_DB_FILE) -> None:
    """Legt DB und Tabellen an falls nicht vorhanden. Idempotent."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS wallet_scout_daily (
                scan_date       TEXT NOT NULL,
                scan_timestamp  TEXT NOT NULL,
                wallet_address  TEXT NOT NULL,
                alias           TEXT,
                rank            INTEGER,
                win_rate        REAL,
                roi_pct         REAL,
                volume_usd      REAL,
                pnl_usd         REAL,
                source          TEXT NOT NULL,
                notes           TEXT,
                PRIMARY KEY (scan_date, wallet_address, source)
            );
            CREATE INDEX IF NOT EXISTS idx_wallet_date
                ON wallet_scout_daily(wallet_address, scan_date);
            CREATE INDEX IF NOT EXISTS idx_source_date
                ON wallet_scout_daily(source, scan_date);
        """)


def _save_scan_results(
    wallets: List, source: str = "polymonit", db_path: str = SCOUT_DB_FILE
) -> int:
    """
    Schreibt Scan-Ergebnisse in SQLite. INSERT OR REPLACE (idempotent pro Tag).
    Gibt Anzahl gespeicherter Rows zurück.
    """
    _init_scout_db(db_path)
    now_utc    = datetime.now(timezone.utc)
    scan_date  = now_utc.strftime("%Y-%m-%d")
    scan_ts    = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    saved = 0
    try:
        with sqlite3.connect(db_path) as c:
            for rank, w in enumerate(wallets, start=1):
                c.execute(
                    """INSERT OR REPLACE INTO wallet_scout_daily
                       (scan_date, scan_timestamp, wallet_address, alias,
                        rank, win_rate, roi_pct, volume_usd, pnl_usd, source, notes)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        scan_date, scan_ts,
                        w.address.lower(), w.name,
                        rank,
                        round(w.win_rate, 4) if w.win_rate else None,
                        None,   # roi_pct — nicht von polymonit verfügbar
                        None,   # volume_usd — nicht verfügbar
                        round(w.profit_usd, 2) if w.profit_usd else None,
                        source,
                        None,
                    ),
                )
                saved += 1
        logger.info(f"Scout DB: {saved} Wallets für {scan_date} ({source}) gespeichert")
    except Exception as e:
        logger.error(f"Scout DB Schreib-Fehler: {e}")
    return saved

# ── Wallet Decay Tracker ──────────────────────────────────────────────────────

DECAY_STATE_FILE = "wallet_decay_state.json"
DECAY_DAYS       = 3     # Tage mit anhaltendem Rückgang bevor Alarm
DECAY_THRESHOLD  = 0.10  # >10% Abfall unter Gesamt-Win Rate


class WalletDecayTracker:
    """
    Verfolgt tägliche Win Rate Entwicklung pro Wallet.

    Logik:
    - Täglich wird ein Snapshot der (Gesamt-WR, Letzte-20-WR) gespeichert
    - Wenn Recent-WR um >10% unter Gesamt-WR liegt → "declining"
    - Nach 3+ aufeinanderfolgenden Declining-Tagen → Alarm + Multiplikator halbieren

    Verwendung:
        tracker = WalletDecayTracker()
        if tracker.snapshot(wallet_addr, total_wr=0.62, recent_wr=0.45):
            # 3+ Tage Rückgang → Alert senden
    """

    def __init__(self):
        self._state: Dict[str, List[dict]] = self._load()

    def snapshot(self, wallet: str, total_wr: float, recent_wr: float) -> bool:
        """
        Speichert den heutigen Win-Rate-Stand für eine Wallet.
        Gibt True zurück wenn der Rückgang seit DECAY_DAYS+ Tagen anhält.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        is_declining = total_wr > 0 and (total_wr - recent_wr) > DECAY_THRESHOLD

        history = self._state.get(wallet, [])
        history = [d for d in history if d["date"] != today]
        history.append({
            "date":       today,
            "total_wr":   round(total_wr, 4),
            "recent_wr":  round(recent_wr, 4),
            "declining":  is_declining,
        })
        history = sorted(history, key=lambda x: x["date"])[-14:]
        self._state[wallet] = history
        self._save()

        if len(history) < DECAY_DAYS:
            return False
        return all(d["declining"] for d in history[-DECAY_DAYS:])

    def consecutive_decline_days(self, wallet: str) -> int:
        """Gibt die Anzahl aufeinanderfolgender Declining-Tage zurück."""
        history = self._state.get(wallet, [])
        count = 0
        for d in reversed(history):
            if d.get("declining"):
                count += 1
            else:
                break
        return count

    def _load(self) -> Dict:
        if not os.path.exists(DECAY_STATE_FILE):
            return {}
        try:
            with open(DECAY_STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        try:
            with open(DECAY_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Decay-State konnte nicht gespeichert werden: {e}")


def build_decay_alert_message(
    wallet_name: str,
    total_wr: float,
    recent_wr: float,
    days: int,
    old_mult: float,
    new_mult: float,
) -> str:
    delta = total_wr - recent_wr
    lines = [
        "📉 <b>WALLET DECAY ALERT</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 Wallet: <b>{wallet_name}</b>",
        f"📊 Gesamt Win Rate: <b>{total_wr:.0%}</b>",
        f"📉 Letzte 20 Trades: <b>{recent_wr:.0%}</b>",
        f"⚠️  Abfall: <b>-{delta:.0%}</b> seit {days} Tagen",
        f"⚖️  Multiplikator: <b>{old_mult:.1f}x → {new_mult:.1f}x</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "Trades dieser Wallet werden mit halbiertem Einsatz ausgeführt.",
    ]
    return "\n".join(lines)


async def decay_monitor_loop(strategy, config):
    """
    Täglicher Loop der alle Wallets auf anhaltenden Decay prüft.
    Wird als asyncio.Task in main.py gestartet.

    strategy: CopyTradingStrategy (hat .wallet_performance)
    config: Config
    """
    from strategies.copy_trading import get_wallet_name, get_wallet_multiplier
    tracker = WalletDecayTracker()
    logger.info("DecayMonitor gestartet — prüft täglich um 23:00 Uhr")

    while True:
        try:
            now      = datetime.now()
            next_run = now.replace(hour=23, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            await asyncio.sleep((next_run - now).total_seconds())

            from telegram_bot import send
            for wallet, perf in strategy.wallet_performance.items():
                if perf.trades_total < 10:
                    continue

                total_wr  = perf.win_rate
                recent_wr = perf.recent_win_rate
                in_decay  = tracker.snapshot(wallet, total_wr, recent_wr)
                days      = tracker.consecutive_decline_days(wallet)

                if in_decay:
                    old_mult = get_wallet_multiplier(wallet)
                    new_mult = round(old_mult / 2, 2)
                    name     = get_wallet_name(wallet)
                    msg = build_decay_alert_message(name, total_wr, recent_wr, days, old_mult, new_mult)
                    logger.warning(
                        f"DECAY ALERT: {name} | Gesamt {total_wr:.0%} vs. Recent {recent_wr:.0%} "
                        f"seit {days} Tagen"
                    )
                    await send(msg)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"DecayMonitor Fehler: {e} — weiter in 1h")
            await asyncio.sleep(3600)


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

    # ── SQLite Historisierung ────────────────────────────────────────────────
    await loop.run_in_executor(
        None, lambda: _save_scan_results(scraped, source="polymonit")
    )

    new_wallets = find_new_top_wallets(
        scraped=scraped,
        known_addresses=config.target_wallets,
        top_n=10,
    )

    if not new_wallets:
        logger.info("WalletScout: Keine neuen Top-Wallets gefunden")
        return

    logger.info(f"WalletScout: {len(new_wallets)} neue Top-Wallet(s) gefunden!")

    from telegram_bot import send
    for wallet in new_wallets:
        logger.info(f"  → {wallet}")
        await send(build_scout_message(wallet))
