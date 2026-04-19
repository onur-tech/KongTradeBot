# Claim-Fix Research (19.04.2026)

_Zweck: Korrekte Methode für Polymarket-Redemption identifizieren._
_T-M04 Phase 0 fand: `client.redeem(condition_id)` → AttributeError (Methode existiert nicht)._

---

## Aktuelle Situation

**Bug in `claim_all.py`, Zeile 92:**
```python
result = client.redeem(condition_id)  # ← AttributeError: 'ClobClient' has no attribute 'redeem'
```

**Bestätigte Fakten (live verifiziert):**
- `ClobClient` (py-clob-client v0.34.6) hat keine `redeem`-Methode — vollständiges Method-Listing geprüft
- GitHub Issue #139 (50+ Upvotes, seit Jul 2025 offen): "not possible to redeem via py-clob-client SDK"
- Jeder Claim-Versuch seit Inbetriebnahme schlägt fehl — 0 erfolgreiche Claims
- Wuning (heute geclaimed) wurde manuell über Polymarket-UI erledigt
- Auf Server installiert: `py_builder_signing_sdk 0.0.2` ✅, `web3 7.15.0` ✅
- NICHT installiert: `py-builder-relayer-client` ❌

---

## Option A: py-builder-relayer-client (Offiziell, Gasless)

### Analyse

Polymarket bietet seit 2025 eine offizielle "Gasless Transactions" Infrastruktur:
[docs.polymarket.com/trading/gasless](https://docs.polymarket.com/trading/gasless)

Statt direkt auf der Blockchain zu schreiben, sendet man Transactions an Polymarkets Relayer,
der sie ausführt. Der Benutzer bezahlt kein POL für Gas.

**Installation:**
```bash
pip install py-builder-relayer-client  # py-builder-signing-sdk ist bereits installiert
```

**Offizieller Code für Standard-Markets (Python):**
```python
from py_builder_relayer_client.client import RelayClient
from web3 import Web3

CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"        # Conditional Tokens (Polygon)
USDC = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"       # USDC (Polygon)
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"  # NegRisk markets

# Standard Binary Market (negRisk=False)
redeem_tx = {
    "to": CTF,
    "data": Web3().eth.contract(
        address=CTF,
        abi=[{
            "name": "redeemPositions",
            "type": "function",
            "inputs": [
                {"name": "collateralToken",      "type": "address"},
                {"name": "parentCollectionId",   "type": "bytes32"},
                {"name": "conditionId",          "type": "bytes32"},
                {"name": "indexSets",            "type": "uint256[]"}
            ],
            "outputs": []
        }]
    ).encode_abi(
        abi_element_identifier="redeemPositions",
        args=[
            USDC,
            bytes(32),          # HASH_ZERO = 0x000...000
            condition_id_bytes, # bytes.fromhex(condition_id.replace('0x', ''))
            [2]                 # [1]=YES/first outcome, [2]=NO/second outcome
        ]
    ),
    "value": "0"
}
response = client.execute([redeem_tx], "Redeem positions")
response.wait()
```

**NegRisk Markets (negRisk=True) — anderes Contract:**
```python
# NegRiskAdapter hat anderes ABI: nur 2 Parameter statt 4
neg_risk_redeem_tx = {
    "to": NEG_RISK_ADAPTER,
    "data": Web3().eth.contract(
        address=NEG_RISK_ADAPTER,
        abi=[{
            "name": "redeemPositions",
            "type": "function",
            "inputs": [
                {"name": "conditionId",  "type": "bytes32"},
                {"name": "indexSets",    "type": "uint256[]"}
            ],
            "outputs": []
        }]
    ).encode_abi(
        abi_element_identifier="redeemPositions",
        args=[condition_id_bytes, [2]]
    ),
    "value": "0"
}
```

**NegRisk Detection:**
```python
is_neg_risk = position.get("negRisk", False) or position.get("neg_risk", False)
```

**RelayClient Setup:**
```python
# Gleiche Credentials wie ClobClient (Builder-API)
client = RelayClient(
    host="https://relayer.polymarket.com",
    api_creds=ApiCreds(
        api_key=config.api_key,
        api_secret=config.api_secret,
        api_passphrase=config.api_passphrase,
    )
)
```

**Warum `indexSets`?**
- Conditional Token Framework kodiert Outcomes binär: [1] = Outcome 0 (YES), [2] = Outcome 1 (NO)
- Bei Standard-Binary: immer [1] oder [2] (je nach welche Seite man hält)
- Woher wissen wir welche? Aus `position.outcomeIndex` → 0→[1], 1→[2]

**Pro:**
- ✅ Offizielles Polymarket-Werkzeug, aktiv maintained
- ✅ Gasless — kein POL nötig
- ✅ `py_builder_signing_sdk` bereits installiert (dependency)
- ✅ Offizielles Code-Beispiel in Docs vorhanden
- ✅ Handhabt Safe/Proxy-Wallet-Mechanismus automatisch
- ✅ Batch: mehrere Redeems in einem Call möglich

**Contra:**
- ⚠ `py-builder-relayer-client` muss noch installiert werden (1 pip-Befehl)
- ⚠ NegRisk-Bifurkation muss implementiert werden (~30min extra)
- ⚠ `indexSets`-Ableitung aus Position-Daten muss korrekt sein

---

## Option B: Web3 Direct Contract Call

### Analyse

Direkt auf dem CTF-Contract `redeemPositions` aufrufen via Web3.py.

**Technisches Problem — Gnosis Safe:**
GitHub Issue #139 (50+ Upvotes) dokumentiert:

> "This approach does not work in practice for real Polymarket accounts because user positions
> are held by a Safe (proxy multisig). The Safe must execute redeemPositions internally using
> execTransaction, which requires multiple EIP-712 signed parameters."

Polymarket-Nutzer halten keine Tokens direkt in ihrer EOA. Die Tokens liegen im Gnosis Safe
(Proxy Wallet). Ein direkter Web3-Call auf CTF würde scheitern weil:
1. Die EOA hat keine Tokens — der Safe hat sie
2. Der Safe muss `execTransaction` aufrufen, nicht die EOA direkt
3. `execTransaction` braucht: `to`, `value`, `data`, `operation`, `safeTxGas`, `nonce`, EIP-712 Signatur

`web3 7.15.0` ist installiert — aber Safe-Interaktion würde ~5h Implementierungsaufwand bedeuten.

**Pro:**
- ✅ Volle Kontrolle, keine Relayer-Abhängigkeit
- ✅ Web3 bereits installiert

**Contra:**
- ❌ Gnosis Safe `execTransaction` extrem komplex (EIP-712, Nonce-Management)
- ❌ ~5h Implementierungsaufwand
- ❌ Nicht offiziell von Polymarket empfohlen
- ❌ Braucht POL für Gas (nicht gasless)
- ❌ Issue #139 bestätigt dass naiver Web3-Call nicht funktioniert

---

## Option C: Gamma API / REST

### Analyse

Es gibt keinen Redeem-Endpunkt in der Gamma-API oder CLOB-REST-API.
GitHub Issue #139 ist explizit ein Feature-Request für genau das — und ist seit Juli 2025 offen.

**Fazit: Option C existiert nicht.** REST-only Redemption ist schlicht nicht verfügbar.

---

## Option D: robottraders.io Script (Community)

Ein externer Blog-Post (robottraders.io, März 2026) bietet ein fertiges Python-Script:

```python
from polymarket_redeem import redeem_all
redeem_all(private_key, funder_address, signature_type, 
           builder_api_key, builder_secret, builder_passphrase)
```

Intern nutzt es dieselbe Relayer-Infrastruktur wie Option A, aber direkt via
`eth_abi` + `eth_utils` + Raw-HTTP-Call statt offizieller Library.

**Pro:** Fertiger Code, NegRisk-Bifurkation bereits implementiert.
**Contra:** Externe Abhängigkeit, nicht peer-reviewed, wartungsintensiv bei API-Änderungen.

→ **Besser:** Option A mit Polymarket's offiziellem Docs-Code, eigene Implementierung.

---

## Empfehlung

**Option A: py-builder-relayer-client** — eindeutig.

| Kriterium | A (Relayer) | B (Web3 Safe) | C (REST) |
|-----------|------------|--------------|---------|
| Funktioniert? | ✅ Ja | ⚠ Komplex | ❌ Nein |
| Implementierungsaufwand | ~2h | ~5-6h | — |
| Gasless | ✅ Ja | ❌ Nein (POL nötig) | — |
| Offiziell supported | ✅ Ja | ❌ Nein | — |
| Dependencies bereits da | Teilweise | ✅ Web3 | — |
| pip install nötig | 1 Package | 0 | — |
| NegRisk-Support | Implementierbar | Sehr komplex | — |

---

## Implementation-Aufwand

**Option A gesamt: ~2h (heute noch machbar)**

| Schritt | Aufwand |
|---------|---------|
| `pip install py-builder-relayer-client` auf Server | 5 Min |
| RelayClient-Setup in claim_all.py | 30 Min |
| `redeem_position()` umschreiben (Standard + NegRisk) | 45 Min |
| `indexSets`-Ableitung aus Position-Daten | 15 Min |
| Dry-Run testen + Logging | 20 Min |
| Erste echte Claim-Ausführung testen | 10 Min |

---

## Technische Parameter-Ableitung

Für jede Polymarket-Position aus `/positions` API:

```python
condition_id_bytes = bytes.fromhex(position["conditionId"].replace("0x", ""))
outcome_index = position.get("outcomeIndex", 0)  # 0 = YES/first, 1 = NO/second
index_sets = [1 << outcome_index]  # 0→[1], 1→[2]
is_neg_risk = position.get("negRisk", False)

if is_neg_risk:
    contract = NEG_RISK_ADAPTER
    # 2-param ABI
else:
    contract = CTF
    # 4-param ABI mit USDC + HASH_ZERO
```

**Was ist `outcomeIndex`?**
Aus der `data-api.polymarket.com/positions` Response. Alternativ: aus dem Asset-ID ableitbar.
Fallback: für Standard-Binary-Markets probieren wir [2] (NO, die häufig verlorene Seite) dann [1].

---

## Blocker / Offene Fragen

1. **`outcomeIndex` in Positions-API vorhanden?**
   `fetch_redeemable_positions()` in claim_all.py muss prüfen ob das Feld verfügbar ist.
   Fallback-Strategie: beide indexSets probieren [1] dann [2].

2. **NegRisk-Detection reliable?**
   `position.negRisk` könnte nicht immer gesetzt sein. Fallback: CTF-Try → catch Error → NEG_RISK retry.

3. **Builder-API-Credentials dieselben wie für Trading?**
   Ja — RelayClient nutzt dieselben api_key/api_secret/api_passphrase wie ClobClient.
   Diese sind bereits in Config verfügbar.

4. **Batch-Claim pro Call?**
   `client.execute([tx1, tx2, ...], "Batch redeem")` — mehrere Redeems in einem Relayer-Call.
   Spart API-Calls, aber: bei Fehler scheitert der ganze Batch. Besser: einzeln mit try/except.

---

## Verifikations-Plan

**Kein Testnet verfügbar** — Polymarket läuft nur auf Polygon Mainnet.

**Test-Strategie:**
1. `--dry` Flag ausführen: zeigt welche Positionen geclaimed würden, ohne tatsächlich zu senden
2. Kleinste echte Position suchen (z.B. < $5 gewonnen)
3. Einzelnen Claim live ausführen, Transaction-Hash loggen
4. Auf Polygonscan verifizieren: USDC-Transfer zum Wallet?
5. Dashboard prüfen: Position verschwindet aus Portfolio?

**Wichtig:** Fehlgeschlagene Claims sind harmlos (kein USDC verloren, nur Gas/Relayer-Versuch).
Richtig schlimm wäre doppelter Claim (nicht möglich — Contract verhindert das on-chain).

---

## Zusammenfassung

| Frage | Antwort |
|-------|---------|
| Empfohlene Option | **A (py-builder-relayer-client)** |
| Aufwand | **~2h** |
| Libraries nötig | `py-builder-relayer-client` (pip install), Web3 + py_builder_signing_sdk bereits da |
| Testnet vorhanden | ❌ Nein — nur Polygon Mainnet |
| Heute Abend implementierbar | ✅ Ja, ~2h |
| Kritische Fallstricke | NegRisk-Bifurkation + `indexSets`-Ableitung |
| Kann morgen warten? | ✅ Ja — keine neuen WON-Positions heute Nacht erwartet |
