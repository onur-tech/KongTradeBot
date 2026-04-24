# Phase 4 Analyse — Copy-Trading Strategy Port zum Plugin-Interface

**Branch:** phase-4-copy-trading-port-v2  
**Datum:** 2026-04-24

---

## 1. Aktuelle Struktur von `strategies/copy_trading.py`

Datei: 766 Zeilen

### Datenklassen

| Klasse | Zweck |
|--------|-------|
| `WalletPerformance` | Win-Rate-Tracking + Decay/Trend-Decline-Detection pro Wallet |
| `CopyOrder` | Order-Dataclass (signal, size_usdc, dry_run, wallet_multiplier, is_multi_signal) |
| `CopyTradingStrategy` | Hauptklasse — Signal-Aggregation, Filter, Risk-Check, Order-Dispatch |

### Konfigurationsblöcke (alle hardcoded in der Quelldatei)

| Dict | Zeilen | Inhalt |
|------|--------|--------|
| `WALLET_MULTIPLIERS` | 162–233 | 25+ Wallet-Adressen → Kapital-Multiplikator (0.3–3.0) |
| `WALLET_CATEGORIES` | 68–87 | Wallet → Kategorie-Liste (sports/crypto/politics/broad) |
| `_CAT_KEYWORDS` | 89–103 | Kategorie → Keyword-Liste (sports, crypto, politics, geopolitics, macro, weather) |
| `WALLET_NAMES` | 268–284 | Wallet-Adresse → lesbarer Name (15 Einträge) |

### Konstanten und Env-Vars

| Variable | Default | Quelle |
|----------|---------|--------|
| `AGGREGATION_WINDOW_S` | `60` | Hardcoded |
| `MULTI_SIGNAL_MULTIPLIERS` | `{1:1.0, 2:1.5, 3:2.0}` | Hardcoded |
| `HERD_FRACTION` | `0.50` | Hardcoded |
| `EARLY_ENTRY_MULTIPLIER` | `1.5` | Hardcoded |
| `EARLY_ENTRY_VOLUME_USD` | `10_000` | Hardcoded |
| `MAX_POSITIONS_TOTAL` | `999` | `os.environ.get("MAX_POSITIONS_TOTAL")` |
| `MIN_MARKT_VOLUMEN_USD` | `0` | `os.environ.get("MIN_MARKT_VOLUMEN")` |
| `_CATEGORY_BLACKLIST` | `[]` | `os.environ.get("CATEGORY_BLACKLIST")` kommagetrennt |
| `_CRYPTO_DAILY_SINGLE_SIGNAL` | `True` | `os.environ.get("CRYPTO_DAILY_SINGLE_SIGNAL")` |
| `COPY_EVENT_CAP` | `3` | `os.environ.get("COPY_EVENT_CAP")` (inline in `_process_signal`) |
| `DEFAULT_WALLET_MULTIPLIER` | `0.5` | Hardcoded (überschreibbar per `WALLET_WEIGHTS` JSON) |
| `WALLET_WEIGHTS` | `{}` | `os.environ.get("WALLET_WEIGHTS")` JSON mit Prefix-Matching |

### Hauptfunktionsfluss

```
handle_signal(TradeSignal)
  → Signal in _agg_buffer[key] buffern
  → asyncio.create_task(_flush_aggregated(key)) nach AGGREGATION_WINDOW_S

_flush_aggregated(key)
  → Herdentrieb-Check (>50% Wallets)
  → MIN_WALLET-Check (Crypto-Daily: 1, sonst: 2)
  → _process_signal(base_signal, extra_multiplier)

_process_signal(signal, extra_multiplier)
  → CATEGORY_BLACKLIST-Check
  → OPPOSING_SIDE + EVENT_CAP Guard
  → WALLET_CATEGORY_FILTER (should_copy_trade)
  → MIN_MARKT_VOLUMEN-Check
  → MAX_POSITIONS_TOTAL-Check
  → Win-Rate-Decay-Check (WalletPerformance.is_decaying)
  → Multiplikator berechnen (wallet × extra × early_bonus)
  → risk_manager.evaluate(scaled_signal)  ← Shared Safety Layer
  → CopyOrder erstellen
  → on_copy_order(order) Callback
```

---

## 2. Was live_engine/main.py aufruft

Datei: `live_engine/main.py`

| Zeile | Call |
|-------|------|
| 59 | `from strategies.copy_trading import CopyTradingStrategy, CopyOrder` |
| 643 | `strategy = CopyTradingStrategy(config, risk)` |
| 1017 | `monitor.on_new_trade = strategy.handle_signal` |
| 1157 | `monitor.on_whale_sell = strategy.handle_whale_sell` |

Zusätzlich setzt `live_engine/main.py` diverse Callbacks auf dem Strategy-Objekt:
- `strategy.on_copy_order` → ExecutionEngine
- `strategy.get_open_positions_count` → für MAX_POSITIONS_TOTAL
- `strategy.get_open_positions` → für OPPOSING_SIDE/EVENT_CAP Guard
- `strategy.on_whale_exit` → für Whale-Exit-Copy
- `strategy.on_wallet_warning` → Telegram-Alert
- `strategy.on_herd_alert` → Telegram-Alert

---

## 3. Wallet-Config-Location

Alle Wallet-Parameter sind aktuell **direkt in `strategies/copy_trading.py` hardcoded**:
- Änderung eines Multiplikators = Code-Änderung + Commit + Deployment
- Kein Reload ohne Bot-Neustart
- WALLET_WEIGHTS env-var ermöglicht Teilüberschreibung, aber umständlich

**Ziel in Phase 4:** Extraktion in `config/strategies/copy_trading.yaml` — editierbar ohne Code-Änderung.

---

## 4. Safety-Module-Nutzung

| Modul | Import | Nutzung |
|-------|--------|---------|
| `core.risk_manager` | Direkt | `risk_manager.evaluate(scaled_signal)` in `_process_signal()` |
| `utils.error_handler` | Optional (`try/except ImportError`) | `_handle_error()` in `_safe_call()` für Callback-Fehler |
| `utils.signal_tracker` | Optional (`try/except ImportError`) | `log_signal()` für jede Signal-Entscheidung (COPIED/SKIPPED) |

Der RiskManager wird **nicht** in der Strategie instantiiert — er wird von `live_engine/main.py` erstellt und per Konstruktor übergeben (`CopyTradingStrategy(config, risk)`). Das ist die korrekte Shared-Safety-Layer-Architektur aus Phase 3.

---

## 5. Plugin-Interface (core/plugin_base.py)

```python
class StrategyPlugin(abc.ABC):
    def __init__(self, mode: PluginMode = "live") -> None: ...
    
    @abc.abstractmethod
    async def on_signal(self, signal: Signal) -> Optional[Order]: ...
    
    @abc.abstractmethod
    async def on_fill(self, fill: Fill) -> None: ...
    
    @abc.abstractmethod
    async def on_tick(self, tick: Tick) -> None: ...
```

Plugin-eigene Dataclasses: `Tick`, `Signal`, `Order`, `Fill` — unterscheiden sich von den bestehenden `TradeSignal`, `CopyOrder` aus `strategies/copy_trading.py`.

**Herausforderung in Phase 4:** Bridge zwischen `TradeSignal` (WalletMonitor) → `Signal` (Plugin-Interface) und `Order` (Plugin) → `CopyOrder` (ExecutionEngine) bauen, ohne live_engine stark umzuschreiben.

---

## 6. Phase-4-Umsetzungsplan

### 2.2 YAML-Config-Extraktion
- Neue Datei: `config/strategies/copy_trading.yaml`
- Neues Modul: `core/strategy_config.py` (YAML-Loader mit `importlib.resources` oder `pathlib`)
- Inhalt: `wallet_multipliers`, `wallet_categories`, `wallet_names`, `cat_keywords`, alle Konstanten

### 2.3 CopyTradingPlugin
- Neue Datei: `strategies/copy_trading_plugin.py`
- Subklasse von `StrategyPlugin`
- Adapter-Pattern: `on_signal(Signal)` → intern `handle_signal(TradeSignal)`-Logik
- Delegiert Risk-Check an `RiskManager` (wird per Konstruktor übergeben)
- 15+ Tests

### 2.4 live_engine Integration
- Backup aktueller `live_engine/main.py`
- Import-Swap: `CopyTradingPlugin` statt `CopyTradingStrategy`
- Callbacks bleiben gleich (Plugin hat dieselben Callback-Attribute)

### 2.5 Regression Test
- Plugin-Output vs. Legacy-Strategy bei identischen Signalen

---

*Analyse abgeschlossen. Weiter mit 2.2 YAML-Extraktion.*
