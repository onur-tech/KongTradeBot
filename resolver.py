"""
resolver.py — Markt-Auflösungs-Tracker v3

Nutzt outcomePrices der Gamma API:
- Preis nahe 1.0 = Gewinner
- Preis nahe 0.0 = Verlierer
- Markt "resolved" wenn ein Token bei >0.97

Ausfuehren: python resolver.py
Mit Archiv-Update: python resolver.py --save
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("FEHLER: pip install aiohttp")
    sys.exit(1)

STATE_FILE = "bot_state.json"
GAMMA_API  = "https://gamma-api.polymarket.com"

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
W = "\033[97m"
B = "\033[94m"
X = "\033[0m"

RESOLVED_THRESHOLD = 0.97   # Preis > 97% = aufgelöst
NEAR_THRESHOLD     = 0.85   # Preis > 85% = fast sicher


def load_positions():
    if not os.path.exists(STATE_FILE):
        print(f"{R}bot_state.json nicht gefunden!{X}")
        return []
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
    return state.get("open_positions", [])


async def find_market(session, question: str) -> dict:
    """Sucht Markt per Titel, gibt vollstaendige Daten zurueck."""
    try:
        url = f"{GAMMA_API}/markets"
        # Erst aktive suchen
        for params in [
            {"q": question[:45], "limit": 5},
            {"q": question[:30], "limit": 5},
        ]:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                markets = data if isinstance(data, list) else []

                for m in markets:
                    title = (m.get("question") or m.get("title") or "").lower()
                    q_words = [w for w in question[:40].lower().split() if len(w) > 3]
                    matches = sum(1 for w in q_words if w in title)
                    if matches >= min(3, len(q_words)):
                        return m

        return {}
    except Exception:
        return {}


def analyze_market(market: dict, our_outcome: str) -> dict:
    """
    Analysiert Markt-Status via outcomePrices.
    Gibt dict mit status, winner, our_price zurueck.
    """
    if not market:
        return {"status": "not_found"}

    try:
        outcomes_raw = market.get("outcomes", '["Yes","No"]')
        prices_raw   = market.get("outcomePrices", '["0.5","0.5"]')

        if isinstance(outcomes_raw, str):
            outcomes = json.loads(outcomes_raw)
        else:
            outcomes = outcomes_raw

        if isinstance(prices_raw, str):
            prices = json.loads(prices_raw)
        else:
            prices = prices_raw

        prices = [float(p) for p in prices]

        # Winner finden (hoechster Preis)
        max_price = max(prices)
        max_idx   = prices.index(max_price)
        winner    = outcomes[max_idx] if max_idx < len(outcomes) else "?"

        # Unseren Outcome-Preis finden
        our_price = 0.5
        for i, o in enumerate(outcomes):
            if str(o).lower().strip() == str(our_outcome).lower().strip():
                our_price = prices[i]
                break

        # Status bestimmen
        if max_price >= RESOLVED_THRESHOLD:
            status = "resolved"
        elif max_price >= NEAR_THRESHOLD:
            status = "near_resolved"
        elif market.get("closed") or not market.get("active", True):
            status = "closed"
        else:
            status = "open"

        won = str(our_outcome).lower().strip() == str(winner).lower().strip()

        return {
            "status": status,
            "winner": winner,
            "winner_price": max_price,
            "our_outcome": our_outcome,
            "our_price": our_price,
            "won": won,
            "outcomes": outcomes,
            "prices": prices,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def calc_pnl(pos: dict, won: bool) -> float:
    size   = float(pos.get("size_usdc", 0) or 0)
    shares = float(pos.get("shares", 0) or 0)
    price  = float(pos.get("entry_price", 0) or 0)
    if shares <= 0 and price > 0:
        shares = size / price
    return (shares * 1.0) - size if won else -size


async def run(save_results: bool = False, show_near: bool = True):
    positions = load_positions()
    if not positions:
        print(f"{Y}Keine Positionen gefunden.{X}")
        return

    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  🔍 RESOLVER v3 — {len(positions)} Positionen{X}")
    print(f"{C}{'='*65}{X}\n")

    # Deduplizieren
    unique = {}
    for pos in positions:
        q = pos.get("market_question", "")
        if q and q not in unique:
            unique[q] = pos

    print(f"{W}  {len(unique)} einzigartige Märkte werden geprüft...{X}\n")

    resolved   = []
    near_res   = []
    still_open = []
    not_found  = []

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        questions = list(unique.keys())

        for i in range(0, len(questions), 5):
            batch = questions[i:i+5]
            tasks = [find_market(session, q) for q in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for q, market in zip(batch, results):
                pos = unique[q]
                if isinstance(market, Exception):
                    not_found.append(q[:50])
                    continue

                analysis = analyze_market(market, pos.get("outcome", "Yes"))
                status = analysis.get("status", "open")

                # Alle Positionen mit dieser Frage
                all_pos = [p for p in positions if p.get("market_question", "") == q]
                total_size = sum(float(p.get("size_usdc", 0) or 0) for p in all_pos)
                total_pnl  = sum(calc_pnl(p, analysis.get("won", False)) for p in all_pos)
                count = len(all_pos)

                entry = {
                    "question":    q[:55],
                    "our_outcome": pos.get("outcome", ""),
                    "winner":      analysis.get("winner", "?"),
                    "winner_pct":  analysis.get("winner_price", 0) * 100,
                    "our_pct":     analysis.get("our_price", 0) * 100,
                    "won":         analysis.get("won", False),
                    "pnl":         total_pnl,
                    "size":        total_size,
                    "count":       count,
                }

                if status == "resolved":
                    resolved.append(entry)
                    icon = "✅" if entry["won"] else "❌"
                    pnl_c = G if total_pnl > 0 else R
                    print(f"  {icon} {q[:52]}")
                    print(f"     Gesetzt: {C}{entry['our_outcome']}{X} ({entry['our_pct']:.0f}%) | Führend: {W}{entry['winner']}{X} ({entry['winner_pct']:.0f}%)")
                    print(f"     {count}x Pos | ${total_size:.2f} → {pnl_c}${total_pnl:+.2f}{X}")
                    print()
                elif status == "near_resolved" and show_near:
                    near_res.append(entry)
                elif status in ("open", "closed"):
                    still_open.append(entry)
                else:
                    not_found.append(q[:50])

            done = min(i + 5, len(questions))
            print(f"{C}  ... {done}/{len(questions)} geprüft{X}")
            await asyncio.sleep(0.3)

    # Fast-aufgeloeste zeigen
    if near_res:
        print(f"\n{Y}{'='*65}{X}")
        print(f"{Y}  📈 FAST AUFGELÖST (>{NEAR_THRESHOLD*100:.0f}% sicher):{X}")
        print(f"{Y}{'='*65}{X}")
        for e in near_res:
            icon = "🟢" if e["won"] else "🔴"
            pnl_c = G if e["pnl"] > 0 else R
            print(f"  {icon} {e['question'][:52]}")
            print(f"     {e['our_outcome']} ({e['our_pct']:.0f}%) | Führend: {e['winner']} ({e['winner_pct']:.0f}%)")
            print(f"     {e['count']}x | ${e['size']:.2f} → {pnl_c}${e['pnl']:+.2f}{X}")
            print()

    # Zusammenfassung
    print(f"\n{C}{'='*65}{X}")
    print(f"{C}  📊 ZUSAMMENFASSUNG{X}")
    print(f"{C}{'='*65}{X}")

    all_results = resolved + near_res
    if all_results:
        wins = [r for r in all_results if r["won"]]
        losses = [r for r in all_results if not r["won"]]
        total_pnl  = sum(r["pnl"] for r in all_results)
        total_size = sum(r["size"] for r in all_results)
        win_rate   = len(wins) / len(all_results) * 100 if all_results else 0

        pnl_c = G if total_pnl >= 0 else R
        print(f"\n  {W}Aufgelöst (>{RESOLVED_THRESHOLD*100:.0f}%): {len(resolved)}{X}")
        print(f"  {Y}Fast sicher (>{NEAR_THRESHOLD*100:.0f}%):   {len(near_res)}{X}")
        print(f"  Gewonnen:    {G}{len(wins)}{X}  |  Verloren: {R}{len(losses)}{X}")
        print(f"  Win Rate:    {G if win_rate >= 50 else R}{win_rate:.1f}%{X}")
        print(f"  Investiert:  ${total_size:.2f}")
        print(f"  Gesamt P&L:  {pnl_c}${total_pnl:+.2f} USDC{X}")

        if wins:
            print(f"\n  {G}TOP GEWINNER:{X}")
            for w in sorted(wins, key=lambda x: x["pnl"], reverse=True)[:5]:
                print(f"     {G}+${w['pnl']:.2f}{X}  {w['question'][:45]}")
        if losses:
            print(f"\n  {R}TOP VERLIERER:{X}")
            for l in sorted(losses, key=lambda x: x["pnl"])[:5]:
                print(f"     {R}-${abs(l['pnl']):.2f}{X}  {l['question'][:45]}")
    else:
        print(f"\n  {Y}Noch keine aufgelösten Märkte.{X}")
        print(f"  Schau morgen früh wieder — viele Märkte laufen heute Nacht!")

    print(f"\n  {W}Noch offen: {len(still_open)}{X}  |  Nicht gefunden: {len(not_found)}{X}")

    # Beste offene Positionen (nach aktuellem Preis)
    if still_open:
        winning_open = sorted(
            [e for e in still_open if e.get("our_pct", 50) > 60],
            key=lambda x: x.get("our_pct", 50), reverse=True
        )
        if winning_open:
            print(f"\n  {B}💡 OFFENE POSITIONEN IM PLUS:{X}")
            for e in winning_open[:5]:
                print(f"     {G}{e['our_pct']:.0f}%{X} | {e['our_outcome']} | {e['question'][:42]}")

    print(f"\n{C}{'='*65}{X}\n")

    # Archiv updaten
    if save_results and resolved:
        try:
            sys.path.insert(0, os.getcwd())
            from utils.tax_archive import _load_trades, _save_trades
            trades = _load_trades()
            updated = 0
            for r in resolved:
                for t in trades:
                    if r["question"][:35].lower() in t.get("markt","").lower() and not t.get("aufgeloest"):
                        t["aufgeloest"] = True
                        t["ergebnis"] = "GEWINN" if r["won"] else "VERLUST"
                        size = float(t.get("einsatz_usdc", 0) or 0)
                        price = float(t.get("preis_usdc", 0.5) or 0.5)
                        shares = size / price if price > 0 else 0
                        t["gewinn_verlust_usdc"] = round(shares - size if r["won"] else -size, 4)
                        updated += 1
            if updated:
                _save_trades(trades)
                print(f"{G}  ✅ {updated} Trades im Archiv aktualisiert{X}\n")
        except Exception as e:
            print(f"{Y}  Archiv fehler: {e}{X}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Archiv aktualisieren")
    parser.add_argument("--no-near", action="store_true", help="Nur 100% aufgeloeste zeigen")
    args = parser.parse_args()
    asyncio.run(run(save_results=args.save, show_near=not args.no_near))
