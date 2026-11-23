"""Example adapter: a webhook fire-log.

Hosted automation webhooks fire work into a third-party agent. The
fire-log proves the fire happened: task id, timestamp, payload hash. It
does not name a served model, because the route does not expose one.

That absence is the point of this adapter. The block it prints carries
the refusal line as its served_model, so a report quoting a model for a
webhook run has nowhere to stand: the run's own record cannot support
the claim, and the block says exactly that.

Config:
  log_path:       JSONL file, one fire record per line.
  id_field:       the field matched against the task id
                  (default "task_id").
  ts_field:       the timestamp field (default "ts").
  hash_field:     payload hash field, printed in shortened form when
                  present (default "sha256").
  executor_label: the executor string printed in the block. Name the
                  hosted route for what it is, and say plainly that it
                  is not a local seat.
"""
import json
import os

from ..core import Outcome, RunRecord
from .base import Adapter


class WebhookLogAdapter(Adapter):
    kind = "webhook"

    def fetch(self, *, run_id=None, task_id=None, attempt_id=None):
        if not task_id:
            return Outcome(None, 2, "the webhook adapter needs a task id")
        path = self.config["log_path"]
        if not os.path.exists(path):
            return self.no_record(task_id, "the webhook fire-log")
        id_field = self.config.get("id_field", "task_id")
        hits = []
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get(id_field) == task_id:
                    hits.append(rec)
        if not hits:
            return self.no_record(task_id, "the webhook fire-log")
        last = hits[-1]
        ts_field = self.config.get("ts_field", "ts")
        hash_field = self.config.get("hash_field", "sha256")
        source = f"webhook fire-log ({id_field} match"
        if last.get(hash_field):
            source += f"; {hash_field} {str(last[hash_field])[:12]}…"
        source += ")"
        record = RunRecord(
            run_id=task_id,
            executor=self.config["executor_label"],
            served_model=None,
            status=(
                f"fired {last.get(ts_field)} · {len(hits)} fire(s) "
                f"on record"
            ),
            source=source,
            model_exposed=False,
        )
        return Outcome(record, 0)
