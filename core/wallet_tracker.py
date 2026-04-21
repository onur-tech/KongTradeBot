"""
Wallet Tracker — KongTradeBot
==============================
Verfolgt per-Wallet Performance in Echtzeit.
Speichert in data/wallet_performance.json.

Kategorien:
  STAR      — Win-Rate ≥ 60% und PnL ≥ 0
  RELIABLE  — Win-Rate ≥ 50% und PnL ≥ 0
  NEUTRAL   — noch keine starke Tendenz
  DECAYING  — Win-Rate < 50% in letzten 10 Trades
  TOXIC     — Win-Rate < 35% oder stark negatives PnL
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("polymarket_bot.wallet_tracker")

WALLET_PERF_FILE = Path("/root/KongTradeBot/data/wallet_performance.json")
WALLET_PERF_FILE.parent.mkdir(exist_ok=True)


class WalletTracker:
    def __init__(self, path: Optional[str] = None):
        self.path = Path(path) if path else WALLET_PERF_FILE
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {"wallets": {}, "updated": ""}

    def _save(self):
        self.data["updated"] = datetime.now(timezone.utc).isoformat()
        self.path.write_text(json.dumps(self.data, indent=2))

    def record_trade(
            self,
            wallet: str,
            market_id: str,
            outcome: str,
            won: bool,
            pnl: float,
            size_usdc: float = 0.0,
            strategy: str = "COPY"):
        """Zeichnet abgeschlossenen Trade auf und aktualisiert Statistiken."""
        alias = wallet[:10]
        if wallet not in self.data["wallets"]:
            self.data["wallets"][wallet] = {
                "alias": alias,
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "total_pnl": 0.0,
                "total_volume": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "recent_outcomes": [],   # letzte 20: True/False
                "category": "NEUTRAL",
                "last_trade": "",
            }

        w = self.data["wallets"][wallet]
        w["total_trades"] += 1
        w["total_pnl"] = round(w["total_pnl"] + pnl, 4)
        w["total_volume"] = round(w["total_volume"] + size_usdc, 4)
        w["last_trade"] = datetime.now(timezone.utc).isoformat()

        if won:
            w["wins"] += 1
            if pnl > w["best_trade"]:
                w["best_trade"] = round(pnl, 2)
        else:
            w["losses"] += 1
            if pnl < w["worst_trade"]:
                w["worst_trade"] = round(pnl, 2)

        # Letzte 20 Outcomes für Decay-Detection
        w["recent_outcomes"].append(won)
        if len(w["recent_outcomes"]) > 20:
            w["recent_outcomes"] = w["recent_outcomes"][-20:]

        w["category"] = self._classify(w)

        logger.info(
            f"[WalletTracker] {alias} | "
            f"{'WIN' if won else 'LOSS'} | "
            f"PnL: ${pnl:+.2f} | "
            f"Total: {w['total_trades']} trades | "
            f"WR: {w['wins']/max(w['total_trades'],1):.0%} | "
            f"Cat: {w['category']}")

        self._save()

    def _classify(self, w: dict) -> str:
        """Kategorisiert Wallet basierend auf Statistiken."""
        total = w["total_trades"]
        if total < 5:
            return "NEUTRAL"

        wr = w["wins"] / total
        pnl = w["total_pnl"]

        # Letzten 10 Trades für Decay
        recent = w["recent_outcomes"][-10:]
        recent_wr = sum(1 for x in recent if x) / max(len(recent), 1)

        if recent_wr < 0.35 or (pnl < -500 and wr < 0.45):
            return "TOXIC"
        if recent_wr < 0.50 and len(recent) >= 5:
            return "DECAYING"
        if wr >= 0.60 and pnl >= 0:
            return "STAR"
        if wr >= 0.50 and pnl >= 0:
            return "RELIABLE"
        return "NEUTRAL"

    def get_decay_candidates(self) -> list:
        """Gibt Wallets zurück die DECAYING oder TOXIC sind."""
        result = []
        for wallet, w in self.data["wallets"].items():
            if w["category"] in ("DECAYING", "TOXIC"):
                wr = w["wins"] / max(w["total_trades"], 1)
                recent = w["recent_outcomes"][-10:]
                recent_wr = sum(1 for x in recent if x) / max(len(recent), 1)
                result.append({
                    "wallet": wallet,
                    "alias": w["alias"],
                    "category": w["category"],
                    "total_trades": w["total_trades"],
                    "win_rate": round(wr, 3),
                    "recent_win_rate": round(recent_wr, 3),
                    "total_pnl": w["total_pnl"],
                    "last_trade": w["last_trade"],
                })
        result.sort(key=lambda x: x["total_pnl"])
        return result

    def get_stats(self, wallet: str) -> Optional[dict]:
        """Gibt Statistiken für eine spezifische Wallet zurück."""
        w = self.data["wallets"].get(wallet)
        if not w:
            return None
        total = w["total_trades"]
        wr = w["wins"] / max(total, 1)
        return {
            "wallet": wallet,
            "alias": w["alias"],
            "total_trades": total,
            "win_rate": round(wr, 3),
            "total_pnl": round(w["total_pnl"], 2),
            "total_volume": round(w["total_volume"], 2),
            "best_trade": w["best_trade"],
            "worst_trade": w["worst_trade"],
            "category": w["category"],
            "last_trade": w["last_trade"],
        }

    def print_report(self):
        """Gibt kompakten Performance-Report aus."""
        wallets = self.data["wallets"]
        if not wallets:
            print("Keine Wallet-Daten vorhanden.")
            return

        print("\n" + "=" * 65)
        print("WALLET PERFORMANCE REPORT")
        print("=" * 65)
        print(f"{'Alias':<14} {'Trades':>6} {'WR':>6} {'PnL':>10} {'Cat':<10}")
        print("-" * 65)

        rows = []
        for wallet, w in wallets.items():
            total = w["total_trades"]
            wr = w["wins"] / max(total, 1)
            rows.append((wallet, w, total, wr))

        rows.sort(key=lambda x: x[1]["total_pnl"], reverse=True)

        for wallet, w, total, wr in rows:
            alias = w.get("alias", wallet[:10])
            pnl = w["total_pnl"]
            cat = w["category"]
            print(f"{alias:<14} {total:>6} {wr:>5.0%} {pnl:>+10.2f} {cat:<10}")

        print("=" * 65)
