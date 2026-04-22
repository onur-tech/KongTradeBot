"""Unit tests for core/signature_check.py — Phase 2.2"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.signature_check import run_self_check

VALID_KEY = "0x" + "a" * 64
VALID_ADDR = "0x" + "b" * 40


class TestSignatureCheck(unittest.TestCase):

    def _env(self, **kwargs):
        defaults = {
            "PRIVATE_KEY": VALID_KEY,
            "POLYMARKET_ADDRESS": VALID_ADDR,
            "SIGNATURE_TYPE": "1",
        }
        defaults.update(kwargs)
        return defaults

    def test_all_valid_returns_true(self):
        with patch.dict("os.environ", self._env(), clear=False):
            self.assertTrue(run_self_check())

    def test_missing_private_key_returns_false(self):
        with patch.dict("os.environ", self._env(PRIVATE_KEY=""), clear=False):
            self.assertFalse(run_self_check())

    def test_invalid_key_length_returns_false(self):
        with patch.dict("os.environ", self._env(PRIVATE_KEY="0x" + "a" * 32), clear=False):
            self.assertFalse(run_self_check())

    def test_missing_address_returns_false(self):
        with patch.dict("os.environ", self._env(POLYMARKET_ADDRESS=""), clear=False):
            self.assertFalse(run_self_check())

    def test_invalid_address_format_returns_false(self):
        with patch.dict("os.environ", self._env(POLYMARKET_ADDRESS="not-an-address"), clear=False):
            self.assertFalse(run_self_check())

    def test_sig_type_0_valid(self):
        with patch.dict("os.environ", self._env(SIGNATURE_TYPE="0"), clear=False):
            # type=0 is valid (EOA), should return True with warning
            result = run_self_check()
            self.assertTrue(result)

    def test_sig_type_invalid_returns_false(self):
        with patch.dict("os.environ", self._env(SIGNATURE_TYPE="99"), clear=False):
            self.assertFalse(run_self_check())

    def test_sig_type_nonnumeric_returns_false(self):
        with patch.dict("os.environ", self._env(SIGNATURE_TYPE="magic"), clear=False):
            self.assertFalse(run_self_check())

    def test_key_without_0x_prefix(self):
        # No 0x prefix but 64 hex chars = valid
        key_no_prefix = "a" * 64
        with patch.dict("os.environ", self._env(PRIVATE_KEY=key_no_prefix), clear=False):
            self.assertTrue(run_self_check())


if __name__ == "__main__":
    unittest.main(verbosity=2)
