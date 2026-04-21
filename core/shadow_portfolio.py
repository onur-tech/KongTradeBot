# SHADOW PORTFOLIO — Unbegrenzt (kein Kapital-Limit)
# Ziel: maximale Datenpunkte für Kalibrierung und Backtesting
# Keine echten Trades, keine echten Limits.
"""
Shadow Portfolio — KongTradeBot
================================
Simuliert das gesamte Trading-System mit virtuellem Geld
parallel zum echten Portfolio.

Unbegrenztes virtuelles Kapital — kein Blocking, kein Skipping.
Alle Signale werden als virtuelle Trades erfasst.
Tägliche Auswertung: was hätten wir verdient?

Kein echtes Geld. Nur Lernen.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(
    "polymarket_bot.shadow_portfolio")

SHADOW_FILE = Path(
    "/root/KongTradeBot/data/shadow_portfolio.json")
SHADOW_FILE.parent.mkdir(exist_ok=True)

VIRTUAL_START_CAPITAL = 999_999.0


@dataclass
class VirtualPosition:
    market_id: str
    question: str
    outcome: str          # YES / NO
    entry_price: float
    shares: float
    invested_usdc: float
    entry_time: str
    strategy: str         # COPY / WEATHER / COMBINED
    signal_score: int     # 0-100
    wallet_alias: Optional[str] = None
    city: str = ""
    status: str = "OPEN"  # OPEN / WON / LOST
    exit_price: float = 0.0
    pnl: float = 0.0
    exit_time: str = ""


class ShadowPortfolio:
    def __init__(self, path=None):
        global SHADOW_FILE
        if path:
            SHADOW_FILE = Path(path) if not Path(path).is_absolute() else Path(path)
            if not SHADOW_FILE.is_absolute():
                SHADOW_FILE = Path("/root/KongTradeBot") / path
        self.data = self._load()

    def _load(self) -> dict:
        if SHADOW_FILE.exists():
            try:
                d = json.loads(SHADOW_FILE.read_text())
                # Upgrade: reset depleted capital to unlimited
                if d.get("current_capital", 0) < 1000:
                    d["current_capital"] = VIRTUAL_START_CAPITAL
                    d["start_capital"] = VIRTUAL_START_CAPITAL
                return d
            except:
                pass
        return {
            "start_capital": VIRTUAL_START_CAPITAL,
            "current_capital": VIRTUAL_START_CAPITAL,
            "positions": [],
            "closed_positions": [],
            "stats": {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0
            },
            "created": datetime.now(
                timezone.utc).isoformat()
        }

    def _save(self):
        SHADOW_FILE.write_text(
            json.dumps(self.data, indent=2))

    def open_position(
            self,
            market_id: str,
            question: str,
            outcome: str,
            entry_price: float,
            invested_usdc: float,
            strategy: str,
            signal_score: int = 0,
            wallet_alias: str = None,
            city: str = "",
            end_date: str = "") -> bool:
        """Öffnet virtuelle Position. Kein Kapital-Limit im Shadow-Mode."""
        # Duplikat-Check: market_id bereits offen?
        if any(p.get("market_id") == market_id and p.get("status") == "OPEN"
               for p in self.data["positions"]):
            logger.info(f"[Shadow] SKIP Duplikat: {city or question[:30]} bereits im Portfolio")
            return False

        shares = round(
            invested_usdc / max(entry_price, 0.001), 4)

        pos = {
            "market_id": market_id,
            "question": question[:60],
            "outcome": outcome,
            "entry_price": entry_price,
            "shares": shares,
            "invested_usdc": invested_usdc,
            "entry_time": datetime.now(
                timezone.utc).isoformat(),
            "strategy": strategy,
            "signal_score": signal_score,
            "wallet_alias": wallet_alias,
            "city": city,
            "closes_at": f"{end_date}T23:59:00Z" if end_date else "",
            "status": "OPEN",
            "pnl": 0.0
        }

        self.data["positions"].append(pos)
        self.data["stats"]["total_trades"] += 1
        self._save()

        logger.info(
            f"[Shadow] 📝 VIRTUAL BUY: "
            f"{question[:40]} | "
            f"{outcome} @ {entry_price:.3f} | "
            f"${invested_usdc:.2f} | "
            f"Score: {signal_score}/100 | "
            f"Strategie: {strategy}")
        return True

    def resolve_position(
            self,
            market_id: str,
            winning_outcome: str,
            resolution_price: float = 1.0):
        """Löst offene Position auf."""
        resolved = False
        for pos in self.data["positions"]:
            if pos["market_id"] != market_id:
                continue
            if pos["status"] != "OPEN":
                continue

            won = pos["outcome"] == winning_outcome

            if won:
                pnl = (pos["shares"] *
                       resolution_price -
                       pos["invested_usdc"])
                self.data["stats"]["wins"] += 1
            else:
                pnl = -pos["invested_usdc"]
                self.data["stats"]["losses"] += 1

            pos["status"] = "WON" if won else "LOST"
            pos["pnl"] = round(pnl, 2)
            pos["exit_time"] = datetime.now(
                timezone.utc).isoformat()

            self.data["stats"]["total_pnl"] += pnl
            self.data["current_capital"] += \
                pos["invested_usdc"] + pnl

            if pnl > self.data["stats"]["best_trade"]:
                self.data["stats"]["best_trade"] = pnl
            if pnl < self.data["stats"]["worst_trade"]:
                self.data["stats"]["worst_trade"] = pnl

            self.data["closed_positions"].append(pos)
            self.data["positions"].remove(pos)
            resolved = True

            virtual_total = (
                self.data["stats"]["total_pnl"])

            logger.info(
                f"[Shadow] {'✅' if won else '❌'} "
                f"VIRTUAL RESOLVED: "
                f"{pos['question'][:40]} | "
                f"{'WON' if won else 'LOST'} | "
                f"P&L: ${pnl:+.2f} | "
                f"Virtual P&L Total: ${virtual_total:.2f}")
            break

        if resolved:
            self._save()
        return resolved

    def resolve_closed_markets(self) -> int:
        """
        Löst abgeschlossene Shadow-Positionen auf.

        Ansatz: Gamma-API liefert geschlossene Märkte seitenweise.
        Wir bauen ein Lookup-Dict {conditionId → winner} aus den ersten
        N Seiten und gleichen unsere offenen market_ids dagegen ab.

        Hintergrund: CLOB API = 403, data-api/gamma-api ignorieren beide
        den conditionId-Filter vom Server-IP. Pagination ist der
        einzige zuverlässige Weg für per-Markt-Resolution.
        """
        import urllib.request
        import json as _json

        GAMMA_API = "https://gamma-api.polymarket.com"
        resolved_total = 0

        # Unique offene market_ids als Such-Set
        open_mids = {
            p["market_id"] for p in self.data["positions"]
            if p.get("status") == "OPEN" and p.get("market_id")
        }
        if not open_mids:
            return 0

        logger.info(
            f"[Shadow] Resolution-Check: {len(open_mids)} unique Märkte, "
            f"scanne geschlossene Gamma-Märkte...")

        # Pagination: geschlossene Märkte durchsuchen
        # Aufhören wenn alle unsere IDs gefunden oder 50 Seiten durch
        winner_map: dict = {}  # conditionId → winning_outcome (upper)
        offset = 0
        max_pages = 50

        for page in range(max_pages):
            url = (f"{GAMMA_API}/markets"
                   f"?closed=true&limit=100&offset={offset}")
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    batch = _json.loads(r.read())
            except Exception as e:
                logger.warning(
                    f"[Shadow] Gamma-API Fehler (Seite {page}): {e}")
                break

            if not batch:
                break

            for mkt in batch:
                cid = mkt.get("conditionId", "")
                if cid not in open_mids:
                    continue
                # Gewinner aus outcomePrices (["1.0","0.0"] → YES)
                prices = mkt.get("outcomePrices", [])
                outcomes = mkt.get("outcomes", ["Yes", "No"])
                try:
                    max_idx = max(
                        range(len(prices)),
                        key=lambda i: float(prices[i]))
                    winner = outcomes[max_idx].upper()
                    winner_map[cid] = winner
                except Exception:
                    pass

            offset += 100

            # Alle unsere IDs gefunden?
            if open_mids.issubset(winner_map.keys()):
                logger.info(
                    f"[Shadow] Alle {len(open_mids)} Märkte gefunden "
                    f"nach {page + 1} Seiten.")
                break

        if not winner_map:
            logger.info("[Shadow] Keine aufgelösten Märkte gefunden.")
            return 0

        logger.info(
            f"[Shadow] {len(winner_map)} aufgelöste Märkte gefunden "
            f"(von {len(open_mids)} gesuchten)")

        # Positionen auflösen
        for mid, winning_outcome in winner_map.items():
            still_open = [
                p for p in self.data["positions"]
                if p.get("market_id") == mid
                and p.get("status") == "OPEN"
            ]
            for pos in still_open:
                won = pos.get("outcome", "").upper() == winning_outcome
                invested = float(pos.get("invested_usdc", 0))
                shares   = float(pos.get("shares", 0))
                pnl = round(
                    (shares - invested) if won else -invested, 2)

                pos["status"]    = "WON" if won else "LOST"
                pos["pnl"]       = pnl
                pos["exit_time"] = datetime.now(timezone.utc).isoformat()

                self.data["stats"]["total_pnl"] = round(
                    self.data["stats"].get("total_pnl", 0) + pnl, 4)
                if won:
                    self.data["stats"]["wins"] = (
                        self.data["stats"].get("wins", 0) + 1)
                else:
                    self.data["stats"]["losses"] = (
                        self.data["stats"].get("losses", 0) + 1)

                self.data["closed_positions"].append(pos)
                resolved_total += 1
                logger.info(
                    f"[Shadow] {'✅' if won else '❌'} "
                    f"{pos.get('city') or pos.get('question','?')[:30]} "
                    f"{pos.get('outcome','')} "
                    f"| {'WON' if won else 'LOST'} | PnL: ${pnl:+.2f}")

            # Aufgelöste aus offenen Positionen entfernen
            self.data["positions"] = [
                p for p in self.data["positions"]
                if not (p.get("market_id") == mid
                        and p.get("status") in ("WON", "LOST"))
            ]

        if resolved_total > 0:
            self._save()
            logger.info(
                f"[Shadow] {resolved_total} Positionen aufgelöst.")
        return resolved_total

    def get_summary(self) -> dict:
        """Tägliche Zusammenfassung."""
        stats = self.data["stats"]
        virtual_pnl = stats["total_pnl"]

        win_rate = (
            stats["wins"] /
            max(stats["wins"] + stats["losses"], 1))

        return {
            "virtual_pnl":     round(virtual_pnl, 2),
            "total_trades":    stats["total_trades"],
            "win_rate":        round(win_rate, 3),
            "open_positions":  len(self.data["positions"]),
            "best_trade":      stats["best_trade"],
            "worst_trade":     stats["worst_trade"],
            # kept for compat
            "virtual_portfolio": round(VIRTUAL_START_CAPITAL + virtual_pnl, 2),
            "real_portfolio":    0.0,
            "difference":        round(virtual_pnl, 2),
        }

    def print_dashboard(self):
        s = self.get_summary()
        print("\n" + "="*55)
        print("SHADOW PORTFOLIO STATUS")
        print("="*55)
        print(f"Virtuelle P&L:  ${s['virtual_pnl']:+,.2f}")
        print(f"\nTrades:   {s['total_trades']}")
        print(f"Win Rate: {s['win_rate']:.1%}")
        print(f"Offen:    {s['open_positions']}")
        print(f"Best:     ${s['best_trade']:+.2f}")
        print(f"Worst:    ${s['worst_trade']:+.2f}")
        print("="*55)
