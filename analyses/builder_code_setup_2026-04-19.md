# KongTrade Builder-Code Setup (19.04.2026)

_Dokumentation der Builder-Profil-Erstellung auf Polymarket._
_NICHT in .env eingetragen heute — Integration als separater Task (T-M10)._

---

## Was ist der Builder-Code?

Ein `bytes32`-Identifier der bei jedem Order-Submit mit übermittelt wird.
Polymarket attributiert das Handelsvolumen dem Builder-Profil — keine Wallet-Kontrolle,
keine Claim-Berechtigung, kein Signer-Mechanismus. Reine Volume-Attribution.

**Zweck:** Leaderboard-Position + zukünftige Fee-Rebates + Grant-Eligibility ($2.5M Pool).

---

## KongTrade Builder-Profil

| Feld | Wert |
|------|------|
| **Name** | KongTrade |
| **Builder-Code** | `0xc58cb20bdf869598b66c226dc3848e0d25d8de8671ec6f7061247d010767c6de` |
| **Builder-API-Key** | `019da5f1-fb1d-790a-802f-46eeb0bc36f5` |
| **Address** | `0x700bc51b721f168ff975ff28942bc0e5faf945eb` (Proxy Wallet) |
| **Status** | Active |
| **Maker Fee** | 0% |
| **Taker Fee** | 0% |
| **Erstellt** | 2026-04-19 |

---

## Was der Builder-Code NICHT kann

**Auto-Claim ermöglichen:**
Der Builder-Code ist ein reines Attribution-Label. Er gibt keinerlei Rechte auf
Wallet-Inhalte, Positions-Redemption oder API-Claim-Calls.

Hintergrund (KB P082 — Custodial Architecture):
- Positionen liegen im Gnosis Safe (Proxy Wallet `0x700bc5...`)
- Der Safe-Owner (Magic.link EOA `0xd7869A5C...`) ist der einzige autorisierte Signer
- Builder-Code enthält keinen privaten Schlüssel und kann nichts unterzeichnen
- Claim-Weg: RelayClient mit PRIVATE_KEY (T-M04b) — unabhängig vom Builder-Code

**Ownership-Problem lösen:**
Falls PRIVATE_KEY und Magic.link-EOA jemals auseinanderfallen (z.B. bei Wallet-Migration),
löst der Builder-Code das nicht. Er ist an die Adresse `0x700bc5...` gebunden, nicht an einen Key.

---

## Was der Builder-Code KANN

**Trades labeln:**
Jeder über KongBot gesendete Order kann das `builderCode`-Feld enthalten:
```python
response = client.create_and_post_order(
    OrderArgs(
        token_id="0x...",
        price=0.55, size=100, side=BUY,
        builder_code="0xc58cb20bdf869598b66c226dc3848e0d25d8de8671ec6f7061247d010767c6de",
    )
)
```

**Leaderboard-Attribution:**
Handelsvolumen wird auf builders.polymarket.com unter "KongTrade" sichtbar.
Competitive ranking gegen andere Builder.

**Fee-Rebates (zukünftig):**
Polymarket-Grants-Programm zahlt Top-Builder wöchentlich aus.
Aktuell 0% Maker/Taker Fee für KongTrade (kein Vorteil gegenüber Normal-User da
normale Polymarket-Accounts auch 0% haben, aber Struktur für spätere Boni steht).

**Builder-API-Key (019da5f1...):**
Dieser Key ist der Auth-Schlüssel für Relayer-API-Calls (RELAYER_API_KEY).
Er ist für das gleiche Zweck wie in T-M04b dokumentiert.

---

## Zukünftige Integration (T-M10, niedrige Prio)

### .env-Ergänzung (NICHT HEUTE)

```bash
# In .env hinzufügen wenn T-M10 umgesetzt wird:
POLY_BUILDER_CODE=0xc58cb20bdf869598b66c226dc3848e0d25d8de8671ec6f7061247d010767c6de
```

### Code-Änderung in execution_engine.py

```python
# In create_and_post_order() — optional, wenn py-clob-client supportet:
order_args = OrderArgs(
    token_id=asset_id,
    price=price,
    size=size,
    side=side,
    builder_code=os.getenv("POLY_BUILDER_CODE"),  # None wenn nicht gesetzt → ignoriert
)
```

**Prüfen ob py-clob-client das Feld kennt:**
```bash
python3 -c "from py_clob_client.clob_types import OrderArgs; help(OrderArgs)"
# Falls 'builder_code' im Signature: Integration möglich
# Falls nicht: py-clob-client updaten oder rohe Order-Struct bauen
```

### Wann implementieren?

Erst wenn:
1. T-M04b vollständig live (Auto-Claim läuft)
2. T-M04d aktiv (Take-Profit feuert)
3. Bot stabil ≥ 2 Wochen

Builder-Code bringt keinen operativen Vorteil — nur Leaderboard-Sichtbarkeit.
Nicht vor stabilem Bot-Betrieb.

---

## Zusammenfassung

| Frage | Antwort |
|-------|---------|
| Kann Builder-Code Claims ermöglichen? | ❌ NEIN |
| Ist der Builder-API-Key der RELAYER_API_KEY? | ✅ JA (gleicher Key) |
| Sofort in .env? | ❌ NEIN — T-M10 später |
| Leaderboard-Attribution sofort? | ❌ Erst nach T-M10 Integration im Code |
| Kosten? | ✅ Gratis (0% Fee) |
| Nächster Schritt? | T-M10 nach Bot-Stabilisierung (≥2 Wochen live) |
