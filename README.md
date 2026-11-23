# run-verify

**Prove which model actually served an agent run, from the run's own record.**

When an agent run finishes, the report about it usually names an executor and
a model. Those names usually come from the request: what was dispatched, what
was configured, what was supposed to happen. Requests are not records. Runs
get re-routed, fall back, time out into a different seat, or fire through a
hosted webhook that serves something else entirely, and the report still
quotes the plan.

Observability tools log what your framework requested. run-verify answers a
different question: what does the system's own record say actually served
this run? And when the record cannot support a claim, it refuses to make one.

## What it prints

You point run-verify at a run id and a route. It reads that route's
authoritative record for the run and prints a verification block:

```
RUN VERIFY — run_aaa111
executor: Claude via agent gateway (primary)
served_model: model-x-5
status: completed
source: GET /v1/agent/status?run_id=run_aaa111 on the gateway-primary gateway (session sess_123)
```

The discipline this enforces: a run report that claims an executor or a
served model must be able to attach this output. A claim without a block is
unverified by definition.

## The refusal is the point

Some routes expose no served model at all. A webhook that fires work into a
hosted agent proves the fire happened; it says nothing about which model
served the work, because the route keeps no such field. For those routes the
block prints, as its served_model line:

```
served_model: NOT EXPOSED by this route — any served-model claim for this run is UNVERIFIABLE
```

That line is the guard. Without it, a webhook run gets quoted whatever model
name is lying around, and the quote hardens into a fact in the next report.
With it, the claim fails at the record.

The same refusal applies inside richer routes. A runner's ledger record with
no executor stamp exits 2 and says the executor is unverified on that record,
because verifying the transport shell that enqueued the work proves the
plumbing ran, not who did the work.

## Routes

A route is an adapter: a small class that knows how to read one kind of
authoritative record. Four example adapters ship in the box, and each is
configured per deployment in a JSON file (see `config.example.json`):

| Adapter type   | Record it reads                                             | Identifier   |
| -------------- | ----------------------------------------------------------- | ------------ |
| `gateway`      | A gateway status API returning the run's record as JSON     | `--run-id`   |
| `cli-sessions` | A CLI's per-run work directory and session records on disk  | `--run-id`   |
| `fire-ledger`  | A runner's fire-ledger, read by its executor stamp          | `--run-id` or `--attempt-id` |
| `webhook`      | A webhook fire-log (JSONL); exposes no served model         | `--task-id`  |

The `gateway` adapter also accepts a `file://` base URL, which reads a saved
status response from disk. That is how archived records are verified, and how
the test suite runs with no network.

### The adapter interface

An adapter subclasses `runverify.adapters.Adapter` and implements one method:

```python
def fetch(self, *, run_id=None, task_id=None, attempt_id=None) -> Outcome:
    ...
```

It returns an `Outcome` holding a `RunRecord` (executor, served model,
status, source), or a no-record outcome with exit code 2. Three rules are
not negotiable:

1. **Read the run's own record.** Never the request, the dispatch log, or
   the report being checked.
2. **Never guess.** No record means no record: exit 2 and say so.
3. **A route with no model field refuses.** Return the record with
   `model_exposed=False` and let the block print the refusal line.

Register a new adapter type in `runverify.adapters.ADAPTER_TYPES` and it is
available to the CLI by name.

## Install and usage

Python 3.10 or later, standard library only. Clone, copy the example config,
and edit it to name your own routes:

```bash
cp config.example.json run-verify.config.json
# edit: base URLs, record paths, executor labels, model patterns

python3 run_verify.py --config run-verify.config.json \
    --adapter gateway-primary --run-id run_<hex>
python3 run_verify.py --config run-verify.config.json \
    --adapter cli-seat-a --run-id <TASKID>
python3 run_verify.py --config run-verify.config.json \
    --adapter runner-ledger --attempt-id att_<hex>
python3 run_verify.py --config run-verify.config.json \
    --adapter webhook-hooks --task-id TASK-1234
```

Exit codes: `0` means a record was read and the block printed. `2` means no
record was found, the route is unsupported, or the record cannot support a
claim. The tool is read-only on every route.

Relative record paths in a config resolve against the config file's own
directory, so a config and its records travel together.

## Tests

The suite runs the CLI against synthetic fixture records for every route,
including the refusal paths:

```bash
python3 -m unittest discover -s tests
```

See `SELFTEST.md` for a recorded run.

## What it does not do

run-verify does not judge the quality of a run's output, store your records,
or watch anything live. It proves provenance for one run at a time, from
records you already keep. If a route keeps no record, no tool can verify it;
the honest fix is to make the route write one.

## License

MIT. See `LICENSE`.
