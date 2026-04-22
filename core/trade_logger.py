"""
Trade Logger — Phase 1 Foundation Build
SQLite-basiertes Trade-Metadaten-Schema (Strategic Audit 2026-04-22, Teil C §1).

Additive zum bestehenden trades_archive.json — keine Breaking Changes.
Alle neuen Trades werden mit 40+ Feldern geloggt.
Bestehende Einträge werden via migrate_from_archive() importiert (fehlende Felder = NULL).
"""

import sqlite3
import json
import uuid
import time
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

_BASE = Path(__file__).parent.parent
DB_PATH = _BASE / "data" / "trades.db"

_lock = threading.Lock()

# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id         TEXT UNIQUE NOT NULL,
    source_wallet     TEXT,
    market_id         TEXT,
    token_id          TEXT,
    side              TEXT,
    price             REAL,
    size_usdc         REAL,
    detected_at       TEXT,
    market_question   TEXT,
    outcome           TEXT,
    market_volume_usd REAL,
    is_early_entry    INTEGER DEFAULT 0,
    tx_hash           TEXT,
    strategy          TEXT DEFAULT 'COPY',
    created_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trades (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id         TEXT UNIQUE NOT NULL,
    parent_signal_id TEXT REFERENCES signals(signal_id),

    -- Identifiers & Context
    triggering_wallets TEXT,
    market_id          TEXT,
    condition_id       TEXT,
    outcome_token_id   TEXT,
    event_category     TEXT,
    event_end_ts       TEXT,
    market_end_ts      TEXT,
    strategy_version   TEXT DEFAULT 'v0.6',
    bot_build_hash     TEXT,
    strategy           TEXT DEFAULT 'COPY',
    is_dry_run         INTEGER DEFAULT 1,

    -- Signal Attribution
    signal_count                    INTEGER DEFAULT 1,
    signal_boost_applied            REAL    DEFAULT 1.0,
    herding_indicator_value         REAL,
    triggering_wallets_trust_scores TEXT,
    triggering_wallets_roi_30d      TEXT,
    time_since_first_whale_signal_s REAL,
    latency_signal_to_submit_ms     REAL,

    -- Pre-Trade Market State
    implied_prob_market  REAL,
    model_prob_estimate  REAL,
    edge_expected        REAL,
    market_volume_24h    REAL,
    market_volume_total  REAL,
    orderbook_bid        REAL,
    orderbook_ask        REAL,
    orderbook_spread     REAL,
    orderbook_depth_top5 TEXT,
    mid_price            REAL,
    tick_size            REAL,
    neg_risk_flag        INTEGER DEFAULT 0,

    -- Sizing
    bankroll_before               REAL,
    kelly_fraction_full           REAL,
    kelly_fraction_applied        REAL,
    position_size_usd             REAL,
    position_fraction_of_bankroll REAL,
    cap_hit_flag                  TEXT,

    -- Execution
    side                     TEXT,
    order_type               TEXT DEFAULT 'GTC',
    intended_price           REAL,
    filled_price             REAL,
    filled_size              REAL,
    slippage_bps             REAL,
    latency_submit_to_ack_ms REAL,
    latency_ack_to_fill_ms   REAL,
    fees                     REAL DEFAULT 0.0,
    gas_cost                 REAL DEFAULT 0.0,
    maker_taker_flag         TEXT,
    signature_type_used      INTEGER,
    order_id                 TEXT,
    tx_hash                  TEXT,

    -- Post-Trade (updated via log_trade_update)
    MAE_price                REAL,
    MFE_price                REAL,
    MAE_usd                  REAL,
    MFE_usd                  REAL,
    time_to_peak_favorable_s REAL,
    time_to_peak_adverse_s   REAL,

    -- Exit
    exit_ts                  TEXT,
    exit_price               REAL,
    exit_size                REAL,
    exit_reason              TEXT,
    whale_exit_timing        TEXT,
    holding_period_s         REAL,
    realized_pnl_usd         REAL,
    realized_pnl_r_multiple  REAL,
    capture_ratio            REAL,

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS wallet_snapshots (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address       TEXT    NOT NULL,
    snapshot_date        TEXT    NOT NULL,
    total_trades         INTEGER DEFAULT 0,
    wins                 INTEGER DEFAULT 0,
    losses               INTEGER DEFAULT 0,
    win_rate             REAL,
    roi_30d              REAL,
    roi_90d              REAL,
    rolling_sharpe_30d   REAL,
    beta_alpha           REAL,
    beta_beta_param      REAL,
    lower_ci95           REAL,
    wallet_overall_score REAL,
    cusum_alarm          INTEGER DEFAULT 0,
    attributed_pnl       REAL    DEFAULT 0.0,
    avg_edge_realized    REAL,
    created_at           TEXT    DEFAULT (datetime('now')),
    UNIQUE(wallet_address, snapshot_date)
);

CREATE TABLE IF NOT EXISTS cohort_attributes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id              TEXT UNIQUE REFERENCES trades(trade_id),
    event_category        TEXT,
    hour_of_day_utc       INTEGER,
    liquidity_tier        TEXT,
    signal_count_bin      TEXT,
    holding_period_bin    TEXT,
    signal_score_quantile INTEGER,
    created_at            TEXT DEFAULT (datetime('now'))
);

-- ── Views ─────────────────────────────────────────────────────────────────────

CREATE VIEW IF NOT EXISTS cohort_by_category AS
SELECT
    COALESCE(event_category, 'Unknown') AS event_category,
    COUNT(*) AS total_trades,
    COUNT(CASE WHEN exit_ts IS NOT NULL THEN 1 END) AS closed_trades,
    COUNT(CASE WHEN exit_ts IS NULL     THEN 1 END) AS open_trades,
    SUM(CASE WHEN realized_pnl_usd > 0 AND exit_ts IS NOT NULL THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 * SUM(CASE WHEN realized_pnl_usd > 0 AND exit_ts IS NOT NULL THEN 1 ELSE 0 END) /
          NULLIF(COUNT(CASE WHEN exit_ts IS NOT NULL THEN 1 END), 0), 1) AS win_rate_pct,
    ROUND(SUM(COALESCE(realized_pnl_usd, 0)), 2) AS total_pnl_usd,
    ROUND(SUM(COALESCE(realized_pnl_usd, 0)) /
          NULLIF(SUM(COALESCE(position_size_usd, 0)), 0), 4) AS roi,
    ROUND(AVG(COALESCE(slippage_bps, 0)), 1) AS avg_slippage_bps,
    ROUND(AVG(CASE WHEN holding_period_s > 0 THEN holding_period_s END) / 3600.0, 1)
          AS avg_holding_hours
FROM trades
GROUP BY COALESCE(event_category, 'Unknown')
ORDER BY total_trades DESC;

CREATE VIEW IF NOT EXISTS wallet_attribution AS
SELECT
    t.triggering_wallets AS wallet,
    COUNT(DISTINCT t.trade_id) AS attributed_trades,
    ROUND(SUM(COALESCE(t.realized_pnl_usd, 0)), 2) AS total_pnl_usd,
    ROUND(SUM(COALESCE(t.position_size_usd, 0)), 2) AS total_stake_usd,
    ROUND(SUM(COALESCE(t.realized_pnl_usd, 0)) /
          NULLIF(SUM(CASE WHEN t.exit_ts IS NOT NULL THEN t.position_size_usd END), 0), 4)
          AS roi,
    SUM(CASE WHEN t.realized_pnl_usd > 0 AND t.exit_ts IS NOT NULL THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 *
          SUM(CASE WHEN t.realized_pnl_usd > 0 AND t.exit_ts IS NOT NULL THEN 1 ELSE 0 END) /
          NULLIF(COUNT(CASE WHEN t.exit_ts IS NOT NULL THEN 1 END), 0), 1) AS win_rate_pct,
    ROUND(AVG(COALESCE(t.edge_expected, 0)), 4) AS avg_edge_expected
FROM trades t
WHERE t.triggering_wallets IS NOT NULL
GROUP BY t.triggering_wallets
ORDER BY total_pnl_usd DESC;

CREATE VIEW IF NOT EXISTS slippage_histogram AS
SELECT
    CASE
        WHEN slippage_bps IS NULL  THEN 'unknown'
        WHEN slippage_bps < 0     THEN 'negative (better fill)'
        WHEN slippage_bps < 25    THEN '0–25 bps'
        WHEN slippage_bps < 50    THEN '25–50 bps'
        WHEN slippage_bps < 100   THEN '50–100 bps'
        WHEN slippage_bps < 200   THEN '100–200 bps'
        WHEN slippage_bps < 300   THEN '200–300 bps'
        ELSE '>300 bps (reject threshold)'
    END AS bucket,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM trades), 0), 1) AS pct
FROM trades
GROUP BY bucket
ORDER BY MIN(COALESCE(slippage_bps, 9999));

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_trades_market_id  ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_trades_category   ON trades(event_category);
CREATE INDEX IF NOT EXISTS idx_trades_exit_ts    ON trades(exit_ts);
CREATE INDEX IF NOT EXISTS idx_trades_order_id   ON trades(order_id);
CREATE INDEX IF NOT EXISTS idx_trades_signal_id  ON trades(parent_signal_id);
CREATE INDEX IF NOT EXISTS idx_signals_wallet    ON signals(source_wallet);
CREATE INDEX IF NOT EXISTS idx_wallet_snap       ON wallet_snapshots(wallet_address, snapshot_date);
"""


# ── Connection helper ─────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # FK enforcement intentionally OFF: parent_signal_id is a soft reference.
    # Enabling it causes silent INSERT aborts when signals table is out of sync
    # (e.g. bot restart loses _order_trade_map, no signal pre-logged).
    return conn


# ── TradeLogger ───────────────────────────────────────────────────────────────

class TradeLogger:
    """
    Zentrale Logging-Klasse für alle Trade-Metadaten.
    Thread-safe via _lock. Hält intern eine Map order_id → trade_id
    damit Exit-Events die zugehörigen Einträge finden können.
    """

    def __init__(self, db_path: Optional[Path] = None):
        global DB_PATH
        if db_path:
            DB_PATH = db_path
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        # order_id → trade_id für Exit-Lookup
        self._order_trade_map: Dict[str, str] = {}

    def _init_db(self):
        with _lock:
            conn = _get_conn()
            try:
                conn.executescript(_SCHEMA_SQL)
                conn.commit()
            finally:
                conn.close()

    # ── Public API ────────────────────────────────────────────────────────────

    def log_signal(self, signal) -> str:
        """
        Loggt ein eingehendes TradeSignal. Gibt die signal_id zurück.
        signal kann ein TradeSignal-Dataclass oder dict sein.
        """
        sid = str(uuid.uuid4())
        row = {
            "signal_id":       sid,
            "source_wallet":   _g(signal, "source_wallet"),
            "market_id":       _g(signal, "market_id"),
            "token_id":        _g(signal, "token_id"),
            "side":            _g(signal, "side"),
            "price":           _gf(signal, "price"),
            "size_usdc":       _gf(signal, "size_usdc"),
            "detected_at":     _dt(_g(signal, "detected_at")),
            "market_question": _g(signal, "market_question", "")[:200],
            "outcome":         _g(signal, "outcome"),
            "market_volume_usd": _gf(signal, "market_volume_usd"),
            "is_early_entry":  int(bool(_g(signal, "is_early_entry", False))),
            "tx_hash":         _g(signal, "tx_hash"),
            "strategy":        "COPY",
        }
        with _lock:
            conn = _get_conn()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO signals "
                    "(signal_id,source_wallet,market_id,token_id,side,price,size_usdc,"
                    "detected_at,market_question,outcome,market_volume_usd,"
                    "is_early_entry,tx_hash,strategy) VALUES "
                    "(:signal_id,:source_wallet,:market_id,:token_id,:side,:price,:size_usdc,"
                    ":detected_at,:market_question,:outcome,:market_volume_usd,"
                    ":is_early_entry,:tx_hash,:strategy)",
                    row
                )
                conn.commit()
            finally:
                conn.close()
        return sid

    def log_trade_entry(
        self,
        signal_id: str,
        order_id: str,
        *,
        signal=None,
        order=None,
        result=None,
        category: str = "",
        is_dry_run: bool = True,
        bankroll: float = 0.0,
        submit_ts: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Loggt einen Trade-Entry. Gibt trade_id zurück und registriert
        order_id → trade_id für spätere Exit-Lookups.
        """
        trade_id = str(uuid.uuid4())
        extra = extra or {}
        now_ts = time.time()
        submit_ts = submit_ts or now_ts

        sig_price  = _gf(signal, "price") if signal else None
        pos_size   = _gf(order, "size_usdc") if order else None
        source_w   = _g(signal, "source_wallet") if signal else None
        market_id  = _g(signal, "market_id") if signal else None
        token_id   = _g(signal, "token_id") if signal else None
        outcome    = _g(signal, "outcome") if signal else None
        side       = _g(signal, "side") if signal else None
        tx_hash    = _g(result, "order_id") if result else None
        filled_p   = _gf(result, "filled_price") if result else sig_price
        is_multi   = bool(_g(order, "is_multi_signal", False)) if order else False
        multiplier = _gf(order, "wallet_multiplier", 1.0) if order else 1.0
        boost      = multiplier if is_multi else 1.0
        wallet_j   = json.dumps([source_w]) if source_w else None
        mkt_vol    = _gf(signal, "market_volume_usd") if signal else None

        latency_ms = extra.get("latency_signal_to_submit_ms")

        row = {
            "trade_id":                     trade_id,
            "parent_signal_id":             signal_id,
            "triggering_wallets":           wallet_j,
            "market_id":                    market_id,
            "condition_id":                 market_id,
            "outcome_token_id":             token_id,
            "event_category":               category or extra.get("category"),
            "strategy":                     extra.get("strategy", "COPY"),
            "is_dry_run":                   int(is_dry_run),
            "signal_count":                 extra.get("signal_count", 1),
            "signal_boost_applied":         boost,
            "market_volume_24h":            mkt_vol,
            "implied_prob_market":          sig_price,
            "model_prob_estimate":          extra.get("model_prob_estimate"),
            "edge_expected":                extra.get("edge_expected",
                                                (_gf(extra, "model_prob", sig_price or 0)
                                                 - (sig_price or 0)) or None),
            "bankroll_before":              bankroll,
            "kelly_fraction_applied":       extra.get("kelly_fraction_applied"),
            "kelly_fraction_full":          extra.get("kelly_fraction_full"),
            "position_size_usd":            pos_size,
            "position_fraction_of_bankroll": round(pos_size / bankroll, 6)
                                              if (pos_size and bankroll) else None,
            "cap_hit_flag":                 extra.get("cap_hit_flag"),
            "side":                         side,
            "order_type":                   extra.get("order_type", "GTC"),
            "intended_price":               sig_price,
            "filled_price":                 filled_p,
            "filled_size":                  pos_size,
            "slippage_bps":                 extra.get("slippage_bps"),
            "latency_signal_to_submit_ms":  latency_ms,
            "order_id":                     order_id,
            "tx_hash":                      tx_hash,
            "strategy_version":             "v0.6",
        }

        with _lock:
            conn = _get_conn()
            try:
                cols = ", ".join(row.keys())
                placeholders = ", ".join(f":{k}" for k in row.keys())
                conn.execute(
                    f"INSERT OR IGNORE INTO trades ({cols}) VALUES ({placeholders})",
                    row
                )
                conn.commit()
            finally:
                conn.close()

        self._order_trade_map[order_id] = trade_id
        self._write_cohort_attributes(trade_id, category, signal, extra)
        return trade_id

    def log_trade_update(
        self,
        trade_id: str,
        *,
        MAE_price: Optional[float] = None,
        MFE_price: Optional[float] = None,
        MAE_usd: Optional[float] = None,
        MFE_usd: Optional[float] = None,
        time_to_peak_favorable_s: Optional[float] = None,
        time_to_peak_adverse_s: Optional[float] = None,
    ):
        """Aktualisiert MAE/MFE während die Position offen ist."""
        updates: Dict[str, Any] = {}
        if MAE_price is not None:         updates["MAE_price"] = MAE_price
        if MFE_price is not None:         updates["MFE_price"] = MFE_price
        if MAE_usd is not None:           updates["MAE_usd"] = MAE_usd
        if MFE_usd is not None:           updates["MFE_usd"] = MFE_usd
        if time_to_peak_favorable_s is not None:
            updates["time_to_peak_favorable_s"] = time_to_peak_favorable_s
        if time_to_peak_adverse_s is not None:
            updates["time_to_peak_adverse_s"] = time_to_peak_adverse_s
        if not updates:
            return
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updates["trade_id"] = trade_id
        set_clause = ", ".join(f"{k}=:{k}" for k in updates if k != "trade_id")
        with _lock:
            conn = _get_conn()
            try:
                conn.execute(
                    f"UPDATE trades SET {set_clause} WHERE trade_id=:trade_id",
                    updates
                )
                conn.commit()
            finally:
                conn.close()

    def log_trade_exit(
        self,
        trade_id_or_order_id: str,
        *,
        exit_price: float,
        exit_size: float,
        exit_reason: str,
        realized_pnl_usd: float,
        exit_ts: Optional[str] = None,
        whale_exit_timing: Optional[str] = None,
        entry_price: Optional[float] = None,
        entry_size: Optional[float] = None,
        MFE_price: Optional[float] = None,
    ):
        """
        Schreibt Exit-Daten in den Trade-Eintrag.
        Akzeptiert trade_id oder order_id (lookup via _order_trade_map).
        """
        trade_id = self._order_trade_map.get(trade_id_or_order_id, trade_id_or_order_id)

        now = datetime.now(timezone.utc).isoformat()
        exit_ts = exit_ts or now

        holding_s: Optional[float] = None
        r_multiple: Optional[float] = None
        capture: Optional[float] = None

        if entry_price and entry_size and entry_price > 0:
            initial_risk = entry_size
            r_multiple = round(realized_pnl_usd / initial_risk, 4) if initial_risk else None

        if MFE_price and entry_price and (MFE_price - entry_price) != 0:
            max_gain = (MFE_price - entry_price) * (exit_size or entry_size or 1)
            if max_gain > 0:
                capture = round(realized_pnl_usd / max_gain, 4)

        # Lookup holding_period from created_at
        with _lock:
            conn = _get_conn()
            try:
                row = conn.execute(
                    "SELECT created_at FROM trades WHERE trade_id=?", (trade_id,)
                ).fetchone()
                if row and row["created_at"]:
                    try:
                        entry_dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                        now_dt = datetime.now(timezone.utc)
                        holding_s = (now_dt - entry_dt).total_seconds()
                    except Exception:
                        pass

                conn.execute(
                    """UPDATE trades SET
                        exit_ts=:exit_ts,
                        exit_price=:exit_price,
                        exit_size=:exit_size,
                        exit_reason=:exit_reason,
                        whale_exit_timing=:whale_exit_timing,
                        holding_period_s=:holding_period_s,
                        realized_pnl_usd=:realized_pnl_usd,
                        realized_pnl_r_multiple=:r_multiple,
                        capture_ratio=:capture,
                        updated_at=:updated_at
                    WHERE trade_id=:trade_id""",
                    {
                        "exit_ts":          exit_ts,
                        "exit_price":       exit_price,
                        "exit_size":        exit_size,
                        "exit_reason":      exit_reason,
                        "whale_exit_timing": whale_exit_timing,
                        "holding_period_s": holding_s,
                        "realized_pnl_usd": realized_pnl_usd,
                        "r_multiple":       r_multiple,
                        "capture":          capture,
                        "updated_at":       now,
                        "trade_id":         trade_id,
                    }
                )
                conn.commit()
            finally:
                conn.close()

        # Clean up map entry
        keys_to_remove = [k for k, v in self._order_trade_map.items() if v == trade_id]
        for k in keys_to_remove:
            self._order_trade_map.pop(k, None)

    def get_trade_id_for_order(self, order_id: str) -> Optional[str]:
        return self._order_trade_map.get(order_id)

    # ── Query helpers (for dashboard) ─────────────────────────────────────────

    def query_cohort_by_category(self) -> List[Dict]:
        with _lock:
            conn = _get_conn()
            try:
                rows = conn.execute("SELECT * FROM cohort_by_category").fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def query_wallet_attribution(self) -> List[Dict]:
        with _lock:
            conn = _get_conn()
            try:
                rows = conn.execute("SELECT * FROM wallet_attribution LIMIT 50").fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def query_slippage_histogram(self) -> List[Dict]:
        with _lock:
            conn = _get_conn()
            try:
                rows = conn.execute("SELECT * FROM slippage_histogram").fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def stats(self) -> Dict:
        """Zusammenfassung für Dashboard-Health-Check."""
        with _lock:
            conn = _get_conn()
            try:
                r = conn.execute("""
                    SELECT
                        COUNT(*) AS total,
                        COUNT(CASE WHEN exit_ts IS NOT NULL THEN 1 END) AS closed,
                        COUNT(CASE WHEN exit_ts IS NULL     THEN 1 END) AS open,
                        ROUND(SUM(COALESCE(realized_pnl_usd,0)),2)      AS total_pnl,
                        COUNT(CASE WHEN is_dry_run=0 THEN 1 END)         AS live_trades,
                        COUNT(CASE WHEN is_dry_run=1 THEN 1 END)         AS paper_trades
                    FROM trades
                """).fetchone()
                sigs = conn.execute("SELECT COUNT(*) AS c FROM signals").fetchone()
                return {
                    "total_trades":  r["total"],
                    "closed_trades": r["closed"],
                    "open_trades":   r["open"],
                    "total_pnl":     r["total_pnl"],
                    "live_trades":   r["live_trades"],
                    "paper_trades":  r["paper_trades"],
                    "total_signals": sigs["c"],
                    "pending_exits": len(self._order_trade_map),
                }
            finally:
                conn.close()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write_cohort_attributes(
        self, trade_id: str, category: str, signal, extra: dict
    ):
        now_h = datetime.now(timezone.utc).hour
        vol = _gf(signal, "market_volume_usd") if signal else None
        if vol is None:
            liq_tier = None
        elif vol >= 100_000:
            liq_tier = "high"
        elif vol >= 10_000:
            liq_tier = "medium"
        else:
            liq_tier = "low"

        sc = extra.get("signal_count", 1)
        sc_bin = "1" if sc == 1 else "2" if sc == 2 else "3+"

        with _lock:
            conn = _get_conn()
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO cohort_attributes
                       (trade_id, event_category, hour_of_day_utc, liquidity_tier,
                        signal_count_bin) VALUES (?,?,?,?,?)""",
                    (trade_id, category, now_h, liq_tier, sc_bin)
                )
                conn.commit()
            finally:
                conn.close()


# ── Migration ─────────────────────────────────────────────────────────────────

def migrate_from_archive(archive_path: Optional[Path] = None) -> int:
    """
    Importiert bestehende trades_archive.json in trades.db.
    Fehlende Felder werden als NULL gespeichert.
    Bereits importierte Einträge (per tx_hash + market_id) werden übersprungen.
    Gibt Anzahl importierter Einträge zurück.
    """
    if archive_path is None:
        archive_path = _BASE / "trades_archive.json"
    if not archive_path.exists():
        return 0

    try:
        raw = json.loads(archive_path.read_text())
    except Exception:
        return 0

    if not isinstance(raw, list):
        return 0

    imported = 0
    with _lock:
        conn = _get_conn()
        try:
            for entry in raw:
                # Generate stable trade_id from archive id
                legacy_id = str(entry.get("id", "")) + str(entry.get("tx_hash", "")) + str(entry.get("market_id", ""))
                trade_id = str(uuid.uuid5(uuid.NAMESPACE_OID, legacy_id))

                exists = conn.execute(
                    "SELECT 1 FROM trades WHERE trade_id=?", (trade_id,)
                ).fetchone()
                if exists:
                    continue

                is_dry = 1 if entry.get("modus", "DRY-RUN") == "DRY-RUN" else 0
                has_exit = bool(entry.get("aufgeloest", False))
                pnl = entry.get("gewinn_verlust_usdc")
                price = entry.get("preis_usdc")
                size = entry.get("einsatz_usdc")

                # Determine exit_reason from category field
                raw_cat = entry.get("kategorie", "")
                exit_reason = None
                if has_exit:
                    if "exit_" in raw_cat:
                        exit_reason = raw_cat.replace("exit_", "").upper()
                    elif entry.get("ergebnis"):
                        exit_reason = "RESOLUTION"

                conn.execute(
                    """INSERT OR IGNORE INTO trades
                    (trade_id, market_id, condition_id, outcome_token_id,
                     event_category, is_dry_run, implied_prob_market,
                     position_size_usd, side, filled_price, filled_size,
                     tx_hash, order_id,
                     exit_ts, exit_price, exit_size, exit_reason,
                     realized_pnl_usd, strategy, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        trade_id,
                        entry.get("market_id"),
                        entry.get("market_id"),
                        entry.get("token_id"),
                        raw_cat,
                        is_dry,
                        price,
                        size,
                        entry.get("seite"),
                        price,
                        size,
                        entry.get("tx_hash") or None,
                        entry.get("tx_hash") or None,
                        (entry.get("datum", "") + " " + entry.get("uhrzeit", "")).strip()
                            if has_exit else None,
                        price if has_exit else None,
                        size if has_exit else None,
                        exit_reason,
                        pnl if has_exit else None,
                        "COPY",
                        (entry.get("datum", "") + "T" + entry.get("uhrzeit", "00:00:00")).strip(),
                    )
                )
                imported += 1
            conn.commit()
        finally:
            conn.close()
    return imported


# ── Utility ───────────────────────────────────────────────────────────────────

def _g(obj, attr: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _gf(obj, attr: str, default=None) -> Optional[float]:
    v = _g(obj, attr, default)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _dt(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)


# ── Module-level singleton ────────────────────────────────────────────────────

_instance: Optional[TradeLogger] = None


def get_trade_logger() -> TradeLogger:
    global _instance
    if _instance is None:
        _instance = TradeLogger()
    return _instance
