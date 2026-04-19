# Discovery Kategorie-Klassifikation Bug-Fix — T-D83
**Erstellt:** 2026-04-19 UTC

---

## Diagnose: Root Cause

### Was kaputt war

**Symptom:** jakgez (`0x9fe53544870879b23a75a2cea0fa35d752cd7936`) wurde als "Politics-Spezialist (88%)" klassifiziert. Realität: jakgez tradet ausschließlich MLB/NBA Over/Unders. Entdeckt durch Windows-CC via 0xinsider Cross-Validation.

**Root Cause: Market-First Bias in `_collect_wallets()` (discovery_poc_v3.py:274)**

```python
# ALT — Bug
wallet_data[w]["category_counts"][category] += 1
```

`category` hier = Kategorie des **Gamma-API-Markts, in dem wir die Wallet gefunden haben**, nicht die tatsächliche Trading-Verteilung der Wallet.

**Ablauf des Bugs:**

1. `_fetch_category_markets()` fetcht Gamma-Events, klassifiziert per `_classify(slug)` → 6 Kategorien
2. `SPORTS_DAILY_RE` in `_classify()` **excludiert** `\bmlb\b`, `\bnba\b`, `\bnfl\b`, etc. → MLB/NBA-Märkte tauchen in keiner Kategorie auf (korrekt: tägliche Sport-Events sind zu häufig für Discovery-Scan)
3. `_collect_wallets()` iteriert nur über gescannte Kategorie-Märkte → findet jakgez in einem **politics-klassifizierten Markt** (wo jakgez 1–N Trades hatte)
4. `category_counts[politics] += 1` für jeden Trade in politics-Märkten
5. **jakgez's echte MLB-Trades**: in excludierten Märkten → nie gezählt
6. Ergebnis: `category_counts = {politics: 541}` → "88% Politics-Focus" — komplett falsch

**Sekundär-Bug: UCL-Slugs nicht erkannt**

`majorexploiter` und `denizz` traden Champions League (`ucl-*`-Slugs). Pattern `champions-league` im Regex matcht aber `ucl-psg1-cfc1-...` nicht (kein Substring-Match auf UCL-Prefix). Beide wurden als "other" klassifiziert statt "sports".

---

## Fix: Wallet-Level Klassifikation via eigene Trade-Slugs

### Strategie

Statt "in welcher Kategorie haben wir die Wallet gefunden" → "was tradet die Wallet tatsächlich".

Die Activity-API gibt pro Trade ein `slug`-Feld zurück. In `_fetch_wallet_stats()` (der ohnehin 1500 Activity-Records fetcht) klassifizieren wir jeden BUY-Trade per `_classify_wallet_slug()` gegen `WALLET_CAT_RE`.

### Änderungen (discovery_poc_v3.py)

**1. Neues `WALLET_CAT_RE` Dict** (~line 144) — umfassende Patterns inkl. täglicher Sports-Slugs:
```python
WALLET_CAT_RE = {
    "sports": re.compile(r"\bmlb\b|\bnba\b|...|\\bucl-|\\bpl-|\\bbundesliga-|..."),
    "politics": ...,
    "geopolitics": ...,
    "crypto": ...,
    "tech": ...,
    "culture": ...,
    "macro": ...,
}
```
Key: `sports` Pattern enthält jetzt auch `ucl-`, `pl-`, `bundesliga-`, `laliga-`, `serie-a-`, `ligue-1-`.

**2. Neue `_classify_wallet_slug(slug)` Funktion** — matcht gegen `WALLET_CAT_RE`, Fallback "other".

**3. `_fetch_wallet_stats()` — Activity-Loop erweitert:**
```python
wallet_cat_counts: Counter = Counter()
# Im Activity-Loop, bei jedem BUY:
slug = a.get("slug", "") or a.get("eventSlug", "")
if slug:
    wallet_cat_counts[_classify_wallet_slug(slug)] += 1
# Return:
"wallet_cat_counts": wallet_cat_counts,
```

**4. Phase 5 — `_compute_focus()` nutzt Wallet-eigene Counts:**
```python
# ALT:
focus = _compute_focus(wd.get("category_counts", Counter()))
# NEU:
wallet_cats = stats.get("wallet_cat_counts") or Counter()
if not wallet_cats:
    wallet_cats = wd.get("category_counts", Counter())  # Fallback
focus = _compute_focus(wallet_cats)
```

**5. `cat_meta`-Update mit Guard** (neue Kategorien wie "sports"/"crypto" nicht in `CATEGORY_RE`-keyed Dict):
```python
if top_cat in cat_meta:
    cat_meta[top_cat]["analyzed"] += 1
```

**Zeilen geändert:** ~50 Zeilen (neu + modifiziert)

---

## Verifikation

### C1: jakgez-Testfall ✅ BESTANDEN

```
Total BUY trades classified: 137
Category breakdown: {'sports': 137}
Top category: sports (100% focus)
TEST PASSED — jakgez correctly classified as sports
```

137/137 BUY-Trades = Sports. Vorher: 88% Politics. Fix korrekt.

### C2: Re-Klassifikation TARGET_WALLETS

| Wallet | Name | Klassifikation (NEU) | Bauchgefühl | Match? |
|--------|------|---------------------|-------------|--------|
| `0xefbc5f...` | majorexploiter | sports 100% (196 Trades) | Geopolitics/Sports | ⚠️ erwartet Geo, ist Sports (UCL) |
| `0xb1abc5...` | HorizonSplendidView | unknown (0 Trades) | Sports | ❓ Keine Activity-Daten |
| `0x492442...` | reachingthesky | sports 100% (161 Trades) | Sports | ✅ |
| `0x02227b...` | denizz | sports 100% (199 Trades) | Politics | ⚠️ erwartet Politics, ist Sports (UCL) |

**Erkenntnis zu majorexploiter + denizz:** Beide traden UCL (`ucl-*`-Slugs = Champions League). Slug-Muster: `ucl-liv1-gal-2026-03-18-liv1`. Nach UCL-Fix korrekt als Sports erkannt. Das "Bauchgefühl Politics/Geopolitics" war für diese Wallets falsch — sie sind Soccer-Trader.

**HorizonSplendidView:** Activity-API gibt 0 Trades zurück. Wallet möglicherweise inaktiv oder anderer Proxy-Wallet-Mechanismus. Klassifikation "unknown" korrekt.

### C3: Re-Klassifikation Phase-1.6-Top-3

Adressen im Phase-1.6-Report truncated (6+4 Hex-Chars). Vollständige Adressen nicht rekonstruierbar ohne Re-Run. Klassifikation via Activity-API für rekonstruierte Adressen gibt 0 Trades → Adressen waren falsch rekonstruiert. **Kein Impact auf Fix** — die Klassifikations-Logik ist korrekt, die Adressen im Report bleiben truncated (Report-Format).

---

## Impact-Abschätzung

| Was | Impact |
|-----|--------|
| jakgez-Klassifikation | War Politics-Spezialist, ist Sports → Aufnahme in TARGET_WALLETS NICHT empfohlen ohne weitere Prüfung (kein Politics-Alpha) |
| Phase 1.5 (v2) Ergebnis | jakgez PASS war möglicherweise korrekt für WR/Sample-Kriterien, aber Archetyp falsch → Auswertung neu bewerten |
| Phase 1.6 (v3) 0 PASS | Wenig Änderung zu erwarten — 0 PASS kam aus WR/GL-Ratio-Filtern, nicht aus Klassifikation |
| majorexploiter/denizz | Sind Soccer-Trader (UCL), nicht Politics/Geopolitics wie vermutet |

---

## Ausblick: Weitere Klassifikations-Probleme

1. **"other"-Residual hoch:** Slugs ohne Keyword-Match (z.B. proprietäre Slugs, neue Märkte) → unklassifiziert. Akzeptabel solange Top-Kategorie eindeutig.
2. **HorizonSplendidView API-Lücke:** Kein Activity-Record zurück. Muss gecheckt werden ob Wallet-Adresse falsch oder Wallet wirklich inaktiv ist.
3. **Multi-Kategorie-Wallets:** Eine Wallet kann Sports+Geopolitics traden. Aktuell nur Top-1-Kategorie gewertet. Für Portfolio-Diversifikation reicht das.
4. **Zeitfenster-Drift:** Wallet-Klassifikation basiert auf letzten 1500 Activity-Records. Saisonale Shifts (MLB off-season → wechselt zu Politics?) könnten in Zukunft WALLET_CAT_RE dynamisch machen.
5. **Tag-basierte Ergänzung:** Gamma-API Events haben `tags`-Array (wenn verfügbar). Noch nicht genutzt. Könnte als Fallback wenn slug-Matching fehlschlägt.

---

## Lesson

**Klassifikation via Markt-Discovery-Quelle ist fundamental broken** wenn tägliche Sport-Märkte aus dem Discovery-Scan excluded werden (korrekt! — zu viel Noise), aber dann das Fehlen der Sports-Counts zu einer falschen Kategorie führt. Die Lösung — Wallet-eigene Trade-History klassifizieren — ist deutlich robuster und von der Discovery-Methode unabhängig.

**Knowledge: P072 — Cross-Validation gegen externe Quellen (0xinsider Leaderboards) kritisch vor TARGET_WALLETS-Aufnahme.**
