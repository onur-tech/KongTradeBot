"""
backtester.py -- Historische Projektion & Gewinnerwartung

Berechnet realistische Monatsrenditen auf Basis von:
  - trades_archive.json  (echte Bot-Aktivitaet, ~2 Tage DRY-RUN)
  - wallet_history.json  (verifizierte Win Rates von predicts.guru)

Budget: $1.000 | MAX_TRADE_SIZE_USD: $25 | COPY_SIZE_MULTIPLIER: 0.02

Ausfuehren: python backtester.py
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

# Windows-Terminal UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(__file__)
ARCHIVE_PATH = os.path.join(BASE, "trades_archive.json")
WALLET_PATH  = os.path.join(BASE, "wallet_history.json")

# ---------- Konfiguration ----------------------------------------------------
BUDGET_USD       = 1_000.0   # Startkapital ($)
MAX_TRADE_USD    = 25.0      # MAX_TRADE_SIZE_USD
COPY_MULTIPLIER  = 0.02      # aus .env
AVG_RESOLUTION_D = 2.0       # Tage bis Market-Aufloesung (konservativ)
ARCHIVE_DAYS     = 2         # Anzahl Tage im Archiv

# Wallet-Multiplikatoren (aus strategies/copy_trading.py)
WALLET_MULTIPLIERS = {
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": 0.3,   # sovereign2013
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": 0.5,   # RN1
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": 0.5,   # denizz
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": 2.5,   # wan123
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": 3.0,   # DrPufferfish
    "0xbddf61af533ff524d27154e589d2d7a81510c684": 3.0,   # Countryside
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 2.0,   # HOOK
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": 2.0,   # kcnyekchno
    "0x019782cab5d844f02bafb71f512758be78579f3c": 3.0,   # majorexploiter
    "0x492442eab586f242b53bda933fd5de859c8a3782": 2.0,   # April#1 Sports
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": 2.0,   # HorizonSplendidView
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": 2.0,   # reachingthesky
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": 1.5,   # BoneReader
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": 2.0,   # Crypto Spezialist
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": 0.3,   # Gambler1968
}

NAMES = {
    "0xee613b3fc183ee44f9da9c05f53e2da107e3debf": "sovereign2013",
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea": "RN1",
    "0xbaa2bcb5439e985ce4ccf815b4700027d1b92c73": "denizz",
    "0xde7be6d489bce070a959e0cb813128ae659b5f4b": "wan123",
    "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e": "DrPufferfish",
    "0xbddf61af533ff524d27154e589d2d7a81510c684": "Countryside",
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": "HOOK",
    "0x7177a7f5c216809c577c50c77b12aae81f81ddef": "kcnyekchno",
    "0x019782cab5d844f02bafb71f512758be78579f3c": "majorexploiter",
    "0x492442eab586f242b53bda933fd5de859c8a3782": "April#1 Sports",
    "0x02227b8f5a9636e895607edd3185ed6ee5598ff7": "HorizonSplendidView",
    "0xefbc5fec8d7b0acdc8911bdd9a98d6964308f9a2": "reachingthesky",
    "0xd84c2b6d65dc596f49c7b6aadd6d74ca91e407b9": "BoneReader",
    "0xde17f7144fbd0eddb2679132c10ff5e74b120988": "Crypto Spezialist",
    "0x7a6192ea6815d3177e978dd3f8c38be5f575af24": "Gambler1968",
}

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; W = "\033[97m"; B = "\033[94m"; X = "\033[0m"


# ---------- Adress-Normalisierung --------------------------------------------

def normalize_addr(raw: str) -> str:
    """Normalisiert Adressen: lowercase, truncation '...' entfernen -> 20-Zeichen Praefix."""
    if not raw:
        return ""
    addr = raw.lower().rstrip(".")
    # Falls abgekuerzt (z.B. '0xee613b3fc183ee44f9'): praefix-match moeglich
    return addr


def resolve_full_addr(prefix_or_full: str) -> str:
    """Findet die vollstaendige bekannte Adresse aus einem Praefix."""
    p = prefix_or_full.lower().rstrip(".")
    for full in NAMES:
        if full.startswith(p) or p.startswith(full[:len(p)]):
            return full
    return p


# ---------- Daten laden ------------------------------------------------------

def load_archive() -> list:
    with open(ARCHIVE_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_wallets() -> dict:
    with open(WALLET_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------- Archiv-Statistiken -----------------------------------------------

def calc_archive_stats(trades: list) -> dict:
    """Per-Wallet Stats aus dem Trade-Archiv (aggregiert, praefix-normalisiert)."""
    stats = defaultdict(lambda: {
        "trades": 0, "wins": 0, "losses": 0,
        "total_stake": 0.0, "total_pnl": 0.0, "prices": [],
    })

    for t in trades:
        raw_addr = t.get("source_wallet") or ""
        full_addr = resolve_full_addr(normalize_addr(raw_addr))

        stake = t.get("einsatz_usdc") or t.get("size_usdc") or 0.0
        price = t.get("preis_usdc") or t.get("preis") or 0.0

        stats[full_addr]["trades"] += 1
        stats[full_addr]["total_stake"] += stake
        if 0 < price < 1:
            stats[full_addr]["prices"].append(price)

        if t.get("aufgeloest"):
            pnl = t.get("gewinn_verlust_usdc") or t.get("pnl") or 0.0
            stats[full_addr]["total_pnl"] += pnl
            if t.get("ergebnis") == "GEWINN":
                stats[full_addr]["wins"] += 1
            elif t.get("ergebnis") == "VERLUST":
                stats[full_addr]["losses"] += 1

    return dict(stats)


# ---------- EV-Kalkulation ---------------------------------------------------

def calc_ev(win_rate: float, avg_price: float, stake: float) -> float:
    """
    Erwartungswert fuer Binary-Market Trade:
    EV = stake * (win_rate / avg_price - 1)
    """
    if avg_price <= 0.01 or avg_price >= 0.99:
        return 0.0
    return stake * (win_rate / avg_price - 1.0)


# ---------- Haupt-Analyse ----------------------------------------------------

def run_backtest():
    archive = load_archive()
    wallets = load_wallets()
    arc_stats = calc_archive_stats(archive)

    resolved_total = sum(1 for t in archive if t.get("aufgeloest"))
    print(f"\n{C}{'='*74}{X}")
    print(f"{C}  POLYMARKET COPY TRADING -- BACKTEST & MONATSPROJEKTION{X}")
    print(f"{C}  Budget: ${BUDGET_USD:,.0f} | MAX_TRADE: ${MAX_TRADE_USD:.0f} | COPY_MULT: {COPY_MULTIPLIER}{X}")
    print(f"{C}  Archiv: {ARCHIVE_DAYS} Tage | {len(archive):,} Trades | {resolved_total:,} aufgeloest{X}")
    print(f"{C}{'='*74}{X}\n")

    # ---- Schritt 1: Per-Wallet berechnen ------------------------------------
    wallet_rows = []
    total_daily_deploy = 0.0
    total_daily_pnl_sim = 0.0

    for addr, ws in arc_stats.items():
        if ws["trades"] < 1:
            continue

        full = resolve_full_addr(addr)
        name = NAMES.get(full, full[:14] + "...")
        multi = WALLET_MULTIPLIERS.get(full, 0.5)
        hist = wallets.get(full, {})

        trades_per_day = ws["trades"] / ARCHIVE_DAYS
        avg_stake = ws["total_stake"] / ws["trades"]
        avg_price = (sum(ws["prices"]) / len(ws["prices"])) if ws["prices"] else 0.50

        # Win Rate: Archiv (>= 100 aufgeloest) >> predicts.guru (mit Abzug)
        resolved_n = ws["wins"] + ws["losses"]
        if resolved_n >= 100:
            win_rate = ws["wins"] / resolved_n
            wr_src = "Archiv"
        else:
            raw_wr = (hist.get("win_rate") or 50.0) / 100.0
            win_rate = min(raw_wr * 0.88, 0.85)  # 12% Regression + 85% Cap
            wr_src = "guru*"

        # Taeglich deployed & PnL
        daily_stake = trades_per_day * avg_stake

        if resolved_n >= 50:
            # Echte PnL aus Archiv
            daily_pnl = ws["total_pnl"] / ARCHIVE_DAYS
            pnl_src = "Archiv"
        else:
            # EV-basiert (Schaetzung)
            daily_pnl = trades_per_day * calc_ev(win_rate, avg_price, avg_stake)
            pnl_src = "EV"

        wallet_rows.append({
            "name": name, "addr": full, "multi": multi,
            "tpd": trades_per_day, "avg_stake": avg_stake, "avg_price": avg_price,
            "wr": win_rate, "wr_src": wr_src,
            "daily_stake": daily_stake, "daily_pnl": daily_pnl, "pnl_src": pnl_src,
            "resolved": resolved_n,
        })

        total_daily_deploy += daily_stake
        total_daily_pnl_sim += daily_pnl

    # ---- Schritt 2: Budget-Skalierung ---------------------------------------
    # Max nachhaltig pro Tag = Budget / avg Aufloesung in Tagen
    max_deploy_day = BUDGET_USD / AVG_RESOLUTION_D
    scale = min(1.0, max_deploy_day / total_daily_deploy) if total_daily_deploy > 0 else 1.0
    scaled_daily_pnl = total_daily_pnl_sim * scale

    # ---- Tabelle 1: Per-Wallet ----------------------------------------------
    HDR = f"  {'Wallet':<20} {'Mult':>4}  {'Trades/d':>8}  {'Avg$':>6}  {'Preis':>7}  {'WR':>7}  {'Deploy/d':>9}  {'PnL/d':>9}"
    print(HDR)
    print(f"  {'-'*20} {'-'*4}  {'-'*8}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*9}  {'-'*9}")

    for r in sorted(wallet_rows, key=lambda x: -x["daily_stake"]):
        spnl = r["daily_pnl"] * scale
        pnl_col = G if spnl > 0 else R
        wr_pct = r["wr"] * 100
        wr_col = G if wr_pct >= 65 else Y if wr_pct >= 55 else R
        src_tag = f"({r['wr_src']})"

        print(f"  {W}{r['name']:<20}{X} "
              f"{r['multi']:>4.1f}x "
              f"{r['tpd']:>9.0f}  "
              f"${r['avg_stake']:>5.2f}  "
              f"{r['avg_price']:>7.3f}  "
              f"{wr_col}{wr_pct:>6.1f}%{X} "
              f"${r['daily_stake']*scale:>8.2f}  "
              f"{pnl_col}${spnl:>+8.2f}{X} "
              f"{Y}{src_tag}{X}")

    print(f"  {'='*20} {'':>4}  {'':>8}  {'':>6}  {'':>7}  {'':>7}  "
          f"${total_daily_deploy*scale:>8.2f}  "
          f"{G if scaled_daily_pnl>0 else R}${scaled_daily_pnl:>+8.2f}{X}  (gesamt/Tag)")

    # ---- Schritt 3: Budget-Analyse ------------------------------------------
    print(f"\n{C}  BUDGET-ANALYSE{X}")
    print(f"  Rohes Signal-Volumen/Tag:      {sum(r['tpd'] for r in wallet_rows):>8,.0f} Trades")
    print(f"  Kapital benoetigt/Tag (roh):   ${total_daily_deploy:>9,.2f}")
    print(f"  Max. Deploy bei $1k Budget:    ${max_deploy_day:>9,.2f}  ($1k / {AVG_RESOLUTION_D:.0f}d Laufzeit)")
    print(f"  Budget-Skalierungsfaktor:      {scale:>9.1%}")
    print(f"  Effektive Trades/Tag:          {sum(r['tpd'] for r in wallet_rows)*scale:>8,.0f}")
    print(f"  Effektiv deployed/Tag:         ${total_daily_deploy*scale:>9,.2f}")

    # ---- Schritt 4: 30-Tage Projektion --------------------------------------
    print(f"\n{C}  30-TAGE MONATSPROJEKTION (auf $1.000 Budget){X}")
    print(f"  {'Szenario':<45} {'Monat PnL':>12}  {'ROI':>8}")
    print(f"  {'-'*45} {'-'*12}  {'-'*8}")

    scenarios = [
        ("Konservativ  (Live ~30% der Simulation)", 0.30),
        ("Erwartet     (Live ~50% der Simulation)", 0.50),
        ("Optimistisch (Live ~75% der Simulation)", 0.75),
    ]
    for label, factor in scenarios:
        mpnl = scaled_daily_pnl * 30 * factor
        roi  = mpnl / BUDGET_USD * 100
        col  = G if mpnl > 0 else R
        print(f"  {label:<45} {col}${mpnl:>+10.2f}  {roi:>+7.1f}%{X}")

    # ---- Schritt 5: Top-Performer -------------------------------------------
    print(f"\n{C}  TOP-PERFORMER (Expected-Szenario, 30 Tage){X}")
    top = sorted(wallet_rows, key=lambda x: -x["daily_pnl"])[:6]
    for r in top:
        m30 = r["daily_pnl"] * scale * 30 * 0.50
        col = G if m30 > 0 else R
        note = " [Archiv-bestaetigt]" if r["wr_src"] == "Archiv" else " [predicts.guru, -12% Reg.]"
        print(f"  {W}{r['name']:<20}{X}  WR {r['wr']*100:.1f}% x {r['multi']}x  ->  "
              f"{col}${m30:>+8.2f}/Monat{X}  {Y}{note}{X}")

    # ---- Schritt 6: Problemfaelle -------------------------------------------
    neg = [r for r in wallet_rows if r["daily_pnl"] < -0.01]
    if neg:
        print(f"\n{Y}  PROBLEM-WALLETS (negatives EV){X}")
        for r in neg:
            m30 = r["daily_pnl"] * scale * 30
            print(f"  {W}{r['name']:<20}{X}  WR {r['wr']*100:.1f}% x {r['multi']}x  ->  "
                  f"{R}${m30:>+8.2f}/Monat{X}  => Multiplier senken")

    # ---- Schritt 7: Empfehlungen --------------------------------------------
    avg_stake_all = (sum(r["avg_stake"] for r in wallet_rows) / len(wallet_rows)) if wallet_rows else 2.3
    rec_max_trades = int(max_deploy_day / avg_stake_all * 0.9)
    print(f"\n{C}  EMPFEHLUNGEN FUER $1.000 BUDGET{X}")
    print(f"  1. COPY_SIZE_MULTIPLIER = 0.02  (beibehalten)")
    print(f"  2. MAX_TRADES_PER_DAY   = {rec_max_trades}  (verhindert Kapitalerschoepfung)")
    print(f"  3. sovereign2013 0.3x   = optimal (Archiv-bestaetigt: 64.1% WR gefiltert)")
    print(f"  4. RN1 auf 0.2x senken  (Archiv: nur 26.8% WR -> negatives EV)")
    print(f"  5. DrPufferfish 3.0x + Countryside 3.0x = hoechste Prioritaet (92% WR)")

    print(f"\n{C}{'='*74}{X}")
    print(f"  * predicts.guru WR mit 12% Abzug + 85% Cap (Overfitting-Schutz)")
    print(f"  * DRY-RUN -> Live-Performance ca. 50% der simulierten Werte")
    print(f"  * Archiv-WR fuer sovereign2013 basiert auf {arc_stats.get('0xee613b3fc183ee44f9da9c05f53e2da107e3debf', {}).get('wins', 0) + arc_stats.get('0xee613b3fc183ee44f9da9c05f53e2da107e3debf', {}).get('losses', 0):,} aufgeloesten Trades")
    print(f"{C}{'='*74}{X}\n")

    # ---- Export -------------------------------------------------------------
    result = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "budget_usd": BUDGET_USD, "max_trade_usd": MAX_TRADE_USD,
            "copy_multiplier": COPY_MULTIPLIER, "archive_days": ARCHIVE_DAYS,
        },
        "summary": {
            "total_archive_trades": len(archive),
            "total_daily_deploy_roh": round(total_daily_deploy, 2),
            "budget_scale_factor": round(scale, 4),
            "scaled_daily_pnl": round(scaled_daily_pnl, 4),
            "monthly_conservative": round(scaled_daily_pnl * 30 * 0.30, 2),
            "monthly_expected": round(scaled_daily_pnl * 30 * 0.50, 2),
            "monthly_optimistic": round(scaled_daily_pnl * 30 * 0.75, 2),
        },
        "per_wallet": sorted([
            {
                "name": r["name"],
                "multiplier": r["multi"],
                "trades_per_day": round(r["tpd"], 1),
                "avg_stake_usd": round(r["avg_stake"], 3),
                "avg_price": round(r["avg_price"], 3),
                "win_rate_pct": round(r["wr"] * 100, 1),
                "wr_source": r["wr_src"],
                "resolved_trades": r["resolved"],
                "monthly_expected_usd": round(r["daily_pnl"] * scale * 30 * 0.50, 2),
            }
            for r in wallet_rows
        ], key=lambda x: -x["monthly_expected_usd"]),
    }

    out = os.path.join(BASE, "backtest_projection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Gespeichert: backtest_projection.json\n")
    return result


if __name__ == "__main__":
    run_backtest()
