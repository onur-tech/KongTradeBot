"""
Loads copy_trading.yaml and exposes typed config for the strategy.

Priority: YAML file → env-var overrides (WALLET_WEIGHTS JSON, COPY_EVENT_CAP, etc.)
Call load() once at import time; the result is a module-level singleton.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml"


@dataclass
class AggregationConfig:
    window_s: int = 60
    multi_signal_multipliers: Dict[int, float] = field(
        default_factory=lambda: {1: 1.0, 2: 1.5, 3: 2.0}
    )
    herd_fraction: float = 0.50
    early_entry_multiplier: float = 1.5
    early_entry_volume_usd: float = 10_000.0


@dataclass
class StrategyConfig:
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)
    default_multiplier: float = 0.5
    wallet_multipliers: Dict[str, float] = field(default_factory=dict)
    wallet_categories: Dict[str, List[str]] = field(default_factory=dict)
    wallet_names: Dict[str, str] = field(default_factory=dict)
    category_keywords: Dict[str, List[str]] = field(default_factory=dict)
    crypto_daily_keywords: List[str] = field(default_factory=list)


def _apply_env_weights(cfg: StrategyConfig) -> None:
    """Merge WALLET_WEIGHTS env-var (JSON) into wallet_multipliers (prefix-match on 18 chars)."""
    raw = os.environ.get("WALLET_WEIGHTS", "").strip()
    if not raw:
        return
    try:
        env_weights: dict = json.loads(raw)
    except Exception:
        return

    for env_prefix, weight in env_weights.items():
        if env_prefix == "default":
            cfg.default_multiplier = float(weight)
            continue
        for full_addr in list(cfg.wallet_multipliers.keys()):
            if full_addr.lower().startswith(env_prefix.lower()):
                cfg.wallet_multipliers[full_addr] = float(weight)


def load(path: Path = _CONFIG_PATH) -> StrategyConfig:
    """Parse YAML file and return a StrategyConfig with env-var overrides applied."""
    with open(path, encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    agg_raw = raw.get("aggregation", {})
    ms_raw = agg_raw.get("multi_signal_multipliers", {1: 1.0, 2: 1.5, 3: 2.0})
    agg = AggregationConfig(
        window_s=int(agg_raw.get("window_s", 60)),
        multi_signal_multipliers={int(k): float(v) for k, v in ms_raw.items()},
        herd_fraction=float(agg_raw.get("herd_fraction", 0.50)),
        early_entry_multiplier=float(agg_raw.get("early_entry_multiplier", 1.5)),
        early_entry_volume_usd=float(agg_raw.get("early_entry_volume_usd", 10_000.0)),
    )

    cfg = StrategyConfig(
        aggregation=agg,
        default_multiplier=float(raw.get("default_multiplier", 0.5)),
        wallet_multipliers={
            str(k).lower(): float(v)
            for k, v in (raw.get("wallet_multipliers") or {}).items()
        },
        wallet_categories={
            str(k).lower(): list(v)
            for k, v in (raw.get("wallet_categories") or {}).items()
        },
        wallet_names={
            str(k).lower(): str(v)
            for k, v in (raw.get("wallet_names") or {}).items()
        },
        category_keywords={
            str(k): list(v)
            for k, v in (raw.get("category_keywords") or {}).items()
        },
        crypto_daily_keywords=list(raw.get("crypto_daily_keywords") or []),
    )

    _apply_env_weights(cfg)
    return cfg


_singleton: StrategyConfig | None = None


def get() -> StrategyConfig:
    """Return the module-level singleton, loading once on first call."""
    global _singleton
    if _singleton is None:
        _singleton = load()
    return _singleton
