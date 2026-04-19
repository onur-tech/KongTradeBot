# T-M09b Implementation: Multiplier-Anpassung April#1 Sports + HOOK

_Fertig: 2026-04-19 — bereit für Server-CC nach T-M04d_
_Basis: HOOK/April#1-Verifikation (analyses/hook_april_sports_verification_2026-04-19.md, KB P077)_

---

## KONTEXT

**Was ist das Problem:**
Zwei Wallets haben 2.0x-Multiplier ohne externe WR-Verifikation bekommen.
Externe Recherche (19.04.2026) ergab:

| Wallet | Alias | Aktuell | Neu | Grund |
|--------|-------|---------|-----|-------|
| 0x492442... | April#1 Sports | 2.0x | **0.3x** | Lifetime PnL -$9.8M, WR 46.7% (HF-8 FAIL) |
| 0x0b7a60... | HOOK | 2.0x | **1.0x** | Nur 46 Trades (unter HF-1 Minimum), WR diskrepant |

**Risiko-Kalkül April#1 Sports bei 2.0x:**
Position-Size-Bot mit $200K–$700K Einzeltrades. Bei 2.0x-Kopie kopieren
wir jeden "NBA Spread" mit doppeltem Weight — und der Bot hat WR 46.7%.
Ein schlechtes Wochenende → überproportionaler Schaden für KongBot.

---

## IMPLEMENTIERUNG (10min, eine Datei)

**Datei:** `strategies/copy_trading.py`

### Änderung 1: April#1 Sports 2.0 → 0.3

```python
# VORHER (Zeile ~82-83):
    # April#1 Sports — 65% Win Rate → 2x
    "0x492442eab586f242b53bda933fd5de859c8a3782": 2.0,

# NACHHER:
    # April#1 Sports — WATCHING 0.3x
    # RECAL 2026-04-19 T-M09b: Extern WR 46.7% (Cointrenches), Lifetime PnL -$9.8M
    # HF-8 FAIL + HF-10 HFT-Bot. Review: T-D109 (2026-05-19). Siehe KB P077.
    "0x492442eab586f242b53bda933fd5de859c8a3782": 0.3,
```

### Änderung 2: HOOK 2.0 → 1.0

```python
# VORHER (Zeile ~92-93):
    # HOOK → 2x
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 2.0,

# NACHHER:
    # HOOK — Tier B 1.0x
    # RECAL 2026-04-19 T-M09b: Nur 46 Trades (unter HF-1 100-Trade-Minimum),
    # WR diskrepant (38.5% vs 67%). Review: T-D109 (2026-05-19). Siehe KB P077.
    "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 1.0,
```

### Verifikation nach Änderung

```bash
cd /root/KongTradeBot
grep -A2 '0x492442\|0x0b7a60' strategies/copy_trading.py
# Expected:
# "0x492442eab586f242b53bda933fd5de859c8a3782": 0.3,
# "0x0b7a6030507efe5db145fbb57a25ba0c5f9d86cf": 1.0,
```

### Bot-Reload

```bash
# Bot-Prozess braucht Reload damit neue Multiplier greifen:
# (je nach wie Bot läuft)
systemctl restart kong-bot
# oder
kill $(pgrep -f 'python.*main.py') && cd /root/KongTradeBot && python3 main.py --live &
```

---

## DEPLOYMENT

```bash
git add strategies/copy_trading.py
git commit -m "fix(wallets): T-M09b Multiplier-Kalibrierung April#1 Sports 2.0x->0.3x + HOOK 2.0x->1.0x

April#1 Sports: extern WR 46.7% (Cointrenches), Lifetime PnL -9.8M USDC
HF-8 FAIL (WR < 55%) + HF-10 (HFT-Bot-Muster). WATCHING 0.3x bis T-D109.

HOOK: nur 46 Trades (unter HF-1 100-Trade-Minimum), WR diskrepant
(38.5% 0xinsider vs 67% predicts.guru). Tier B 1.0x bis T-D109.

Regel (KB P077): Multiplier >= 1.5x braucht externen WR-Nachweis >= 55%."
git push
```

---

## CRITICAL STOPS

- Kein Stop nötig — nur Konfigurationsänderung, kein Risiko
- Offene Positionen von diesen Wallets werden NICHT beeinflusst (nur neue Signale)

---

## ABSCHLUSSBERICHT (nach Implementation)

1. Grep-Output der veränderten Zeilen?
2. Bot-Reload erfolgreich?
3. Nächstes Signal von April#1 Sports/HOOK: wird 0.3x / 1.0x angewendet?
