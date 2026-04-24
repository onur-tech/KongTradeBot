"""Tests for core/strategy_config.py — YAML loader and env-var overrides."""
import json
import os
import textwrap
from pathlib import Path

import pytest
import yaml

from core.strategy_config import AggregationConfig, StrategyConfig, load, _apply_env_weights


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def yaml_path(tmp_path) -> Path:
    content = textwrap.dedent("""
        aggregation:
          window_s: 45
          multi_signal_multipliers:
            1: 1.0
            2: 1.5
            3: 2.0
          herd_fraction: 0.40
          early_entry_multiplier: 1.2
          early_entry_volume_usd: 8000

        default_multiplier: 0.7

        wallet_multipliers:
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1": 1.5
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2": 3.0
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3": 0.3

        wallet_categories:
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1": ["sports"]
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2": ["crypto"]

        wallet_names:
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1": "TestWalletA"
          "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2": "TestWalletB"

        category_keywords:
          sports:
            - "nba"
            - "nfl"
          crypto:
            - "bitcoin"
            - "btc"

        crypto_daily_keywords:
          - "bitcoin-above"
          - "eth-above"
    """)
    p = tmp_path / "copy_trading.yaml"
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------

def test_load_returns_strategy_config(yaml_path):
    cfg = load(yaml_path)
    assert isinstance(cfg, StrategyConfig)


def test_aggregation_values(yaml_path):
    cfg = load(yaml_path)
    assert cfg.aggregation.window_s == 45
    assert cfg.aggregation.herd_fraction == pytest.approx(0.40)
    assert cfg.aggregation.early_entry_multiplier == pytest.approx(1.2)
    assert cfg.aggregation.early_entry_volume_usd == pytest.approx(8000.0)


def test_multi_signal_multipliers(yaml_path):
    cfg = load(yaml_path)
    assert cfg.aggregation.multi_signal_multipliers == {1: 1.0, 2: 1.5, 3: 2.0}


def test_default_multiplier(yaml_path):
    cfg = load(yaml_path)
    assert cfg.default_multiplier == pytest.approx(0.7)


def test_wallet_multipliers_loaded(yaml_path):
    cfg = load(yaml_path)
    assert len(cfg.wallet_multipliers) == 3
    assert cfg.wallet_multipliers["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"] == pytest.approx(1.5)
    assert cfg.wallet_multipliers["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2"] == pytest.approx(3.0)
    assert cfg.wallet_multipliers["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa3"] == pytest.approx(0.3)


def test_wallet_categories_loaded(yaml_path):
    cfg = load(yaml_path)
    assert cfg.wallet_categories["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"] == ["sports"]
    assert cfg.wallet_categories["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2"] == ["crypto"]


def test_wallet_names_loaded(yaml_path):
    cfg = load(yaml_path)
    assert cfg.wallet_names["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"] == "TestWalletA"
    assert cfg.wallet_names["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa2"] == "TestWalletB"


def test_category_keywords_loaded(yaml_path):
    cfg = load(yaml_path)
    assert "sports" in cfg.category_keywords
    assert "nba" in cfg.category_keywords["sports"]
    assert "bitcoin" in cfg.category_keywords["crypto"]


def test_crypto_daily_keywords_loaded(yaml_path):
    cfg = load(yaml_path)
    assert "bitcoin-above" in cfg.crypto_daily_keywords
    assert "eth-above" in cfg.crypto_daily_keywords


def test_addresses_lowercased(yaml_path):
    cfg = load(yaml_path)
    for addr in cfg.wallet_multipliers:
        assert addr == addr.lower(), f"Address not lowercase: {addr}"
    for addr in cfg.wallet_categories:
        assert addr == addr.lower()
    for addr in cfg.wallet_names:
        assert addr == addr.lower()


# ---------------------------------------------------------------------------
# Missing / empty fields → defaults
# ---------------------------------------------------------------------------

def test_empty_yaml_uses_defaults(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    cfg = load(p)
    assert cfg.default_multiplier == pytest.approx(0.5)
    assert cfg.aggregation.window_s == 60
    assert cfg.wallet_multipliers == {}
    assert cfg.wallet_categories == {}
    assert cfg.crypto_daily_keywords == []


def test_missing_aggregation_block_uses_defaults(tmp_path):
    p = tmp_path / "no_agg.yaml"
    p.write_text("default_multiplier: 1.0\n")
    cfg = load(p)
    assert cfg.aggregation.herd_fraction == pytest.approx(0.50)
    assert cfg.aggregation.window_s == 60


# ---------------------------------------------------------------------------
# env-var override: WALLET_WEIGHTS
# ---------------------------------------------------------------------------

def test_env_weight_override_by_full_prefix(yaml_path, monkeypatch):
    prefix = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"
    monkeypatch.setenv("WALLET_WEIGHTS", json.dumps({prefix: 2.5}))
    cfg = load(yaml_path)
    _apply_env_weights(cfg)
    assert cfg.wallet_multipliers[prefix] == pytest.approx(2.5)


def test_env_weight_default_override(yaml_path, monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", json.dumps({"default": 0.8}))
    cfg = load(yaml_path)
    _apply_env_weights(cfg)
    assert cfg.default_multiplier == pytest.approx(0.8)


def test_env_weight_invalid_json_ignored(yaml_path, monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "not-valid-json")
    cfg = load(yaml_path)
    _apply_env_weights(cfg)
    # original value must be unchanged
    assert cfg.wallet_multipliers["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1"] == pytest.approx(1.5)


def test_env_weight_empty_ignored(yaml_path, monkeypatch):
    monkeypatch.setenv("WALLET_WEIGHTS", "")
    cfg = load(yaml_path)
    _apply_env_weights(cfg)
    assert cfg.default_multiplier == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Production YAML sanity checks
# ---------------------------------------------------------------------------

def test_production_yaml_loads():
    """The real config/strategies/copy_trading.yaml must be parseable."""
    from pathlib import Path
    prod_path = Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml"
    assert prod_path.exists(), "config/strategies/copy_trading.yaml missing"
    cfg = load(prod_path)
    assert len(cfg.wallet_multipliers) >= 10
    assert len(cfg.wallet_names) >= 10
    assert len(cfg.category_keywords) >= 4
    assert cfg.aggregation.window_s > 0


def test_production_countryside_multiplier():
    """Countryside must have 3.0x (high-WR wallet)."""
    from pathlib import Path
    prod_path = Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml"
    cfg = load(prod_path)
    addr = "0xbddf61af533ff524d27154e589d2d7a81510c684"
    assert cfg.wallet_multipliers.get(addr) == pytest.approx(3.0)


def test_production_drpufferfish_multiplier():
    from pathlib import Path
    prod_path = Path(__file__).parent.parent / "config" / "strategies" / "copy_trading.yaml"
    cfg = load(prod_path)
    addr = "0xdb27bf2ac5d428a9c63dbc914611036855a6c56e"
    assert cfg.wallet_multipliers.get(addr) == pytest.approx(3.0)
