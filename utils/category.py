"""
utils/category.py — Zentrale Kategorie-Klassifizierung für Polymarket-Märkte.

Kategorien (in Prüf-Reihenfolge):
  Soccer    — Fußball (FC-Teams, lateinam. Clubs, Ligaschlüsselwörter)
  Sport_US  — NBA, MLB, NHL, NFL (US-Profisport, Team-Namen, O/U, Spread)
  Tennis    — ATP/WTA-Turniere, Stadtname: Spieler vs Spieler
  Geopolitik
  Crypto
  Makro
  Sonstiges (Fallback)
"""

import re

# Für Backtester / Filter die alle Sport-Kategorien zusammenfassen wollen
SPORT_CATEGORIES = frozenset({"Sport_US", "Tennis", "Soccer", "Sport"})

ALL_CATEGORIES = ["Sport_US", "Tennis", "Soccer", "Geopolitik", "Crypto", "Makro", "Sonstiges"]


def get_category(question: str) -> str:
    if not question:
        return "Sonstiges"
    q = question.lower().strip()

    if _is_soccer(q):
        return "Soccer"
    if _is_us_sport(q):
        return "Sport_US"
    if _is_tennis(q):
        return "Tennis"

    if any(w in q for w in [
        "iran", "israel", "ukraine", "trump", "nuclear", "war", "ceasefire",
        "election", "president", "nato", "china", "russia", "peace",
        "venezuela", "maduro", "hormuz", "missile", "sanction", "tariff",
        "ufos", "ufo files", "declassif", "enrichment",
    ]):
        return "Geopolitik"

    if any(w in q for w in [
        "bitcoin", "btc", "eth", "crypto", "solana", "render", "token",
        "blockchain", "defi", "nft", "coinbase", "binance", "doge",
    ]):
        return "Crypto"

    if any(w in q for w in [
        "fed", "interest rate", "inflation", "gdp", "recession", "oil", "gold",
        "dollar", "euro", "yen", "bond", "yield", "cpi",
    ]):
        return "Makro"

    return "Sonstiges"


def is_sport(cat: str) -> bool:
    """True für alle Sport-Kategorien (US, Tennis, Soccer, legacy Sport)."""
    return cat in SPORT_CATEGORIES


# ─── Private Helfer ────────────────────────────────────────────────────────────

def _is_soccer(q: str) -> bool:
    # "FC" als eigenständiges Wort — stärkstes Fußball-Signal
    if re.search(r'\bfc\b', q):
        return True
    # Spielformat-spezifisch für Fußball
    if any(w in q for w in [
        "both teams to score", " draw", "end in a draw",
        "premier league", "bundesliga", "la liga", "serie a",
        "champions league", "europa league", "copa ", "liga ",
        "atletico", "real madrid", "manchester", "arsenal", "chelsea",
        "liverpool", "juventus", "inter milan", "ajax",
        "jaguares",   # Jaguares de Córdoba FC (Kolumbien)
        "boyacá", "chicó",
    ]):
        return True
    # "Will X win on YYYY-MM-DD?" — Polymarket-Format für Fußball-Match-Outcomes
    if re.search(r'win on \d{4}-\d{2}-\d{2}', q):
        return True
    # Lateinamerikanische Club-Kürzel (CA, AD, CD, CF, SC) als eigenständiges Token
    # Beispiel: "CA Unión", "AD Cali", "CD Guadalajara"
    if re.search(r'\b(ca|ad|cd|cf|sc)\s+[a-záéíóúñü]', q):
        return True
    # CF América / Toluca etc.
    if any(w in q for w in ["cf ", " cf ", "toluca", "america fc", "pumas", "chivas",
                              "leon fc", "club leon", "deportivo"]):
        return True
    return False


def _is_us_sport(q: str) -> bool:
    # Explizite Liga-Abkürzungen
    if any(w in q for w in ["nba", "mlb", "nhl", "nfl", "ncaa"]):
        return True
    # Wett-Formate (O/U und Spread sind US-Sport-spezifisch auf Polymarket)
    if "o/u" in q:
        return True
    if re.search(r'\bspread\s*:', q):
        return True
    # NBA-Teams
    _NBA = [
        "hornets", "magic", "warriors", "suns", "nuggets", "timberwolves",
        "celtics", "lakers", "heat", "bucks", "knicks", "nets", "76ers", "sixers",
        "hawks", "wizards", "pacers", "bulls", "pistons", "cavaliers", "cavs",
        "raptors", "thunder", "trail blazers", "blazers", "jazz", "spurs",
        "pelicans", "grizzlies", "rockets", "mavericks", "mavs", "clippers", "kings",
    ]
    if any(w in q for w in _NBA):
        return True
    # MLB-Teams
    _MLB = [
        "yankees", "orioles", "guardians", "brewers", "marlins", "rays",
        "pirates", "royals", "braves", "phillies", "tigers", "red sox",
        "dodgers", "giants", "cubs", "cardinals", "mets", "nationals", "nats",
        "astros", "athletics", "mariners", "twins", "white sox", "angels",
        "rangers", "blue jays", "padres", "reds", "rockies", "diamondbacks",
    ]
    if any(w in q for w in _MLB):
        return True
    # NHL-Teams
    _NHL = [
        "oilers", "bruins", "canadiens", "maple leafs", "lightning",
        "penguins", "capitals", "blackhawks", "red wings", "flames",
        "canucks", "senators", "sabres", "hurricanes", "golden knights",
        "jets", "avalanche", "predators", "stars", "wild", "ducks", "sharks",
        "blues", "panthers",
    ]
    if any(w in q for w in _NHL):
        return True
    # NFL-Teams
    _NFL = [
        "chiefs", "eagles", "49ers", "packers", "cowboys", "broncos",
        "bears", "ravens", "steelers", "dolphins", "bills", "patriots",
        "seahawks", "rams", "buccaneers", "bucs", "falcons", "bengals",
        "browns", "colts", "texans", "raiders", "chargers", "vikings",
        "lions", "commanders", "saints",
    ]
    if any(w in q for w in _NFL):
        return True
    if "baseball" in q:
        return True
    return False


def _is_tennis(q: str) -> bool:
    # Explizite ATP/WTA-Kennzeichnung
    if any(w in q for w in ["atp", "wta", " tennis", "tennis "]):
        return True
    # Grand Slams & große Turniere
    _TOURNAMENTS = [
        "roland garros", "wimbledon", "australian open",
        "madrid open", "barcelona open", "rome open", "italian open",
        "indian wells", "miami open", "monte-carlo", "monte carlo",
        "cincinnati", "hamburg open", "geneva open", "lyon open",
        "busan open", "houston open", "marrakech", "estoril",
        "santa cruz",   # Challenger-Turnier aus dem Archiv
        "tallahassee",  # ITF/Challenger-Turnier aus dem Archiv
    ]
    if any(w in q for w in _TOURNAMENTS):
        return True
    # Format: "StadtName: Vorname Nachname vs Vorname Nachname" (Turnierformat)
    # Nur "vs" ohne Punkt (Tennis/ITF nutzt "vs", US-Sport nutzt "vs.")
    if re.match(r'^[a-z][a-z\s]+:\s+[a-záéíóú]+\s+[a-záéíóú]+\s+vs\s+[a-záéíóú]', q) \
            and "vs." not in q:
        return True
    return False
