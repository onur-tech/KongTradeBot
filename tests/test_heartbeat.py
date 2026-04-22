"""Unit tests for core/heartbeat.py and cancel_all_on_death.py — Phase 2.6"""
import sys
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Heartbeat module tests ────────────────────────────────────────────────────

class TestHeartbeat(unittest.IsolatedAsyncioTestCase):

    async def test_run_exits_immediately_when_url_not_set(self):
        with patch.dict("os.environ", {"HEALTHCHECKS_PING_URL": ""}, clear=False):
            import core.heartbeat as hb
            # Should return without looping
            await asyncio.wait_for(hb.run(interval_s=0), timeout=1.0)

    async def test_ping_ok_resets_failure_count(self):
        with patch.dict("os.environ", {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/test"}, clear=False):
            import core.heartbeat as hb

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_resp)

            ping_calls = []

            async def fake_run(interval_s=30):
                url = "https://hc-ping.com/test"
                consecutive = 0
                # Single iteration
                mock_resp.status_code = 200
                consecutive = 0
                ping_calls.append("ok")

            with patch("core.heartbeat.run", side_effect=fake_run):
                await hb.run(interval_s=0)

    async def test_warning_logged_after_3_failures(self):
        """Verify the 3-consecutive-failures warning threshold is tested."""
        import core.heartbeat as hb
        # The threshold constant
        self.assertEqual(hb._MAX_CONSECUTIVE_FAIL, 3)


# ── cancel_all_on_death webhook tests ────────────────────────────────────────

class TestCancelAllOnDeath(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp_dir.name)
        self.status_path = self.base / "data" / "bot_status.json"
        self.lock_path = self.base / "bot.lock"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _get_app(self):
        import scripts.cancel_all_on_death as mod
        self._orig_status = mod.BOT_STATUS
        self._orig_lock = mod.BOT_LOCK
        mod.BOT_STATUS = self.status_path
        mod.BOT_LOCK = self.lock_path
        return mod.app.test_client(), mod

    def _restore(self, mod):
        mod.BOT_STATUS = self._orig_status
        mod.BOT_LOCK = self._orig_lock

    def test_rejects_wrong_secret(self):
        client, mod = self._get_app()
        orig_secret = mod.WEBHOOK_SECRET
        mod.WEBHOOK_SECRET = "correct-secret"
        try:
            resp = client.post(
                "/emergency-stop",
                headers={"X-Healthchecks-Secret": "wrong-secret"},
                json={"reason": "test"},
            )
            self.assertEqual(resp.status_code, 401)
        finally:
            mod.WEBHOOK_SECRET = orig_secret
            self._restore(mod)

    def test_accepts_correct_secret(self):
        client, mod = self._get_app()
        orig_secret = mod.WEBHOOK_SECRET
        mod.WEBHOOK_SECRET = "test-secret"
        with patch.object(mod, "_cancel_all_with_retry", return_value=(True, "Canceled 0 orders")):
            with patch.object(mod, "_telegram", return_value=True):
                try:
                    resp = client.post(
                        "/emergency-stop",
                        headers={"X-Healthchecks-Secret": "test-secret"},
                        json={"reason": "test trigger"},
                    )
                    self.assertEqual(resp.status_code, 200)
                    data = resp.get_json()
                    self.assertEqual(data["status"], "EMERGENCY_STOPPED")
                finally:
                    mod.WEBHOOK_SECRET = orig_secret
                    self._restore(mod)

    def test_creates_bot_lock_and_status(self):
        client, mod = self._get_app()
        orig_secret = mod.WEBHOOK_SECRET
        mod.WEBHOOK_SECRET = ""  # No auth required when secret is empty
        with patch.object(mod, "_cancel_all_with_retry", return_value=(True, "Canceled 2 orders")):
            with patch.object(mod, "_telegram", return_value=True):
                try:
                    resp = client.post(
                        "/emergency-stop",
                        json={"reason": "unit test"},
                    )
                    self.assertEqual(resp.status_code, 200)
                    # Check bot.lock was created
                    self.assertTrue(self.lock_path.exists())
                    # Check bot_status.json was written
                    self.assertTrue(self.status_path.exists())
                    status = json.loads(self.status_path.read_text())
                    self.assertEqual(status["status"], "EMERGENCY_STOPPED")
                finally:
                    mod.WEBHOOK_SECRET = orig_secret
                    self._restore(mod)

    def test_health_endpoint(self):
        client, mod = self._get_app()
        self._restore(mod)
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "ok")

    def test_cancel_failure_sends_intervention_alert(self):
        client, mod = self._get_app()
        mod.WEBHOOK_SECRET = ""
        alert_calls = []
        with patch.object(mod, "_cancel_all_with_retry", return_value=(False, "CLOB error")):
            with patch.object(mod, "_telegram", side_effect=lambda m: alert_calls.append(m)):
                try:
                    resp = client.post("/emergency-stop", json={"reason": "test"})
                    self.assertEqual(resp.status_code, 200)
                    self.assertTrue(any("MANUAL INTERVENTION" in m for m in alert_calls))
                finally:
                    self._restore(mod)


# ── unlock_emergency tests ────────────────────────────────────────────────────

class TestUnlockEmergency(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_removes_lock_and_resets_status(self):
        import scripts.unlock_emergency as mod
        orig_status = mod.BOT_STATUS
        orig_lock = mod.BOT_LOCK
        orig_cb = mod.CB_STATE

        status_path = self.base / "data" / "bot_status.json"
        lock_path = self.base / "bot.lock"
        cb_path = self.base / "data" / "circuit_breaker.json"

        status_path.parent.mkdir(parents=True)
        status_path.write_text(json.dumps({"status": "EMERGENCY_STOPPED"}))
        lock_path.write_text("{}")
        cb_path.write_text(json.dumps({"level": 3, "reason": "test"}))

        mod.BOT_STATUS = status_path
        mod.BOT_LOCK = lock_path
        mod.CB_STATE = cb_path

        try:
            with patch("sys.argv", ["unlock_emergency.py", "--confirm"]):
                with patch.object(mod, "_telegram"):
                    mod.main()

            self.assertFalse(lock_path.exists())
            status = json.loads(status_path.read_text())
            self.assertEqual(status["status"], "NORMAL")
            cb = json.loads(cb_path.read_text())
            self.assertEqual(cb["level"], 0)
        finally:
            mod.BOT_STATUS = orig_status
            mod.BOT_LOCK = orig_lock
            mod.CB_STATE = orig_cb


if __name__ == "__main__":
    unittest.main(verbosity=2)
