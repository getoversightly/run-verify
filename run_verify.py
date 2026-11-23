#!/usr/bin/env python3
"""run_verify.py: prove which model actually served an agent run.

Reads a run's AUTHORITATIVE record through a route adapter and prints a
verification block: executor + served model + status + the source read.
A run report that claims an executor or a served model must be able to
attach this output; a claim without it is unverified by definition.

Adapters are configured in a JSON file (see config.example.json). Each
entry names a route you operate:

  gateway       a gateway status API returning the run's own record
  cli-sessions  a CLI's per-run work dirs + session records on disk
  fire-ledger   a runner's fire-ledger, read by its executor stamp
  webhook       a webhook fire-log; exposes NO served model, and the
                block prints the refusal line, which is the guard

Usage:
  run_verify.py --config run-verify.config.json \
      --adapter gateway-primary --run-id run_<hex>
  run_verify.py --config run-verify.config.json \
      --adapter cli-seat-a --run-id <TASKID>
  run_verify.py --config run-verify.config.json \
      --adapter runner-ledger --attempt-id att_<hex>
  run_verify.py --config run-verify.config.json \
      --adapter webhook-hooks --task-id TASK-1234

Exit codes: 0 = record read; 2 = no record found / route unsupported /
record cannot support a claim. Read-only everywhere.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runverify.adapters import ADAPTER_TYPES  # noqa: E402
from runverify.core import format_block  # noqa: E402

PATH_KEYS = ("runs_root", "sessions_root", "ledger_path", "log_path")


def load_adapters(config_path):
    with open(config_path) as f:
        cfg = json.load(f)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    adapters = {}
    for name, spec in cfg.get("adapters", {}).items():
        spec = dict(spec)
        kind = spec.pop("type")
        if kind not in ADAPTER_TYPES:
            raise SystemExit(f"unknown adapter type: {kind}")
        for key in PATH_KEYS:
            value = spec.get(key)
            if value and not os.path.isabs(value):
                spec[key] = os.path.join(base_dir, value)
        if str(spec.get("base_url", "")).startswith("file://"):
            fs_path = spec["base_url"][len("file://"):]
            if not os.path.isabs(fs_path):
                spec["base_url"] = "file://" + os.path.join(base_dir, fs_path)
        adapters[name] = ADAPTER_TYPES[kind](name, **spec)
    return adapters


def main():
    ap = argparse.ArgumentParser(
        description="Prove which model actually served an agent run, "
        "from the run's own record.")
    ap.add_argument("--config", required=True,
                    help="JSON config naming the route adapters")
    ap.add_argument("--adapter", required=True,
                    help="adapter instance name from the config")
    ap.add_argument("--run-id")
    ap.add_argument("--task-id")
    ap.add_argument("--attempt-id")
    a = ap.parse_args()

    adapters = load_adapters(a.config)
    if a.adapter not in adapters:
        print(f"unknown adapter: {a.adapter} "
              f"(configured: {', '.join(sorted(adapters))})")
        return 2
    outcome = adapters[a.adapter].fetch(
        run_id=a.run_id, task_id=a.task_id, attempt_id=a.attempt_id)
    if outcome.record is not None:
        print(format_block(outcome.record))
    if outcome.message:
        print(outcome.message)
    return outcome.exit_code


if __name__ == "__main__":
    sys.exit(main())
