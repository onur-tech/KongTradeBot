# Polymarket Builder Program Research (19.04.2026)

_Zweck: Verstehen ob/wie Builder Program für Auto-Claim (T-M04b) benötigt wird._
_Trigger: T-M04b Implementation — MetaMask nicht direkter Signer, Private Key Weg unklar._

---

## ⚡ KRITISCHE KORREKTUR (P076 / claim_fix_research)

**claim_fix_research_2026-04-19.md hatte FALSCHE RelayClient-Credentials.**

### Alt (falsch aus P076):
```python
client = RelayClient(
    host="https://relayer.polymarket.com",       # ← FALSCH
    api_creds=ApiCreds(
        api_key=config.api_key,                  # ← FALSCH (CLOB-Keys ≠ Relayer-Keys)
        api_secret=config.api_secret,
        api_passphrase=config.api_passphrase,
    )
)
```

### Neu (korrekt aus offiziellen Docs):
```python
from py_builder_relayer_client.client import RelayClient

client = RelayClient(
    host="https://relayer-v2.polymarket.com",    # ← relayer-v2, nicht relayer
    chain=137,                                    # ← Polygon Mainnet
    signer=os.getenv("PRIVATE_KEY"),             # ← Private Key direkt
    relayer_api_key=os.environ["RELAYER_API_KEY"],
    relayer_api_key_address=os.environ["RELAYER_API_KEY_ADDRESS"],
)
```

**Konsequenz:** T-M04b braucht kein Builder Program. Nur self-service API-Key erstellen.

---

## Was ist das Builder Program?

**Kurz:** Das Builder Program ist ein **Grants- und Attribution-System** — kein Zugangstor.

Jeder kann die Relayer-API nutzen. Der Builder Program-Beitritt dient nur dazu:
- Volume-Credit auf dem Builder Leaderboard zu erhalten
- Wöchentliche Grant-Auszahlungen ($2.5M+ gesamt) zu erhalten
- Builder Badge + Telegram/Engineering Support (höhere Tiers)

**Falsche Annahme (heute Morgen):** "Builder Program erforderlich für Relayer-Zugang"
**Wahrheit:** Relayer-Zugang = self-service API-Key, keine Genehmigung nötig

### Builder Code (für Leaderboard)

Ein `bytes32`-Identifier der jedem Order beigefügt wird:
```python
response = client.create_and_post_order(
    OrderArgs(..., builder_code=os.environ["POLY_BUILDER_CODE"])
)
```

Erhältlich unter: `polymarket.com/settings?tab=builder` → sofort, kein Review.
KongBot benötigt diesen Code NUR wenn wir im Leaderboard auftauchen wollen.

---

## Anwendungsprozess: Relayer API-Key erstellen

### Schritt-für-Schritt (SELF-SERVICE)

1. **Login** auf polymarket.com mit dem Bot-Wallet (oder via Magic.link)
2. **Navigate:** `polymarket.com/settings?tab=api-keys`
   - Oder: Profilbild → Settings → "API Keys" Tab
3. **Klick:** "+ Create New" im Bereich "Builder Keys"
4. **Kopieren:** API Key + Address werden einmalig angezeigt
   - `RELAYER_API_KEY` = UUID-Format
   - `RELAYER_API_KEY_ADDRESS` = Ethereum-Adresse (0x...)
   - ⚠ Secret und Passphrase nur einmal sichtbar — sofort sichern!
5. **Server:** In `.env` eintragen

**Keine Wartezeit, keine Genehmigung, kein Application-Formular erforderlich.**

### Benötigte Informationen

Keine spezielle Angaben — nur Login mit dem Wallet.

### Kontakt (optional, nur für Builder Program Leaderboard)

- Formular: builders.polymarket.com → "Apply now"
  - Projektname, Website, Email, Twitter, Telegram, Builder API Key
- Discord: discord.gg/polymarket (Channel: #builders)
- Twitter: @PolymarketBuild

---

## Credentials und Integration

### Was man bekommt

| Credential | Format | Zweck |
|-----------|--------|-------|
| `RELAYER_API_KEY` | UUID | Auth für Relayer-Requests |
| `RELAYER_API_KEY_ADDRESS` | 0x... Ethereum-Adresse | Besitzer-Identifikation |
| `POLY_BUILDER_CODE` | bytes32 | Optional: Leaderboard-Attribution |

### Konfusion: Alte vs. Neue Credential-Formate

Es gibt **zwei Formatsysteme** in verschiedenen Quellen:

**Format A (veraltet, .env.example im GitHub-Repo):**
```
BUILDER_API_KEY=...
BUILDER_SECRET=...
BUILDER_PASS_PHRASE=...
```

**Format B (aktuell, offizielle Docs 2026):**
```
RELAYER_API_KEY=...        # UUID
RELAYER_API_KEY_ADDRESS=...  # 0x...
```

→ Format B ist korrekt für aktuelle `py-builder-relayer-client` Version.
→ Format A entspricht dem veralteten Builder-Settings-System (CLOB-ähnlich).

### Vollständige .env-Ergänzung für T-M04b

```bash
# Bestehend (bereits auf Server):
PRIVATE_KEY=...
POLYMARKET_ADDRESS=...

# NEU für T-M04b (via polymarket.com/settings?tab=api-keys erstellen):
RELAYER_API_KEY=...
RELAYER_API_KEY_ADDRESS=...

# Optional (nur für Leaderboard):
POLY_BUILDER_CODE=...
```

### Vollständige Python-Integration (T-M04b)

```python
import os
from py_builder_relayer_client.client import RelayClient
from web3 import Web3

CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

client = RelayClient(
    host="https://relayer-v2.polymarket.com",
    chain=137,
    signer=os.getenv("PRIVATE_KEY"),
    relayer_api_key=os.environ["RELAYER_API_KEY"],
    relayer_api_key_address=os.environ["RELAYER_API_KEY_ADDRESS"],
)

# Claim (Standard-Market):
redeem_tx = {
    "to": CTF,
    "data": Web3().eth.contract(address=CTF, abi=[{
        "name": "redeemPositions",
        "type": "function",
        "inputs": [
            {"name": "collateralToken", "type": "address"},
            {"name": "parentCollectionId", "type": "bytes32"},
            {"name": "conditionId", "type": "bytes32"},
            {"name": "indexSets", "type": "uint256[]"}
        ],
        "outputs": []
    }]).encode_abi("redeemPositions", [USDC, bytes(32), condition_id_bytes, index_sets]),
    "value": "0"
}
response = client.execute([redeem_tx], "Claim position")
response.wait()
```

---

## Wartezeit und Kosten

| Aspekt | Detail |
|--------|--------|
| Wartezeit Relayer-API-Key | **0 — sofort, self-service** |
| Wartezeit Builder Leaderboard | 1-2 Werktage (nach Formular-Einreichung) |
| Kosten Relayer-Transaktionen | **Gratis (gasless)** — Polymarket übernimmt Gas |
| Rate-Limits | Nicht dokumentiert — max. 100 API-Keys pro Adresse |
| Kosten Builder Program Mitgliedschaft | Gratis |

---

## Alternativen (wenn Relayer nicht funktioniert)

### Alternative A: Polygon-CLI direkt

Nach T-M04b Erkenntnissen: direkter Web3-Call scheitert an Gnosis Safe.
Bleibt keine praktikable Alternative.

### Alternative B: Notification-only (aktueller Zustand)

Bot erkennt RESOLVED_WON, sendet Telegram-Alert → Onur claimed manuell.
Aktuell de-facto Standard. Kein Automation-Vorteil, aber funktioniert.

**Wann Notification-only als Dauerlösung akzeptabel?**
- Wenn < 1 WON-Position pro Woche → Aufwand minimal
- Wenn Relayer API nicht funktioniert (keine Erfahrungsberichte für unseren Use Case)

### Alternative C: polymarket-redeem Community Script

robottraders.io/blog/polymarket-auto-redeem-python (403 beim Fetch — nicht verifizierbar)
Nutzt dieselbe Relayer-Infrastruktur. Nicht empfohlen (externe Abhängigkeit).

### Alternative D: polymarket-cli (offiziell)

github.com/Polymarket/polymarket-cli — Polymarks offizielle CLI.
Möglicherweise unterstützt sie `redeem` als Kommando. Wäre Fallback wenn py-builder-relayer-client Probleme hat.

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Relayer API Key wird revoked | Sehr niedrig | Hoch | Backup-Key erstellen (max. 100/Adresse) |
| Relayer down/Outage | Niedrig | Mittel | status.polymarket.com monitoren, Notification-Fallback |
| API Breaking Change | Mittel (neue Doku ≠ alte) | Mittel | Versionspinning bei pip install |
| Private Key Exposure (signer-Param) | Niedrig | Extrem hoch | Bereits auf Server (.env), kein neues Risiko |
| Format-Konfusion (Alt vs. Neu) | **HOCH** (schon passiert) | Mittel | Diese Datei als Referenz verwenden |

---

## Empfehlung

### Jetzt sofort möglich: T-M04b in ~1h

**Schritt 1 (5min):** `polymarket.com/settings?tab=api-keys` → "+ Create New"
- Bot-Wallet einloggen, Key erstellen, in Server-.env eintragen

**Schritt 2 (5min):** `pip install py-builder-relayer-client` auf Server

**Schritt 3 (45min):** `claim_all.py` umschreiben
- `RelayClient` mit korrekten Credentials initialisieren
- `redeem_position()` mit Format B (RELAYER_API_KEY, nicht api_creds)
- NegRisk-Bifurkation
- Dry-Run-Test

**Schritt 4 (5min):** Ersten echten Claim testen (kleinste WON-Position)

### Builder Program Leaderboard: Optional, später

Kein Mehrwert für Auto-Claim. Nur relevant wenn wir:
- An Grant-Programm teilnehmen wollen ($2.5M+ Pool)
- Volumen-Attribution für externe Stats wollen

→ Empfehlung: erstmal NICHT beantragen (Ablenkung von PRIO 1).

### Fallback-Plan

Falls Relayer API Probleme hat (Fehler, Authentifizierungsprobleme):
1. Notification-only als Dauerlösung akzeptieren
2. Manuelle Claims via Polymarket UI (<5min/Claim)
3. Bei mehreren WON-Positionen gleichzeitig: Batch-Claim via UI

---

## Offene Fragen

1. **Format A vs. B: Welches ist tatsächlich korrekt für aktuelle Library-Version?**
   Die offizielle Doku zeigt Format B, das .env.example auf GitHub zeigt Format A.
   → Erst beim tatsächlichen `pip install` und Test klären.

2. **RELAYER_API_KEY_ADDRESS: Ist das der ProxyWallet oder EOA?**
   ProxyWallet = `0x700BC51b721F168FF975ff28942BC0E5fAF945eb`
   EOA = abgeleitet aus PRIVATE_KEY
   → Vermutlich ProxyWallet (dieselbe wie POLYMARKET_ADDRESS).

3. **Ist Login auf polymarket.com mit Bot-Wallet möglich?**
   Bot nutzt Magic.link (internen Signer). Direkter MetaMask-Login mit PRIVATE_KEY
   müsste über "Import Private Key" in MetaMask gehen → dann Settings-Zugang.
   Alternative: API-Key-Erstellung via Relayer-API direkt (Gamma-Auth).

4. **Max. Rate-Limit für Relayer-Calls?**
   Dokumentiert: max 100 API-Keys. Rate-Limit pro Key: nicht dokumentiert.

---

## Zusammenfassung

| Frage | Antwort |
|-------|---------|
| Builder Program für Relayer nötig? | **NEIN** — self-service |
| Wo Credentials erstellen? | polymarket.com/settings?tab=api-keys |
| Wartezeit | **0** — sofort |
| Kosten | **Gratis** (gasless) |
| Kritische Korrektur P076 | Host: `relayer-v2`, Auth: RELAYER_API_KEY+ADDRESS statt api_creds |
| T-M04b Aufwand (revidiert) | **~1h** (nicht 2h — kein Antrag nötig) |
| Fallback | Notification-only + manueller Claim |
| Builder Leaderboard | Optional — später, kein PRIO |
