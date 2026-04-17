"""
performance_tracker.py — Performance-Kontrolle + Steuer-Tracker

ZWEI AUFGABEN IN EINEM MODUL:

1. PERFORMANCE-KONTROLLE (on the fly lernen)
   - Jeden Trade tracken: Entry, Exit, PnL
   - Win Rate pro kopierter Wallet
   - Welche Markt-Typen performen am besten?
   - Automatische Erkennung wenn eine Strategie schlechter wird
   - Empfehlungen: welche Wallets weiter kopieren, welche stoppen?

2. STEUER-TRACKER (Finanzamt)
   - Jede Transaktion mit Timestamp, Asset, USDC-Betrag, PnL
   - CSV-Export kompatibel mit Blockpit / CoinTracking
   - Jahresauswertung: Gesamtgewinn, Gesamtverlust, Netto
   - Trennung: realized PnL (aufgelöste Märkte) vs unrealized

VERWENDUNG:
    tracker = PerformanceTracker()
    tracker.record_entry(order, result)         # Bei jedem Trade
    tracker.record_exit(order_id, pnl_usdc)     # Bei Markt-Auflösung
    tracker.export_tax_csv("steuer_2026.csv")   # Für Finanzamt
    report = tracker.get_performance_report()   # Für Bot-Optimierung
"""

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from utils.logger import get_logger

logger = get_logger("tracker")


# ============================================================
# DATENSTRUKTUREN
# ============================================================

@dataclass
class TradeRecord:
    """Ein vollständiger Trade von Entry bis Exit."""

    # Identifikation
    trade_id: str
    source_wallet: str          # Welche Wallet wurde kopiert?

    # Markt
    market_question: str
    outcome: str                # "Yes" / "No"
    market_id: str

    # Entry
    entry_price: float
    entry_size_usdc: float
    entry_shares: float
    entry_time: str             # ISO 8601

    # Exit (wird befüllt wenn Markt sich auflöst)
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    resolved_outcome: Optional[str] = None  # Was war das echte Ergebnis?

    # PnL
    pnl_usdc: Optional[float] = None
    pnl_percent: Optional[float] = None
    is_win: Optional[bool] = None

    # Status
    status: str = "OPEN"        # OPEN → RESOLVED oder EXPIRED

    # Meta
    dry_run: bool = True
    market_category: str = ""   # "crypto", "politics", "sports", etc.

    @property
    def is_closed(self) -> bool:
        return self.status in ("RESOLVED", "EXPIRED")

    def close(self, pnl_usdc: float, exit_price: float = None, resolved_outcome: str = None):
        """Schließt den Trade und berechnet PnL."""
        self.pnl_usdc = pnl_usdc
        self.exit_time = datetime.now(timezone.utc).isoformat()
        self.exit_price = exit_price or (1.0 if pnl_usdc > 0 else 0.0)
        self.resolved_outcome = resolved_outcome
        self.is_win = pnl_usdc > 0
        self.pnl_percent = (pnl_usdc / self.entry_size_usdc * 100) if self.entry_size_usdc > 0 else 0
        self.status = "RESOLVED"

    def to_tax_row(self) -> dict:
        """Format für Steuer-CSV (Blockpit/CoinTracking kompatibel)."""
        return {
            "Datum": self.entry_time[:10],
            "Uhrzeit": self.entry_time[11:19],
            "Art": "KAUF" if self.entry_price < 1 else "VERKAUF",
            "Asset": "USDC (Polymarket)",
            "Markt": self.market_question[:80],
            "Outcome": self.outcome,
            "Einsatz_USD": f"{self.entry_size_usdc:.4f}",
            "Kurs_USD": f"{self.entry_price:.4f}",
            "Ergebnis_USD": f"{self.pnl_usdc:.4f}" if self.pnl_usdc is not None else "",
            "Gewinn_Verlust_USD": f"{self.pnl_usdc:.4f}" if self.pnl_usdc is not None else "offen",
            "Status": self.status,
            "Source_Wallet": self.source_wallet[:20],
            "Trade_ID": self.trade_id[:16],
            "Dry_Run": str(self.dry_run),
        }


@dataclass
class WalletStats:
    """Performance-Statistik für eine kopierte Wallet."""
    wallet: str
    trades_total: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    trades_open: int = 0
    total_invested_usdc: float = 0.0
    total_pnl_usdc: float = 0.0

    # Letzte 20 Trades für Trend-Erkennung
    recent_pnl: List[float] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        closed = self.trades_won + self.trades_lost
        return self.trades_won / closed if closed > 0 else 0.0

    @property
    def recent_win_rate(self) -> float:
        recent = self.recent_pnl[-20:]
        if not recent:
            return 0.0
        return sum(1 for p in recent if p > 0) / len(recent)

    @property
    def roi_percent(self) -> float:
        if self.total_invested_usdc == 0:
            return 0.0
        return (self.total_pnl_usdc / self.total_invested_usdc) * 100

    @property
    def recommendation(self) -> str:
        """Automatische Empfehlung basierend auf Performance."""
        closed = self.trades_won + self.trades_lost
        if closed < 10:
            return "⏳ Zu wenige Trades für Bewertung"
        if self.recent_win_rate < 0.40:
            return "🛑 STOPPEN — Win Rate unter 40% in letzten 20 Trades"
        if self.recent_win_rate < 0.50:
            return "⚠️  BEOBACHTEN — Win Rate schwächelt"
        if self.win_rate >= 0.60 and self.roi_percent > 0:
            return "✅ WEITER KOPIEREN — Gute Performance"
        return "🔄 NEUTRAL — Weiter beobachten"


# ============================================================
# HAUPTKLASSE
# ============================================================

class PerformanceTracker:
    """
    Trackt alle Trades für Performance-Analyse und Steuer-Dokumentation.

    Speichert Daten in JSON (Wiederherstellung nach Neustart)
    und exportiert CSV für das Finanzamt.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self._trades: Dict[str, TradeRecord] = {}
        self._wallet_stats: Dict[str, WalletStats] = defaultdict(
            lambda: WalletStats(wallet="unknown")
        )

        # Aus Datei laden (Bot-Neustart überlebt)
        self._load_from_disk()
        logger.info(f"Performance Tracker gestartet | {len(self._trades)} Trades geladen")

    # --------------------------------------------------------
    # TRADE LIFECYCLE
    # --------------------------------------------------------

    def record_entry(
        self,
        trade_id: str,
        source_wallet: str,
        market_question: str,
        outcome: str,
        market_id: str,
        entry_price: float,
        entry_size_usdc: float,
        dry_run: bool = True,
        market_category: str = "",
    ) -> TradeRecord:
        """Neuer Trade wird geöffnet."""
        trade = TradeRecord(
            trade_id=trade_id,
            source_wallet=source_wallet,
            market_question=market_question,
            outcome=outcome,
            market_id=market_id,
            entry_price=entry_price,
            entry_size_usdc=entry_size_usdc,
            entry_shares=entry_size_usdc / entry_price if entry_price > 0 else 0,
            entry_time=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
            market_category=market_category,
        )

        self._trades[trade_id] = trade

        # Wallet Stats aktualisieren
        stats = self._get_wallet_stats(source_wallet)
        stats.trades_total += 1
        stats.trades_open += 1
        stats.total_invested_usdc += entry_size_usdc

        self._save_to_disk()

        mode = "[DRY]" if dry_run else "[LIVE]"
        logger.info(
            f"📝 Trade geöffnet {mode}: {outcome} @ ${entry_price:.3f} | "
            f"${entry_size_usdc:.2f} | {market_question[:50]}"
        )

        return trade

    def record_exit(
        self,
        trade_id: str,
        pnl_usdc: float,
        resolved_outcome: str = None,
    ) -> Optional[TradeRecord]:
        """Markt aufgelöst — Trade schließen und PnL erfassen."""
        trade = self._trades.get(trade_id)
        if not trade:
            logger.warning(f"Trade {trade_id} nicht gefunden")
            return None

        if trade.is_closed:
            logger.warning(f"Trade {trade_id} bereits geschlossen")
            return trade

        trade.close(pnl_usdc, resolved_outcome=resolved_outcome)

        # Wallet Stats aktualisieren
        stats = self._get_wallet_stats(trade.source_wallet)
        stats.trades_open = max(0, stats.trades_open - 1)
        stats.total_pnl_usdc += pnl_usdc
        stats.recent_pnl.append(pnl_usdc)
        if len(stats.recent_pnl) > 50:
            stats.recent_pnl = stats.recent_pnl[-50:]

        if pnl_usdc > 0:
            stats.trades_won += 1
        else:
            stats.trades_lost += 1

        self._save_to_disk()

        emoji = "✅" if pnl_usdc > 0 else "❌"
        logger.info(
            f"{emoji} Trade geschlossen: {trade.outcome} | "
            f"PnL: {pnl_usdc:+.2f} USD ({trade.pnl_percent:+.1f}%) | "
            f"{trade.market_question[:50]}"
        )

        return trade

    # --------------------------------------------------------
    # PERFORMANCE REPORT
    # --------------------------------------------------------

    def get_performance_report(self) -> dict:
        """
        Vollständiger Performance-Report für Bot-Optimierung.

        Enthält:
        - Gesamtperformance
        - Per-Wallet Analyse mit Empfehlungen
        - Beste/schlechteste Markt-Kategorien
        - Trend: wird es besser oder schlechter?
        """
        closed_trades = [t for t in self._trades.values() if t.is_closed]
        open_trades = [t for t in self._trades.values() if not t.is_closed]

        if not closed_trades:
            return {"message": "Noch keine abgeschlossenen Trades"}

        total_pnl = sum(t.pnl_usdc for t in closed_trades)
        total_invested = sum(t.entry_size_usdc for t in closed_trades)
        wins = [t for t in closed_trades if t.is_win]
        losses = [t for t in closed_trades if not t.is_win]

        # Durchschnittlicher Gewinn vs. Verlust (Asymmetrie)
        avg_win = sum(t.pnl_usdc for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl_usdc for t in losses) / len(losses) if losses else 0

        # Kategorien-Analyse
        cat_stats = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
        for t in closed_trades:
            cat = t.market_category or "unknown"
            cat_stats[cat]["trades"] += 1
            cat_stats[cat]["pnl"] += t.pnl_usdc
            if t.is_win:
                cat_stats[cat]["wins"] += 1

        # Wallet-Empfehlungen
        wallet_recs = {}
        for wallet, stats in self._wallet_stats.items():
            wallet_recs[wallet[:16] + "..."] = {
                "win_rate": f"{stats.win_rate:.0%}",
                "recent_win_rate": f"{stats.recent_win_rate:.0%}",
                "roi": f"{stats.roi_percent:+.1f}%",
                "trades": stats.trades_total,
                "pnl": f"${stats.total_pnl_usdc:+.2f}",
                "empfehlung": stats.recommendation,
            }

        # Trend: letzte 10 vs. vorletzte 10 Trades
        if len(closed_trades) >= 20:
            recent_10 = sorted(closed_trades, key=lambda t: t.entry_time)[-10:]
            older_10 = sorted(closed_trades, key=lambda t: t.entry_time)[-20:-10]
            recent_wr = sum(1 for t in recent_10 if t.is_win) / 10
            older_wr = sum(1 for t in older_10 if t.is_win) / 10
            trend = "📈 Verbessernd" if recent_wr > older_wr else "📉 Verschlechternd"
        else:
            trend = "⏳ Noch zu wenige Daten"

        return {
            "gesamt": {
                "trades_closed": len(closed_trades),
                "trades_open": len(open_trades),
                "win_rate": f"{len(wins)/len(closed_trades):.0%}",
                "total_pnl_usdc": f"${total_pnl:+.2f}",
                "total_invested_usdc": f"${total_invested:.2f}",
                "roi": f"{(total_pnl/total_invested*100):+.1f}%" if total_invested > 0 else "N/A",
                "avg_gewinn": f"${avg_win:+.2f}",
                "avg_verlust": f"${avg_loss:+.2f}",
                "asymmetrie": f"{abs(avg_win/avg_loss):.1f}x" if avg_loss != 0 else "N/A",
            },
            "trend": trend,
            "wallets": wallet_recs,
            "kategorien": {
                cat: {
                    "trades": s["trades"],
                    "win_rate": f"{s['wins']/s['trades']:.0%}" if s["trades"] > 0 else "N/A",
                    "pnl": f"${s['pnl']:+.2f}",
                }
                for cat, s in cat_stats.items()
            },
        }

    def print_performance_report(self):
        """Gibt lesbaren Report aus."""
        report = self.get_performance_report()
        if "message" in report:
            logger.info(report["message"])
            return

        logger.info("\n" + "=" * 60)
        logger.info("📊 PERFORMANCE REPORT")
        logger.info("=" * 60)

        g = report["gesamt"]
        logger.info(f"Trades:      {g['trades_closed']} closed, {g['trades_open']} open")
        logger.info(f"Win Rate:    {g['win_rate']}")
        logger.info(f"Total PnL:   {g['total_pnl_usdc']}")
        logger.info(f"ROI:         {g['roi']}")
        logger.info(f"Avg Gewinn:  {g['avg_gewinn']} | Avg Verlust: {g['avg_verlust']}")
        logger.info(f"Asymmetrie:  {g['asymmetrie']}")
        logger.info(f"Trend:       {report['trend']}")

        logger.info("\n--- WALLETS ---")
        for wallet, stats in report["wallets"].items():
            logger.info(f"{wallet}")
            logger.info(f"  Win Rate: {stats['win_rate']} (recent: {stats['recent_win_rate']})")
            logger.info(f"  ROI: {stats['roi']} | PnL: {stats['pnl']}")
            logger.info(f"  → {stats['empfehlung']}")

        logger.info("=" * 60)

    # --------------------------------------------------------
    # STEUER-EXPORT
    # --------------------------------------------------------

    def export_tax_csv(self, filename: str = None, year: int = None) -> str:
        """
        Exportiert alle Trades als CSV für das Finanzamt.

        Kompatibel mit Blockpit und CoinTracking Import-Format.
        Enthält: Datum, Art, Asset, Betrag, Gewinn/Verlust

        Args:
            filename: Dateiname (default: steuer_{jahr}.csv)
            year: Nur Trades dieses Jahres (default: alle)
        """
        if filename is None:
            jahr = year or datetime.now().year
            filename = f"steuer_{jahr}.csv"

        filepath = self.data_dir / filename

        trades_to_export = list(self._trades.values())

        if year:
            trades_to_export = [
                t for t in trades_to_export
                if t.entry_time.startswith(str(year))
            ]

        # Nur closed trades für Steuer relevant (realized PnL)
        # Open trades werden als Hinweis aufgeführt
        closed = [t for t in trades_to_export if t.is_closed]
        open_trades = [t for t in trades_to_export if not t.is_closed]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            if not closed:
                f.write("Keine abgeschlossenen Trades\n")
                logger.info(f"Steuer-CSV: Keine Trades ({filepath})")
                return str(filepath)

            writer = csv.DictWriter(f, fieldnames=closed[0].to_tax_row().keys())
            writer.writeheader()

            total_pnl = 0.0
            for trade in sorted(closed, key=lambda t: t.entry_time):
                writer.writerow(trade.to_tax_row())
                total_pnl += trade.pnl_usdc or 0

            # Zusammenfassung am Ende
            f.write("\n")
            f.write(f"ZUSAMMENFASSUNG STEUERJAHR {year or 'GESAMT'}\n")
            f.write(f"Anzahl Trades (realisiert),{len(closed)}\n")
            f.write(f"Anzahl Trades (offen),{len(open_trades)}\n")
            f.write(f"Gesamtgewinn_USD,{sum(t.pnl_usdc for t in closed if t.is_win):.4f}\n")
            f.write(f"Gesamtverlust_USD,{sum(t.pnl_usdc for t in closed if not t.is_win):.4f}\n")
            f.write(f"Netto_PnL_USD,{total_pnl:.4f}\n")
            f.write(f"Hinweis,Bitte Steuerberater konsultieren fuer korrekte steuerliche Einordnung\n")
            f.write(f"Hinweis,Polymarket Gewinne koennen als sonstige Einkunfte (§22 EStG) steuerpflichtig sein\n")
            f.write(f"Hinweis,DAC8 ab 2026: Transaktionen werden automatisch an Finanzamt gemeldet\n")

        logger.info(
            f"📄 Steuer-CSV exportiert: {filepath} | "
            f"{len(closed)} Trades | Netto: ${total_pnl:+.2f} USD"
        )
        return str(filepath)

    def get_yearly_summary(self, year: int = None) -> dict:
        """Jahres-Zusammenfassung für Steuererklärung."""
        year = year or datetime.now().year
        year_str = str(year)

        closed = [
            t for t in self._trades.values()
            if t.is_closed and t.entry_time.startswith(year_str)
        ]

        if not closed:
            return {"year": year, "message": "Keine abgeschlossenen Trades"}

        gewinne = [t for t in closed if t.is_win]
        verluste = [t for t in closed if not t.is_win]
        total_gewinn = sum(t.pnl_usdc for t in gewinne)
        total_verlust = sum(t.pnl_usdc for t in verluste)
        netto = total_gewinn + total_verlust

        return {
            "steuerjahr": year,
            "trades_gesamt": len(closed),
            "gewinn_trades": len(gewinne),
            "verlust_trades": len(verluste),
            "gesamtgewinn_usd": round(total_gewinn, 2),
            "gesamtverlust_usd": round(total_verlust, 2),
            "netto_pnl_usd": round(netto, 2),
            "steuerpflichtig": netto > 1000,
            "freigrenze_usd": 1000,
            "hinweis": (
                "⚠️  Über €1.000 Freigrenze — Steuerpflicht wahrscheinlich"
                if netto > 1000
                else "✅ Unter €1.000 Freigrenze (Stand 2026)"
            ),
        }

    # --------------------------------------------------------
    # PERSISTENZ
    # --------------------------------------------------------

    def _save_to_disk(self):
        """Speichert alle Trades in JSON — überlebt Bot-Neustart."""
        try:
            trades_file = self.data_dir / "trades.json"
            data = {
                trade_id: asdict(trade)
                for trade_id, trade in self._trades.items()
            }
            with open(trades_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}")

    def _load_from_disk(self):
        """Lädt Trades aus JSON beim Start."""
        trades_file = self.data_dir / "trades.json"
        if not trades_file.exists():
            return

        try:
            with open(trades_file) as f:
                data = json.load(f)

            for trade_id, trade_data in data.items():
                # recent_pnl ist in WalletStats, nicht in TradeRecord
                trade_data.pop("recent_pnl", None)
                self._trades[trade_id] = TradeRecord(**trade_data)

            # Wallet Stats neu berechnen aus geladenen Trades
            self._rebuild_wallet_stats()
            logger.info(f"Trades geladen: {len(self._trades)} aus {trades_file}")

        except Exception as e:
            logger.error(f"Laden fehlgeschlagen: {e}")

    def _rebuild_wallet_stats(self):
        """Berechnet Wallet-Stats aus allen geladenen Trades neu."""
        self._wallet_stats = defaultdict(lambda: WalletStats(wallet="unknown"))
        for trade in self._trades.values():
            stats = self._get_wallet_stats(trade.source_wallet)
            stats.total_invested_usdc += trade.entry_size_usdc
            stats.trades_total += 1
            if trade.is_closed:
                stats.total_pnl_usdc += trade.pnl_usdc or 0
                stats.recent_pnl.append(trade.pnl_usdc or 0)
                if trade.is_win:
                    stats.trades_won += 1
                else:
                    stats.trades_lost += 1
            else:
                stats.trades_open += 1

    def _get_wallet_stats(self, wallet: str) -> WalletStats:
        if wallet not in self._wallet_stats:
            self._wallet_stats[wallet] = WalletStats(wallet=wallet)
        return self._wallet_stats[wallet]
