"""The adapter interface.

An adapter knows how to read ONE kind of authoritative record for a run:
a gateway's status API, a CLI's session records on disk, a runner's
fire-ledger, a webhook fire-log. Adapters are read-only. An adapter must
never guess: if the record is not there, it returns a no-record Outcome;
if the route keeps no served-model field, it returns a record with
model_exposed=False so the block prints the refusal line.
"""
from ..core import Outcome


class Adapter:
    kind = "base"

    def __init__(self, name: str, **config):
        self.name = name
        self.config = config

    def fetch(self, *, run_id=None, task_id=None, attempt_id=None) -> Outcome:
        raise NotImplementedError

    def no_record(self, ident: str, where: str) -> Outcome:
        return Outcome(
            record=None,
            exit_code=2,
            message=f"RUN VERIFY — {ident}\nNO RECORD FOUND in {where}.",
        )
