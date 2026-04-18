"""
tax_archive.py — Steuer-Archiv für alle Trades

Exportiert alle Trades als CSV für den Steuerberater.
Format 1: Detailliertes deutsches Format (mit EUR-Umrechnung)
Format 2: Blockpit CSV-Import-Format

EUR/USD: tagesaktueller Kurs via Frankfurter API (ECB-Daten), kein API-Key nötig.
Rechtlicher Hinweis: Polymarket-Gewinne unterliegen in Deutschland
§ 22 Nr. 3 EStG (sonstige Einkünfte). Freigrenze: €256/Jahr.
DAC8-Meldepflicht ab 2026.
"""

import csv
import json
import os
from datetime import datetime
from typing import Optional, Dict
from urllib.request import urlopen
from urllib.error import URLError

from utils.logger import get_logger

logger = get_logger("tax")

TRADE_LOG_FILE    = "trades_archive.json"
TAX_CSV_FILE      = "steuer_export_{year}.csv"
BLOCKPIT_CSV_FILE = "blockpit_import_{year}.csv"


# ── EUR/USD Kurs-Abruf ────────────────────────────────────────────────────────

def _fetch_eur_usd_rates(start_date: str, end_date: str) -> Dict[str, float]:
    """
    Holt EUR/USD-Kurse für einen Datumsbereich via Frankfurter API (ECB-Daten).
    Gibt ein Dict zurück: {"2026-01-15": 0.9123, ...}
    Fällt auf einen festen Fallback-Kurs zurück wenn die API nicht erreichbar ist.
    """
    FALLBACK_RATE = 0.92  # Grober Fallback, wird im Export vermerkt

    try:
        url = f"https://api.frankfurter.app/{start_date}..{end_date}?from=USD&to=EUR"
        with urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        rates = {date: vals["EUR"] for date, vals in data.get("rates", {}).items()}
        if rates:
            logger.info(f"EUR/USD Kurse geladen: {len(rates)} Tage ({start_date} – {end_date})")
            return rates
    except URLError as e:
        logger.warning(f"Frankfurter API nicht erreichbar: {e}")
    except Exception as e:
        logger.warning(f"EUR/USD Abruf fehlgeschlagen: {e}")

    # Fallback: heutigen Kurs probieren
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=EUR"
        with urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        rate = data["rates"]["EUR"]
        today = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        logger.warning(f"Fallback: verwende heutigen Kurs {today}: 1 USD = {rate} EUR")
        return {"__fallback__": rate}
    except Exception:
        logger.warning(f"Kein EUR-Kurs verfügbar — verwende Fallback {FALLBACK_RATE}")
        return {"__fallback__": FALLBACK_RATE}


def _get_rate(rates: Dict[str, float], date: str) -> float:
    """Gibt den EUR/USD-Kurs für ein Datum zurück, nächsten bekannten als Fallback."""
    if date in rates:
        return rates[date]
    if "__fallback__" in rates:
        return rates["__fallback__"]
    # Nächsten verfügbaren Kurs suchen (ECB schließt an Wochenenden)
    for offset in range(1, 5):
        from datetime import timedelta
        dt = datetime.strptime(date, "%Y-%m-%d")
        for direction in [-1, 1]:
            candidate = (dt + timedelta(days=direction * offset)).strftime("%Y-%m-%d")
            if candidate in rates:
                return rates[candidate]
    return 0.92  # letzter Fallback


# ── Trade-Logging ─────────────────────────────────────────────────────────────

def log_trade(
    market_question: str,
    outcome: str,
    side: str,
    price: float,
    size_usdc: float,
    shares: float,
    source_wallet: str,
    tx_hash: str = "",
    category: str = "",
    is_dry_run: bool = True,
    market_id: str = "",
    token_id: str = "",
) -> None:
    """Loggt einen Trade ins persistente Archiv."""
    try:
        trades = _load_trades()

        trade = {
            "id":                  len(trades) + 1,
            "datum":               datetime.now().strftime("%Y-%m-%d"),
            "uhrzeit":             datetime.now().strftime("%H:%M:%S"),
            "markt":               market_question,
            "market_id":           market_id,
            "token_id":            token_id,
            "outcome":             outcome,
            "seite":               side,
            "preis_usdc":          round(price, 4),
            "einsatz_usdc":        round(size_usdc, 4),
            "shares":              round(shares, 4),
            "source_wallet":       source_wallet,
            "tx_hash":             tx_hash,
            "kategorie":           category,
            "modus":               "DRY-RUN" if is_dry_run else "LIVE",
            "ergebnis":            "",
            "gewinn_verlust_usdc": 0.0,
            "aufgeloest":          False,
        }

        trades.append(trade)
        _save_trades(trades)

    except Exception as e:
        logger.error(f"Trade archivieren fehlgeschlagen: {e}")


def resolve_trade(trade_id: int, won: bool, payout_usdc: float) -> None:
    """Aktualisiert einen Trade mit dem Ergebnis."""
    try:
        trades = _load_trades()
        for trade in trades:
            if trade.get("id") == trade_id:
                trade["aufgeloest"]          = True
                trade["ergebnis"]            = "GEWINN" if won else "VERLUST"
                trade["gewinn_verlust_usdc"] = round(payout_usdc - trade["einsatz_usdc"], 4)
                break
        _save_trades(trades)
        logger.info(f"Trade #{trade_id} aufgelöst: {'GEWINN' if won else 'VERLUST'} ${payout_usdc:.2f}")
    except Exception as e:
        logger.error(f"Trade auflösen fehlgeschlagen: {e}")


# ── Detaillierter Steuer-Export (mit EUR) ────────────────────────────────────

def export_tax_csv(year: Optional[int] = None) -> str:
    """
    Exportiert alle Trades als detailliertes Steuer-CSV mit EUR-Umrechnung.
    Zusätzlich wird eine Blockpit-kompatible CSV erstellt.
    """
    if year is None:
        year = datetime.now().year

    trades      = _load_trades()
    year_trades = [t for t in trades if t.get("datum", "").startswith(str(year))]

    if not year_trades:
        logger.warning(f"Keine Trades für {year} gefunden.")
        return ""

    # EUR/USD-Kurse für alle Trade-Daten holen
    dates      = sorted({t["datum"] for t in year_trades if t.get("datum")})
    start_date = dates[0]
    end_date   = dates[-1]
    eur_rates  = _fetch_eur_usd_rates(start_date, end_date)
    rate_src   = "ECB via frankfurter.app" if "__fallback__" not in eur_rates else "Fallback-Kurs (API nicht erreichbar)"

    # ── Detailliertes CSV ────────────────────────────────────────────────────
    filename = TAX_CSV_FILE.format(year=year)

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            "ID", "Datum", "Uhrzeit", "TX-Hash", "Markt", "Market-ID", "Outcome", "Seite",
            "Preis (USDC)", "Einsatz (USDC)", "Einsatz (EUR)", "Shares",
            "EUR/USD Kurs", "Kursquelle",
            "Gewinn/Verlust (USDC)", "Gewinn/Verlust (EUR)",
            "Source Wallet", "Kategorie", "Modus", "Ergebnis", "Aufgeloest",
        ])

        total_invested_usd = 0.0
        total_invested_eur = 0.0
        total_pnl_usd      = 0.0
        total_pnl_eur      = 0.0

        for t in year_trades:
            date       = t.get("datum", "")
            rate       = _get_rate(eur_rates, date)
            inv_usd    = float(t.get("einsatz_usdc", 0) or 0)
            pnl_usd    = float(t.get("gewinn_verlust_usdc", 0) or 0)
            inv_eur    = round(inv_usd * rate, 2)
            pnl_eur    = round(pnl_usd * rate, 2)

            writer.writerow([
                t.get("id", ""),
                date,
                t.get("uhrzeit", ""),
                t.get("tx_hash", ""),
                t.get("markt", ""),
                t.get("market_id", ""),
                t.get("outcome", ""),
                t.get("seite", ""),
                _fmt(t.get("preis_usdc", "")),
                _fmt(inv_usd),
                _fmt(inv_eur),
                _fmt(t.get("shares", "")),
                _fmt(rate),
                rate_src,
                _fmt(pnl_usd),
                _fmt(pnl_eur),
                t.get("source_wallet", ""),
                t.get("kategorie", ""),
                t.get("modus", ""),
                t.get("ergebnis", "offen"),
                "Ja" if t.get("aufgeloest") else "Nein",
            ])

            total_invested_usd += inv_usd
            total_invested_eur += inv_eur
            total_pnl_usd      += pnl_usd
            total_pnl_eur      += pnl_eur

        writer.writerow([])
        writer.writerow(["ZUSAMMENFASSUNG"])
        writer.writerow(["Anzahl Trades",            len(year_trades)])
        writer.writerow(["Gesamt Einsatz (USDC)",    _fmt(round(total_invested_usd, 2))])
        writer.writerow(["Gesamt Einsatz (EUR)",     _fmt(round(total_invested_eur, 2))])
        writer.writerow(["Gesamt P&L (USDC)",        _fmt(round(total_pnl_usd, 2))])
        writer.writerow(["Gesamt P&L (EUR)",         _fmt(round(total_pnl_eur, 2))])
        writer.writerow(["Kursquelle",               rate_src])
        writer.writerow(["Export-Datum",             datetime.now().strftime("%Y-%m-%d %H:%M")])
        writer.writerow(["Hinweis", "Gewinne aus Prediction Markets unterliegen §22 Nr.3 EStG. Freigrenze EUR 256/Jahr."])
        writer.writerow(["DAC8-Hinweis", "Meldepflicht für Krypto-Einkünfte ab 2026 beachten."])

    logger.info(f"Steuer-CSV exportiert: {filename} ({len(year_trades)} Trades)")

    # ── Blockpit-Export ──────────────────────────────────────────────────────
    bp_file = _export_blockpit_csv(year_trades, eur_rates, year)

    return filename


# ── Blockpit CSV-Export ───────────────────────────────────────────────────────

def _export_blockpit_csv(year_trades: list, eur_rates: Dict[str, float], year: int) -> str:
    """
    Erstellt eine Blockpit-kompatible CSV-Datei.

    Blockpit-Spalten (Custom Import Template):
    Timestamp (UTC) | Transaction Type | Outgoing Asset | Outgoing Amount |
    Incoming Asset  | Incoming Amount  | Fee Asset      | Fee Amount      |
    Transaction ID  | Note

    Transaktionsttypen für Polymarket:
    - Kauf einer Position:  Transaction Type = "Buy"
                            Outgoing = USDC, Incoming = PM-Token
    - Gewinn (aufgelöst):   Transaction Type = "Sell"
                            Outgoing = PM-Token, Incoming = USDC
    - Verlust (aufgelöst):  Transaction Type = "Expense"  (Token verfällt wertlos)
                            Outgoing = PM-Token, Incoming = (leer)
    """
    filename = BLOCKPIT_CSV_FILE.format(year=year)

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=',')

        # Blockpit-Header (exakt gemäß Template)
        writer.writerow([
            "Timestamp (UTC)",
            "Transaction Type",
            "Outgoing Asset",
            "Outgoing Amount",
            "Incoming Asset",
            "Incoming Amount",
            "Fee Asset",
            "Fee Amount",
            "Transaction ID",
            "Note",
        ])

        for t in year_trades:
            if t.get("modus") == "DRY-RUN":
                continue  # Simulation nicht exportieren

            date    = t.get("datum", "")
            time    = t.get("uhrzeit", "00:00:00")
            ts      = f"{date} {time}"
            rate    = _get_rate(eur_rates, date)

            inv_usd = float(t.get("einsatz_usdc", 0) or 0)
            shares  = float(t.get("shares", 0) or 0)
            pnl_usd = float(t.get("gewinn_verlust_usdc", 0) or 0)
            market_id_short = (t.get("market_id", "") or "")[:8]
            outcome = t.get("outcome", "").replace(" ", "_")[:20]

            # Eindeutiger Asset-Name für diesen Prediction-Market-Token
            asset_name = f"PM-{outcome}-{market_id_short}" if market_id_short else f"PM-{outcome}"

            tx_id   = t.get("tx_hash", "") or f"pm-{t.get('id', '')}"
            note    = f"{t.get('markt', '')[:60]} | {t.get('kategorie', '')} | EUR/USD {rate:.4f}"

            # ── Zeile 1: Kauf der Position ───────────────────────────────
            writer.writerow([
                ts,
                "Buy",
                "USDC",              # Outgoing Asset
                _fmt_bp(inv_usd),    # Outgoing Amount
                asset_name,          # Incoming Asset
                _fmt_bp(shares),     # Incoming Amount
                "",                  # Fee Asset
                "",                  # Fee Amount
                tx_id,
                note,
            ])

            # ── Zeile 2: Auflösung (nur wenn resolved) ───────────────────
            if t.get("aufgeloest"):
                payout_usd = inv_usd + pnl_usd

                if t.get("ergebnis") == "GEWINN" and payout_usd > 0:
                    # Gewinn: Token → USDC
                    writer.writerow([
                        ts,
                        "Sell",
                        asset_name,           # Outgoing Asset
                        _fmt_bp(shares),      # Outgoing Amount
                        "USDC",               # Incoming Asset
                        _fmt_bp(payout_usd),  # Incoming Amount
                        "",
                        "",
                        tx_id + "-resolve",
                        note + " | GEWINN",
                    ])
                else:
                    # Verlust: Token verfällt wertlos → Expense
                    writer.writerow([
                        ts,
                        "Expense",
                        asset_name,        # Outgoing Asset
                        _fmt_bp(shares),   # Outgoing Amount
                        "",                # Incoming Asset (leer bei Verlust)
                        "",
                        "",
                        "",
                        tx_id + "-resolve",
                        note + " | VERLUST (wertlos verfallen)",
                    ])

    logger.info(f"Blockpit-CSV exportiert: {filename}")
    return filename


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _fmt(val) -> str:
    """Dezimalzahl mit Komma als Trennzeichen (deutsches Format für Excel)."""
    return str(val).replace(".", ",")


def _fmt_bp(val: float) -> str:
    """Dezimalzahl mit Punkt (englisches Format für Blockpit)."""
    return f"{val:.6f}".rstrip("0").rstrip(".")


def get_summary(year: Optional[int] = None) -> dict:
    if year is None:
        year = datetime.now().year
    trades      = _load_trades()
    year_trades = [t for t in trades if t.get("datum", "").startswith(str(year))]
    live_trades = [t for t in year_trades if t.get("modus") == "LIVE"]
    resolved    = [t for t in live_trades if t.get("aufgeloest")]
    won         = [t for t in resolved    if t.get("ergebnis") == "GEWINN"]

    return {
        "total_trades":   len(year_trades),
        "live_trades":    len(live_trades),
        "dry_run_trades": len(year_trades) - len(live_trades),
        "resolved":       len(resolved),
        "won":            len(won),
        "lost":           len(resolved) - len(won),
        "win_rate":       round(len(won) / len(resolved) * 100, 1) if resolved else 0,
        "total_pnl":      round(sum(t.get("gewinn_verlust_usdc", 0) for t in live_trades), 2),
        "total_invested": round(sum(t.get("einsatz_usdc", 0) for t in live_trades), 2),
    }


def _load_trades() -> list:
    if not os.path.exists(TRADE_LOG_FILE):
        return []
    try:
        with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_trades(trades: list) -> None:
    with open(TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)
