"""Example adapter: a CLI's own session records on disk.

Some agent CLIs keep, per run, a work directory with an exit file, and a
session directory holding the session's own record files. The served
model is whatever those files name. This adapter reads them directly:
no daemon, no API, no inference from the request that launched the run.

Config:
  runs_root:      directory holding one work directory per run id; each
                  may contain exit.txt with the run's exit code.
  sessions_root:  directory holding one session directory per run id.
                  Record files inside are scanned for model identifiers.
  model_pattern:  regex matching the CLI's model identifiers in its
                  session records, e.g. "forge-[0-9.]+-build".
  executor_label: the executor string printed in the block.
  max_scan_bytes: files larger than this are skipped during the scan
                  (default 60000000).
"""
import os
import re

from ..core import Outcome, RunRecord
from .base import Adapter


class CliSessionsAdapter(Adapter):
    kind = "cli-sessions"

    def fetch(self, *, run_id=None, task_id=None, attempt_id=None):
        if not run_id:
            return Outcome(None, 2, "the cli-sessions adapter needs a run id")
        runs_root = self.config["runs_root"]
        sessions_root = self.config["sessions_root"]
        workdir = os.path.join(runs_root, run_id)
        if not os.path.isdir(workdir):
            return self.no_record(
                run_id, f"the run work directories under {runs_root}")
        exit_code = None
        exit_path = os.path.join(workdir, "exit.txt")
        if os.path.exists(exit_path):
            with open(exit_path) as f:
                exit_code = f.read().strip()
        session_dir = os.path.join(sessions_root, run_id)
        sessions = []
        prompts = 0
        models = set()
        pattern = re.compile(self.config["model_pattern"])
        max_bytes = self.config.get("max_scan_bytes", 60000000)
        if os.path.isdir(session_dir):
            for name in sorted(os.listdir(session_dir)):
                if os.path.isdir(os.path.join(session_dir, name)):
                    sessions.append(name)
            history = os.path.join(session_dir, "prompt_history.jsonl")
            if os.path.exists(history):
                with open(history) as f:
                    prompts = sum(1 for _ in f)
            for root, _dirs, files in os.walk(session_dir):
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        if os.path.getsize(path) > max_bytes:
                            continue
                        with open(path, errors="ignore") as f:
                            models.update(pattern.findall(f.read()))
                    except Exception:
                        continue
        rec = RunRecord(
            run_id=run_id,
            executor=self.config["executor_label"],
            served_model=", ".join(sorted(models))
            if models
            else "NOT IN SESSION RECORD",
            status=(
                f"exit {exit_code} · sessions {sessions} · "
                f"prompts {prompts}"
            ),
            source=(
                f"the run's own session record under {sessions_root} "
                f"(workdir {workdir})"
            ),
        )
        return Outcome(rec, 0)
