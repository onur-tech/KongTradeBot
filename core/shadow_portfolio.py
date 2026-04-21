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
    def __init__(self):
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
            city: str = "") -> bool:
        """Öffnet virtuelle Position. Kein Kapital-Limit im Shadow-Mode."""

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
