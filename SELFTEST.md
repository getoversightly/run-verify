# Self-test record

Recorded 2026-11-22, Python 3.13, from the repo root. Every fixture under
`tests/fixtures/` is synthetic: invented run ids, an invented CLI ("Forge"),
invented models. No real run, host, or record appears anywhere in the suite.

In the transcripts below, the two `source:` lines that name record paths on
the machine running the test are shown with the fixture directory written as
`<fixtures>`; everything else is literal program output.

## Unit suite

```
$ python3 -m unittest discover -s tests
........
----------------------------------------------------------------------
Ran 8 tests in 1.392s

OK
```

The 8 tests: a correct block per route (gateway, cli-sessions, fire-ledger,
webhook), the webhook refusal, the unstamped-ledger refusal, and no-record
handling on the gateway, CLI, and webhook routes.

## Gateway route (status record read from a saved response)

```
$ python3 run_verify.py --config tests/fixtures/config.json \
    --adapter gateway-primary --run-id run_aaa111
RUN VERIFY — run_aaa111
executor: Claude via agent gateway (primary)
served_model: model-x-5
status: completed
source: GET /status.json?run_id=run_aaa111 on the gateway-primary gateway (session sess_123)
exit code: 0
```

## CLI session records route

```
$ python3 run_verify.py --config tests/fixtures/config.json \
    --adapter cli-seat-a --run-id run_bbb222
RUN VERIFY — run_bbb222
executor: Forge CLI (seat-a, runner)
served_model: forge-2.1-build
status: exit 0 · sessions ['session-1'] · prompts 3
source: the run's own session record under <fixtures>/cli_sessions/sessions (workdir <fixtures>/cli_sessions/runs/run_bbb222)
exit code: 0
```

## Fire-ledger route, stamped record

```
$ python3 run_verify.py --config tests/fixtures/config.json \
    --adapter runner-ledger --attempt-id att_ccc333
RUN VERIFY — att_ccc333 (remote-run)
executor: Forge CLI via the runner (seat-a) — engine pinned in the job file, executed in the seat's interactive session
served_model: forge-2.1
status: completed · exit 0 · finished 2026-11-22T15:04:05Z
source: fire-ledger executor stamp: done-record done/att_ccc333.json + engine session record sessions/att_ccc333/rollout.jsonl (read by the completion poll); transport shell was gateway run run_shell_1 (enqueue/poll plumbing, not the executor)
exit code: 0
```

## Fire-ledger route, unstamped record (refusal)

```
$ python3 run_verify.py --config tests/fixtures/config.json \
    --adapter runner-ledger --attempt-id att_ddd444
RUN VERIFY — att_ddd444 (remote-run)
executor: NOT STAMPED — this record carries no executor stamp, so the executor is UNVERIFIED here. Read the done-record, the runner log, and the engine session record on the seat machine directly.
status: completed
source: fire-ledger record att_ddd444 (route seat-b); enqueue shell run run_shell_2 is transport, not the executor
exit code: 2
```

## Webhook route (the refusal)

```
$ python3 run_verify.py --config tests/fixtures/config.json \
    --adapter webhook-hooks --task-id TASK-1001
RUN VERIFY — TASK-1001
executor: Hosted agent (automation webhook), not a local CLI seat
served_model: NOT EXPOSED by this route — any served-model claim for this run is UNVERIFIABLE
status: fired 2026-11-22T15:30:00Z · 2 fire(s) on record
source: webhook fire-log (task_id match; sha256 fedcba987654…)
exit code: 0
```

The webhook block exits 0 because the fire record was read and the block
printed; the refusal lives in the served_model line, which is where a model
claim would have to stand.
