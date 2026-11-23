"""Example adapter: an agent gateway's status API.

Many agent gateways expose a status endpoint that returns the run's own
record as JSON: run_id, the model that served it, its status, a session
id. This adapter reads that endpoint and maps it to a RunRecord.

Config:
  base_url:      e.g. "http://127.0.0.1:8080". A "file://" base reads a
                 JSON document from disk instead, which is how archived
                 status responses are verified (and how the tests run).
  status_path:   path appended to base_url, e.g. "/v1/agent/status".
                 The run id is passed as ?run_id=<id>.
  executor_label: the executor string printed in the block. The label is
                 yours to set per deployment; the model is never part of
                 the label, because the model comes from the record.
  timeout:       seconds for the HTTP read (default 30).
"""
import json
import os
import urllib.parse
import urllib.request

from ..core import Outcome, RunRecord
from .base import Adapter


class GatewayStatusAdapter(Adapter):
    kind = "gateway"

    def _read_status(self, run_id):
        base = self.config["base_url"].rstrip("/")
        path = self.config.get("status_path", "/status")
        if base.startswith("file://"):
            fs_path = base[len("file://"):] + path
            if not os.path.exists(fs_path):
                return None
            with open(fs_path) as f:
                doc = json.load(f)
            if isinstance(doc, dict) and doc.get("run_id") in (None, run_id):
                return doc
            return None
        url = f"{base}{path}?run_id={urllib.parse.quote(run_id)}"
        try:
            with urllib.request.urlopen(
                url, timeout=self.config.get("timeout", 30)
            ) as resp:
                doc = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None
        if not isinstance(doc, dict) or not doc.get("run_id"):
            return None
        return doc

    def fetch(self, *, run_id=None, task_id=None, attempt_id=None):
        if not run_id:
            return Outcome(None, 2, "the gateway adapter needs a run id")
        st = self._read_status(run_id)
        if st is None:
            return self.no_record(
                run_id, f"the {self.name} gateway status API")
        rec = RunRecord(
            run_id=run_id,
            executor=self.config["executor_label"],
            served_model=st.get("model"),
            status=st.get("status") or "unknown",
            source=(
                f"GET {self.config.get('status_path', '/status')}"
                f"?run_id={run_id} on the {self.name} gateway "
                f"(session {st.get('session_id', '?')})"
            ),
        )
        return Outcome(rec, 0)
