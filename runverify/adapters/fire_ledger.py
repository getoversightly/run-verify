"""Example adapter: a runner's fire-ledger executor stamp.

Queued runners often enqueue work through a transport shell (an API call,
a scheduled job) that is NOT the executor. Verifying the shell's record
proves the plumbing ran, not who did the work. This adapter reads the
fire-ledger's executor stamp instead: a record the runner's completion
poll writes from the run's done-record plus the engine's own session
record, naming the engine, the model, the exit code, and the finish time.

A ledger record with no stamp cannot support an executor claim. The
adapter says so and exits 2: the executor is unverified on that record,
and the reader is pointed at the primary records on the seat machine.

Config:
  ledger_path:    JSON file: an object whose values are ledger records.
  record_kind:    only records with this "kind" are considered
                  (example: "remote-run").
  engine_display: map of engine keys to display names,
                  e.g. {"forge": "Forge CLI"}.
"""
import json
import os

from ..core import Outcome, RunRecord
from .base import Adapter


class FireLedgerAdapter(Adapter):
    kind = "fire-ledger"

    def _find(self, run_id=None, attempt_id=None):
        path = self.config["ledger_path"]
        if not os.path.exists(path):
            return None
        with open(path) as f:
            ledger = json.load(f)
        kind = self.config.get("record_kind", "remote-run")
        for key, rec in ledger.items():
            if rec.get("kind") != kind:
                continue
            if run_id and rec.get("run_id") == run_id:
                return rec
            if attempt_id and attempt_id in (rec.get("attempt_id"), key):
                return rec
        return None

    def fetch(self, *, run_id=None, task_id=None, attempt_id=None):
        if not run_id and not attempt_id:
            return Outcome(
                None, 2, "the fire-ledger adapter needs a run id or "
                "an attempt id")
        rec = self._find(run_id=run_id, attempt_id=attempt_id)
        ident = attempt_id or run_id
        if rec is None:
            return self.no_record(ident, "the fire-ledger")
        aid = rec.get("attempt_id", ident)
        kind = self.config.get("record_kind", "remote-run")
        if not rec.get("executor_engine"):
            message = "\n".join([
                f"RUN VERIFY — {aid} ({kind})",
                "executor: NOT STAMPED — this record carries no executor "
                "stamp, so the executor is UNVERIFIED here. Read the "
                "done-record, the runner log, and the engine session "
                "record on the seat machine directly.",
                f"status: {rec.get('state', 'unknown')}",
                f"source: fire-ledger record {aid} (route "
                f"{rec.get('route_selected')}); enqueue shell run "
                f"{rec.get('run_id')} is transport, not the executor",
            ])
            return Outcome(None, 2, message)
        display = self.config.get("engine_display", {})
        eng = rec["executor_engine"]
        record = RunRecord(
            run_id=f"{aid} ({kind})",
            executor=(
                f"{display.get(eng, eng)} via the runner "
                f"({rec.get('route_selected')}) — engine pinned in the "
                f"job file, executed in the seat's interactive session"
            ),
            served_model=rec.get("executor_model")
            or "NOT IN SESSION RECORD",
            status=(
                f"{rec.get('state', 'unknown')} · exit "
                f"{rec.get('executor_exit')} · finished "
                f"{rec.get('executor_finished_at')}"
            ),
            source=(
                f"fire-ledger executor stamp: done-record "
                f"done/{aid}.json + engine session record "
                f"{rec.get('executor_rollout')} (read by the completion "
                f"poll); transport shell was gateway run "
                f"{rec.get('run_id')} (enqueue/poll plumbing, not the "
                f"executor)"
            ),
        )
        return Outcome(record, 0)
