#!/usr/bin/env python3
"""
scripts/test_category_matcher.py — Unit-Tests für utils/category.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.category import get_category, is_sport

TESTS = [
    # ── Sport_US (NBA) ──────────────────────────────────────────────────────
    ("Hornets vs. Magic",                                "Sport_US"),
    ("Hornets vs. Magic: O/U 218.5",                    "Sport_US"),
    ("Spread: Hornets (-3.5)",                           "Sport_US"),
    ("Warriors vs. Suns: O/U 229.5",                    "Sport_US"),
    ("76ers vs. Celtics: O/U 213.5",                    "Sport_US"),
    # ── Sport_US (MLB) ──────────────────────────────────────────────────────
    ("Baltimore Orioles vs. Cleveland Guardians",        "Sport_US"),
    ("Spread: New York Yankees (-2.5)",                  "Sport_US"),
    ("Milwaukee Brewers vs. Miami Marlins",              "Sport_US"),
    ("Kansas City Royals vs. New York Yankees",          "Sport_US"),
    ("Tampa Bay Rays vs. Pittsburgh Pirates",            "Sport_US"),
    ("Detroit Tigers vs. Boston Red Sox",                "Sport_US"),
    ("Atlanta Braves vs. Philadelphia Phillies",         "Sport_US"),
    ("San Diego Padres vs. Los Angeles Angels",          "Sport_US"),
    # ── Sport_US (NHL) ──────────────────────────────────────────────────────
    ("Oilers vs. Canucks: O/U 5.5",                     "Sport_US"),
    # ── Soccer ─────────────────────────────────────────────────────────────
    ("Boyacá Chicó FC vs. AD Cali: Both Teams to Score","Soccer"),
    ("Boyacá Chicó FC vs. AD Cali: O/U 1.5",           "Soccer"),
    ("CA Unión vs. CA Newell's Old Boys: O/U 4.5",      "Soccer"),
    ("Jaguares de Córdoba FC vs. AD Pasto: O/U 3.5",   "Soccer"),
    ("Will AD Cali win on 2026-04-17?",                 "Soccer"),
    ("Will AD Pasto win on 2026-04-17?",                "Soccer"),
    ("Will Boyacá Chicó FC vs. AD Cali end in a draw?","Soccer"),
    ("Will CA Unión vs. CA Newell's Old Boys end in a draw?", "Soccer"),
    ("Will CA Unión win on 2026-04-17?",                "Soccer"),
    ("Atlanta United FC vs. Philadelphia Union",        "Soccer"),
    ("CF América vs. Deportivo Toluca FC: O/U 3.5",    "Soccer"),
    ("Will Club León FC win on 2026-04-18?",            "Soccer"),
    # ── Tennis ─────────────────────────────────────────────────────────────
    ("Santa Cruz: Matias Soto vs Juan Carlos Prado",    "Tennis"),
    ("Tallahassee: Clement Tabur vs Tyler Zink",        "Tennis"),
    ("Tallahassee: Daniil Glinka vs Jack Kennedy",      "Tennis"),
    ("Busan: Alex Bolt vs Yunchaokete Bu",              "Tennis"),
    ("Roland Garros 2026: Djokovic vs Alcaraz",        "Tennis"),
    # ── Geopolitik ─────────────────────────────────────────────────────────
    ("US x Iran permanent peace deal by April 22, 2026?",       "Geopolitik"),
    ("Trump announces end of military operations against Iran",  "Geopolitik"),
    ("Will Trump agree to Iranian enrichment of uranium?",       "Geopolitik"),
    ("Trump declassifies new UFO files by April 30?",           "Geopolitik"),
    ("Will Nicolás Maduro be the leader of Venezuela end of 2026?", "Geopolitik"),
    ("Strait of Hormuz traffic returns to normal by end of April?", "Geopolitik"),
    # ── Sonstiges ──────────────────────────────────────────────────────────
    ("Will AI surpass human intelligence by 2030?",     "Sonstiges"),
]

IS_SPORT_TESTS = [
    ("Sport_US", True),
    ("Tennis",   True),
    ("Soccer",   True),
    ("Sport",    True),
    ("Geopolitik", False),
    ("Sonstiges",  False),
]


def run():
    ok = 0; fail = 0
    for market, expected in TESTS:
        got = get_category(market)
        if got == expected:
            ok += 1
        else:
            fail += 1
            print(f"❌ FAIL: [{expected:10s}→{got:10s}] {market[:65]}")

    for cat, expected in IS_SPORT_TESTS:
        got = is_sport(cat)
        if got == expected:
            ok += 1
        else:
            fail += 1
            print(f"❌ FAIL is_sport({cat!r}): got={got}, want={expected}")

    total = len(TESTS) + len(IS_SPORT_TESTS)
    print(f"\n{'✅ Alle' if fail == 0 else '⚠️ '}{ok}/{total} Tests bestanden"
          + (f" | {fail} Fehler" if fail else ""))
    return fail == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
