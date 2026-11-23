#!/usr/bin/env python3
"""Self-test: run the CLI against synthetic fixture records.

Every fixture under tests/fixtures/ is invented. No real run, host, or
record appears in this suite. Run from the repo root:

    python3 -m unittest discover -s tests -v
    # or
    python3 tests/test_run_verify.py
"""
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "run_verify.py")
CONFIG = os.path.join(REPO, "tests", "fixtures", "config.json")


def run_cli(*args):
    proc = subprocess.run(
        [sys.executable, CLI, "--config", CONFIG, *args],
        capture_output=True, text=True, cwd=REPO)
    return proc.returncode, proc.stdout


class GatewayTest(unittest.TestCase):
    def test_block_from_status_record(self):
        rc, out = run_cli("--adapter", "gateway-primary",
                          "--run-id", "run_aaa111")
        self.assertEqual(rc, 0)
        self.assertIn("RUN VERIFY — run_aaa111", out)
        self.assertIn("executor: Claude via agent gateway (primary)", out)
        self.assertIn("served_model: model-x-5", out)
        self.assertIn("status: completed", out)
        self.assertIn("session sess_123", out)

    def test_no_record(self):
        rc, out = run_cli("--adapter", "gateway-primary",
                          "--run-id", "run_missing")
        self.assertEqual(rc, 2)
        self.assertIn("NO RECORD FOUND", out)


class CliSessionsTest(unittest.TestCase):
    def test_block_from_session_record(self):
        rc, out = run_cli("--adapter", "cli-seat-a",
                          "--run-id", "run_bbb222")
        self.assertEqual(rc, 0)
        self.assertIn("served_model: forge-2.1-build", out)
        self.assertIn("exit 0", out)
        self.assertIn("prompts 3", out)
        self.assertIn("session-1", out)

    def test_no_record(self):
        rc, out = run_cli("--adapter", "cli-seat-a",
                          "--run-id", "run_missing")
        self.assertEqual(rc, 2)
        self.assertIn("NO RECORD FOUND", out)


class FireLedgerTest(unittest.TestCase):
    def test_stamped_record(self):
        rc, out = run_cli("--adapter", "runner-ledger",
                          "--attempt-id", "att_ccc333")
        self.assertEqual(rc, 0)
        self.assertIn("executor: Forge CLI via the runner (seat-a)", out)
        self.assertIn("served_model: forge-2.1", out)
        self.assertIn("exit 0", out)
        self.assertIn("transport shell was gateway run run_shell_1", out)

    def test_unstamped_record_refuses(self):
        rc, out = run_cli("--adapter", "runner-ledger",
                          "--attempt-id", "att_ddd444")
        self.assertEqual(rc, 2)
        self.assertIn("NOT STAMPED", out)
        self.assertIn("UNVERIFIED", out)
        self.assertIn("transport, not the executor", out)


class WebhookTest(unittest.TestCase):
    def test_refusal_block(self):
        rc, out = run_cli("--adapter", "webhook-hooks",
                          "--task-id", "TASK-1001")
        self.assertEqual(rc, 0)
        self.assertIn("RUN VERIFY — TASK-1001", out)
        self.assertIn("NOT EXPOSED by this route", out)
        self.assertIn("UNVERIFIABLE", out)
        self.assertIn("2 fire(s) on record", out)

    def test_no_fire(self):
        rc, out = run_cli("--adapter", "webhook-hooks",
                          "--task-id", "TASK-9999")
        self.assertEqual(rc, 2)
        self.assertIn("NO RECORD FOUND", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
