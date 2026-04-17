"""
auswertung.py v3 - Tägliche P&L Auswertung

Gruppiert nach market_id (direkt auswertbar) statt nach Marktname.
Funktioniert auch wenn markt='Unknown' ist.

Täglich:              python auswertung.py           (speichert automatisch)
Mit Details:          python auswertung.py --details
Ohne Speichern:       python auswertung.py --no-save
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime, date

try:
    import aiohttp
except ImportError:
    print("FEHLER: pip install aiohttp")
    sys.exit(1)

ARCHIVE_FILE = "trades_archive.json"
GAMMA_API    = "https://gamma-api.polymarket.com"

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
C = "\033[96m"; W = "\033[97m"; B = "\033[94m"; X = "\033[0m"


def load_archive():
    if not os.path.exists(ARCHIVE_FILE):
        print(f"{R}trades_archive.json nicht gefunden!{X}")
        return []
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_archive(trades):
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


async def fetch_market(session, market_id):
    """Holt Marktdaten direkt per conditionId via CLOB API."""
    if not market_id or market_id in ("?", "", "None"):
        return {}

    # CLOB API - direkte conditionId Abfrage (korrekte Methode!)
    try:
        url = f"https://clob.polymarket.com/markets/{market_id}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                data = await r.json()
                if data:
                    return data
    except Exception:
        pass

    return {}


def analyze_market(market, our_outcome):
    """Analysiert Markt-Status via CLOB API Format."""
    if not market:
        return "not_found", None, 0.5, 0

    try:
        is_closed = market.get("closed", False)
        is_50_50  = market.get("is_50_50_outcome", False)

        # CLOB API: tokens Liste mit outcome, price, winner
        tokens = market.get("tokens", [])

        if tokens:
            winner    = None
            our_p     = 0.5

            for token in tokens:
                outcome = str(token.get("outcome", ""))
                price   = float(token.get("price", 0.5) or 0.5)
                is_win  = token.get("winner", False)

                if outcome.lower().strip() == str(our_outcome).lower().strip():
                    our_p = price

                if is_win:
                    winner = outcome

            # Aufgelöst wenn: closed=true ODER ein Token winner=true
            resolved = is_closed or (winner is not None)

            if is_50_50:
                return "resolved", "50-50", 0.5, 0.5

            won = (winner is not None and
                   winner.lower().strip() == str(our_outcome).lower().strip())

            if resolved:
                return "resolved", winner or "?", our_p, (1.0 if won else 0.0)
            elif our_p >= 0.80 or our_p <= 0.20:
                near_winner = max(tokens, key=lambda t: float(t.get("price",0)))
                return "near", near_winner.get("outcome","?"), our_p, None
            else:
                return "open", None, our_p, None

        # Fallback: Gamma API Format
        prices_raw   = market.get("outcomePrices", '["0.5","0.5"]')
        outcomes_raw = market.get("outcomes", '["Yes","No"]')
        prices   = [float(p) for p in json.loads(prices_raw if isinstance(prices_raw, str) else json.dumps(prices_raw))]
        outcomes = json.loads(outcomes_raw if isinstance(outcomes_raw, str) else json.dumps(outcomes_raw))
        max_p    = max(prices)
        max_idx  = prices.index(max_p)
        winner   = outcomes[max_idx] if max_idx < len(outcomes) else "?"
        our_p    = 0.5
        for i, o in enumerate(outcomes):
            if str(o).lower().strip() == str(our_outcome).lower().strip():
                our_p = prices[i]; break
        resolved = max_p >= 0.96 or is_closed
        won = str(winner).lower().strip() == str(our_outcome).lower().strip()
        if resolved:
            return "resolved", winner, our_p, (1.0 if won else 0.0)
        elif max_p >= 0.80:
            return "near", winner, our_p, None
        else:
            return "open", winner, our_p, None

    except Exception as e:
        return "error", None, 0.5, 0


async def run(details=False, save=False):
    trades = load_archive()
    if not trades:
        return

    open_trades   = [t for t in trades if not t.get("aufgeloest")]
    closed_trades = [t for t in trades if t.get("aufgeloest")]

    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📊 AUSWERTUNG v3 — {date.today().strftime('%d.%m.%Y')}{X}")
    print(f"{C}  {len(trades)} Trades | {len(open_trades)} offen | {len(closed_trades)} aufgelöst{X}")
    print(f"{C}{'='*65}{X}\n")

    # Bereits archivierte anzeigen
    if closed_trades:
        wins = [t for t in closed_trades if t.get("ergebnis") == "GEWINN"]
        loss = [t for t in closed_trades if t.get("ergebnis") == "VERLUST"]
        pnl  = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in closed_trades)
        print(f"  {W}Archiviert:{X} {G}{len(wins)} Gewonnen{X} | {R}{len(loss)} Verloren{X} | P&L: {G if pnl>=0 else R}${pnl:+.2f}{X}")
        print()

    # Gruppieren nach market_id (nicht nach Marktname!)
    markets_by_id  = {}  # market_id → {trades, question, outcome}
    trades_no_id   = []  # Trades ohne gültige market_id

    for t in open_trades:
        mid = t.get("market_id", "")
        # Gültige conditionId beginnt mit 0x und ist lang
        if mid and mid.startswith("0x") and len(mid) > 10:
            if mid not in markets_by_id:
                markets_by_id[mid] = {
                    "trades":   [],
                    "question": t.get("markt", "Unknown"),
                    "outcome":  t.get("outcome", "Yes"),
                }
            markets_by_id[mid]["trades"].append(t)
            # Wenn Marktname bekannt, updaten
            q = t.get("markt", "")
            if q and q != "Unknown":
                markets_by_id[mid]["question"] = q
        else:
            trades_no_id.append(t)

    total_with_id    = sum(len(g["trades"]) for g in markets_by_id.values())
    total_without_id = len(trades_no_id)

    print(f"  {W}Auswertbar (mit market_id): {G}{total_with_id} Trades{X} in {len(markets_by_id)} Märkten")
    print(f"  {Y}Ohne market_id (alt):       {total_without_id} Trades{X}")
    print(f"\n  {W}Prüfe {len(markets_by_id)} Märkte via API...{X}\n")

    resolved_list = []
    near_list     = []
    open_list     = []
    nf_list       = []

    connector = aiohttp.TCPConnector(limit=8)
    async with aiohttp.ClientSession(connector=connector) as session:
        items = list(markets_by_id.items())
        for i, (mid, group) in enumerate(items):
            trades_in_market = group["trades"]
            our_outcome      = group["outcome"]
            question         = group["question"]

            total_size   = sum(float(t.get("einsatz_usdc", 0) or 0) for t in trades_in_market)
            total_shares = sum(float(t.get("shares", 0) or 0) for t in trades_in_market)
            entry_price  = float(trades_in_market[0].get("preis_usdc", 0.5) or 0.5)
            count        = len(trades_in_market)

            market = await fetch_market(session, mid)

            # Marktname aus API holen wenn lokal unbekannt
            if question == "Unknown" and market:
                question = market.get("question", mid[:30]) or mid[:30]

            status, winner, our_p, pnl_factor = analyze_market(market, our_outcome)

            # P&L berechnen
            if pnl_factor is not None and total_size > 0:
                if total_shares <= 0 and entry_price > 0:
                    total_shares = total_size / entry_price
                won = pnl_factor > 0
                pnl = (total_shares - total_size) if won else -total_size
            else:
                won = False
                pnl = 0

            entry = {
                "mid":      mid,
                "question": question[:58],
                "outcome":  our_outcome,
                "winner":   winner,
                "our_p":    our_p,
                "won":      won,
                "pnl":      pnl,
                "size":     total_size,
                "count":    count,
                "trades":   trades_in_market,
            }

            if status == "resolved":
                resolved_list.append(entry)
                ic = "✅" if won else "❌"
                pc = G if pnl > 0 else R
                print(f"  {ic} {question[:52]}")
                print(f"     {our_outcome} | Gewinner: {W}{winner}{X} | {count}x | ${total_size:.2f} → {pc}${pnl:+.2f}{X}")
                print()

            elif status == "near":
                near_list.append(entry)
                if details:
                    trend = G if our_p >= 0.5 else R
                    print(f"  {'🟢' if our_p>=0.5 else '🔴'} {question[:52]}")
                    print(f"     {our_outcome}: {trend}{our_p*100:.0f}%{X} | ${total_size:.2f}")
                    print()

            elif status == "open":
                open_list.append(entry)

            else:
                nf_list.append(entry)

            if (i+1) % 20 == 0:
                print(f"  {C}... {i+1}/{len(items)} geprüft{X}")

            await asyncio.sleep(0.1)

    # ── Zusammenfassung ──
    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📊 ZUSAMMENFASSUNG{X}")
    print(f"{C}{'='*65}{X}\n")

    if resolved_list:
        wins = [r for r in resolved_list if r["won"]]
        loss = [r for r in resolved_list if not r["won"]]
        tpnl = sum(r["pnl"] for r in resolved_list)
        tsiz = sum(r["size"] for r in resolved_list)
        wr   = len(wins)/len(resolved_list)*100 if resolved_list else 0
        pc   = G if tpnl >= 0 else R
        wi   = "🟢" if wr >= 55 else "🟡" if wr >= 50 else "🔴"

        print(f"  {W}AUFGELÖSTE MÄRKTE: {len(resolved_list)}{X}")
        print(f"  {G}Gewonnen: {len(wins)}{X}  |  {R}Verloren: {len(loss)}{X}")
        print(f"  {wi} Win Rate: {G if wr>=55 else R}{wr:.1f}%{X}")
        print(f"  Investiert: ${tsiz:.2f}")
        print(f"  P&L:        {pc}${tpnl:+.2f} USDC{X}")

        if wins:
            print(f"\n  {G}TOP GEWINNER:{X}")
            for w in sorted(wins, key=lambda x: x["pnl"], reverse=True)[:5]:
                print(f"     {G}+${w['pnl']:.2f}{X}  {w['outcome']} | {w['question'][:45]}")

        if loss:
            print(f"\n  {R}TOP VERLIERER:{X}")
            for l in sorted(loss, key=lambda x: x["pnl"])[:5]:
                print(f"     {R}-${abs(l['pnl']):.2f}{X}  {l['outcome']} | {l['question'][:45]}")

    else:
        print(f"  {Y}Noch keine aufgelösten Märkte in dieser Session.{X}")
        print(f"  Neue Trades mit market_id werden in den nächsten Stunden aufgelöst.")

    if near_list:
        print(f"\n  {Y}FAST ENTSCHIEDEN ({len(near_list)}):{X}")
        for n in sorted(near_list, key=lambda x: x["our_p"], reverse=True)[:5]:
            t = G if n["our_p"] >= 0.5 else R
            print(f"     {t}{n['our_p']*100:.0f}%{X} {n['outcome']} | {n['question'][:45]}")

    print(f"\n  Noch offen:       {W}{len(open_list)}{X}")
    print(f"  API nicht erreichbar: {Y}{len(nf_list)}{X}")
    print(f"  Ohne market_id (alt): {Y}{total_without_id}{X}")

    # Gesamtbilanz
    arch_pnl = sum(float(t.get("gewinn_verlust_usdc", 0) or 0) for t in closed_trades)
    new_pnl  = sum(r["pnl"] for r in resolved_list)
    total    = arch_pnl + new_pnl
    tc       = G if total >= 0 else R
    print(f"\n  {'─'*40}")
    print(f"  {W}GESAMT P&L: {tc}${total:+.2f} USDC{X}")
    print(f"\n{C}{'='*65}{X}\n")

    # Archiv updaten
    if save and resolved_list:
        updated = 0
        for r in resolved_list:
            for t in r["trades"]:
                tid = t.get("id")
                for orig in trades:
                    if orig.get("id") == tid and not orig.get("aufgeloest"):
                        orig["aufgeloest"]          = True
                        orig["ergebnis"]            = "GEWINN" if r["won"] else "VERLUST"
                        sz = float(orig.get("einsatz_usdc", 0) or 0)
                        pr = float(orig.get("preis_usdc", 0.5) or 0.5)
                        sh = sz / pr if pr > 0 else 0
                        orig["gewinn_verlust_usdc"] = round(sh - sz if r["won"] else -sz, 4)
                        updated += 1
        if updated:
            save_archive(trades)
            print(f"{G}  ✅ {updated} Trades archiviert{X}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--details",  action="store_true",  help="Alle Märkte zeigen inkl. fast-entschiedene")
    p.add_argument("--no-save",  action="store_true",  help="Ergebnisse NICHT ins Archiv schreiben (Standard: speichern)")
    args = p.parse_args()
    asyncio.run(run(details=args.details, save=not args.no_save))
