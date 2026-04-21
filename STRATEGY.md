# KongTrade Bot — Strategy

## Aktuelle Config
Stand: 21.04.2026

```
MAX_PORTFOLIO_PCT     = 0.70   (war 0.50 — erhöht nach vollständiger Kalibrierung)
COPY_SIZE_MULTIPLIER  = 0.15   (bestätigt — bewusst beibehalten)
```

Begründung:
- MAX_PORTFOLIO_PCT 0.50 → 0.70: Nach Kalibrierung und 2 Wochen Live-Betrieb.
  Budget $683 USDC × 70% = $478 max investierbar.
  Aktuell invested $404 → $74 freier Spielraum für neue Trades.
- COPY_SIZE_MULTIPLIER 0.15: Balanciert Rendite vs. Risiko nach $137 Verlust-Erfahrung.
  Entspricht ~$30 Trade-Größe bei $200 Signal.
