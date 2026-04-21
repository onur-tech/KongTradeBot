"""
Market Intelligence Scorer
============================
Bewertet Märkte nach ihrer "Dummheit" —
je ineffizienter, desto besser für uns.

Basierend auf Forschung:
- Sub $10k:    61% Genauigkeit → BEATABLE
- $10-50k:     68% Genauigkeit → Gut
- $50-250k:    77% Genauigkeit → Schwer
- >$1M:        85% Genauigkeit → Kaum beatable

Beste Kategorien:
- Pop Culture/Awards: 62% (dümmste Märkte!)
- Geopolitik klein:  60-65% (Insider-Vorteil)
- Weather:           variabel (Modell-Edge)
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger("polymarket_bot.market_intelligence")


@dataclass
class MarketIntelligence:
    market_id: str
    question: str
    volume: float
    category: str
    efficiency_score: float   # 0-1 (0=dumm, 1=smart)
    our_edge_potential: str   # HIGH/MEDIUM/LOW/SKIP
    reason: str
    recommended_bet_size: float


def score_market_intelligence(
        question: str,
        volume: float,
        category: str = "",
        num_traders: int = 0) -> MarketIntelligence:
    """
    Bewertet ob ein Markt für uns interessant ist.
    Kriterium: NICHT wie groß der Markt ist,
    sondern wie INEFFIZIENT er ist.
    """
    q_lower = question.lower()

    detected_cat = category.lower() if category else ""

    if any(k in q_lower for k in [
        "temperature", "celsius", "fahrenheit",
        "highest temp", "weather"
    ]):
        detected_cat = "weather"
    elif any(k in q_lower for k in [
        "nba", "nfl", "nhl", "mlb", "soccer",
        "football", "basketball", "tennis",
        "game", "match", "score", "championship"
    ]):
        detected_cat = "sports"
    elif any(k in q_lower for k in [
        "iran", "ukraine", "russia", "israel",
        "ceasefire", "war", "military", "nuclear",
        "sanctions", "attack", "strike"
    ]):
        detected_cat = "geopolitics"
    elif any(k in q_lower for k in [
        "bitcoin", "btc", "ethereum", "eth",
        "crypto", "price", "token", "coin"
    ]):
        detected_cat = "crypto"
    elif any(k in q_lower for k in [
        "oscar", "grammy", "emmy", "award", "movie",
        "celebrity", "taylor", "kardashian",
        "album", "song", "chart"
    ]):
        detected_cat = "pop_culture"
    elif any(k in q_lower for k in [
        "trump", "biden", "election", "president",
        "congress", "senate", "vote", "poll"
    ]):
        detected_cat = "politics"
    elif any(k in q_lower for k in [
        "fed", "rate", "inflation", "gdp", "jobs",
        "unemployment", "recession", "cpi"
    ]):
        detected_cat = "macro"

    # ── Volumen-Effizienz ──────────────────────
    if volume < 5000:
        vol_efficiency = 0.20
        vol_label = "MICRO (<$5k)"
    elif volume < 10000:
        vol_efficiency = 0.30
        vol_label = "SMALL ($5-10k)"
    elif volume < 50000:
        vol_efficiency = 0.45
        vol_label = "MEDIUM ($10-50k)"
    elif volume < 250000:
        vol_efficiency = 0.65
        vol_label = "LARGE ($50-250k)"
    elif volume < 1000000:
        vol_efficiency = 0.80
        vol_label = "WHALE ($250k-$1M)"
    else:
        vol_efficiency = 0.90
        vol_label = "INSTITUTIONAL (>$1M)"

    # ── Kategorie-Effizienz ────────────────────
    category_efficiency = {
        "pop_culture":  0.25,
        "geopolitics":  0.30,
        "weather":      0.35,
        "macro":        0.50,
        "politics":     0.55,
        "sports":       0.65,
        "crypto":       0.70,
    }.get(detected_cat, 0.50)

    efficiency = (vol_efficiency * 0.6 + category_efficiency * 0.4)
    edge_potential = (1 - efficiency)

    if edge_potential >= 0.65:
        edge_label = "HIGH"
        bet = 3.0 if volume < 10000 else 5.0
    elif edge_potential >= 0.50:
        edge_label = "MEDIUM"
        bet = 5.0
    elif edge_potential >= 0.35:
        edge_label = "LOW"
        bet = 2.0
    else:
        edge_label = "SKIP"
        bet = 0.0

    reason = (
        f"Kategorie: {detected_cat or 'unbekannt'} "
        f"({category_efficiency:.0%} effizient) | "
        f"Volumen: {vol_label} "
        f"({vol_efficiency:.0%} effizient) | "
        f"Gesamt-Edge: {edge_potential:.0%}"
    )

    result = MarketIntelligence(
        market_id="",
        question=question[:50],
        volume=volume,
        category=detected_cat,
        efficiency_score=efficiency,
        our_edge_potential=edge_label,
        reason=reason,
        recommended_bet_size=bet,
    )

    if edge_label in ["HIGH", "MEDIUM"]:
        logger.info(
            f"[MktIntel] {edge_label} EDGE: "
            f"{question[:40]} | {reason}")

    return result


def filter_markets_by_intelligence(
        markets: list,
        min_edge: str = "MEDIUM") -> list:
    """
    Filtert Märkte nach Intelligenz-Score.
    Gibt nur Märkte zurück wo wir Edge haben.
    """
    priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SKIP": 0}
    min_priority = priority.get(min_edge, 2)

    scored = []
    for m in markets:
        q = m.get("question", "")
        vol = float(m.get("volume", "0") or 0)
        cat = m.get("tags", [""])[0] if m.get("tags") else ""

        intel = score_market_intelligence(q, vol, cat)
        intel.market_id = m.get("conditionId", "")

        if priority.get(intel.our_edge_potential, 0) >= min_priority:
            scored.append((intel, m))

    scored.sort(
        key=lambda x: (
            priority.get(x[0].our_edge_potential, 0),
            -x[0].efficiency_score,
        ),
        reverse=True,
    )

    logger.info(
        f"[MktIntel] {len(scored)}/{len(markets)} "
        f"Märkte mit Edge ≥ {min_edge}")

    return [(intel, market) for intel, market in scored]
