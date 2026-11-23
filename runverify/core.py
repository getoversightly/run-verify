"""Core types and the verification block.

A verification block is the only acceptable evidence for a claim about an
agent run. It is printed from the run's OWN authoritative record: executor,
served model, status, and the source that was read. If a route does not
expose a served model, the block says so in a fixed form, and any claim
about that run's model is unverifiable by definition.
"""
from dataclasses import dataclass

# The refusal line. This wording is part of the tool's behavior: it is the
# exact string a report must be able to show for a route that keeps no
# served-model field. Do not soften it.
NOT_EXPOSED_MODEL = (
    "NOT EXPOSED by this route — any served-model claim for this run "
    "is UNVERIFIABLE"
)


@dataclass
class RunRecord:
    """One run, as read from its own record."""

    run_id: str
    executor: str
    served_model: str | None  # None + model_exposed -> "NOT IN RECORD"
    status: str
    source: str
    model_exposed: bool = True


@dataclass
class Outcome:
    """The result of one adapter lookup.

    record: a RunRecord to print as a block, or None.
    exit_code: 0 when a record was read, 2 otherwise.
    message: lines to print instead of a block (no record, or a record
        that exists but cannot support a claim, e.g. an unstamped one).
    """

    record: RunRecord | None
    exit_code: int
    message: str | None = None


def format_block(rec: RunRecord) -> str:
    if not rec.model_exposed:
        model = NOT_EXPOSED_MODEL
    elif rec.served_model is None:
        model = "NOT IN RECORD"
    else:
        model = rec.served_model
    lines = [
        f"RUN VERIFY — {rec.run_id}",
        f"executor: {rec.executor}",
        f"served_model: {model}",
        f"status: {rec.status}",
        f"source: {rec.source}",
    ]
    return "\n".join(lines)
