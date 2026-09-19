# Equity Strategist

Equity Strategist turns equity-market questions into traceable quantitative
analysis. LLM understanding extracts typed intent; Python validates, plans, gets
market data, and calculates results; LLM interpretation explains the resulting
deterministic evidence. The HTTP API is a transport layer around this pipeline.

## Local setup

Use Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Set `OPENAI_API_KEY` for the LLM pipeline and `EQUITY_STRATEGIST_API_KEY` for
Bearer authentication. `EQUITY_STRATEGIST_MODEL` is optional and defaults to
`gpt-5.6` for both understanding and interpretation, including when unset, empty,
or whitespace-only. Startup requires a nonblank `OPENAI_API_KEY` and a nonempty
`EQUITY_STRATEGIST_API_KEY` containing only visible ASCII without spaces.
Configuration validation makes no external calls; the graph is built lazily on
the first chat request. Keep secrets in environment variables; `.env.example`
contains variable names only.

Start the API with one worker:

```bash
uvicorn equity_strategist.api.server:app --host 0.0.0.0 --port 8000 --workers 1
```

The unauthenticated liveness check makes no OpenAI or Yahoo call:

```bash
curl http://localhost:8000/health
```

Submit a question:

```bash
curl -sS http://localhost:8000/v1/chat \
  -H "Authorization: Bearer $EQUITY_STRATEGIST_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Compare Schneider Electric and Safran by historical performance from 2024-01-01 to 2025-12-31."}'
```

The response includes `request_id`, `thread_id`, `status`, `answer`, an interpreted
request snapshot, validation, and deterministic `evidence` when execution occurs.
Set `include_evidence` to `false` to omit evidence. `status` is `success`,
`needs_clarification`, or `unsupported`; the latter two are normal HTTP 200
application outcomes. Missing or invalid Bearer tokens return 401; invalid bodies
return 422, including unexpected request fields. `/v1/chat` accepts at most
64 KiB of total body bytes, including streamed requests without `Content-Length`;
larger bodies return 413 before JSON parsing or graph execution. Unexpected
failures return a sanitized 500 with a `request_id`. API failure logs contain only
the generated request ID and fixed event, stage, and error-category fields,
without exception messages, tracebacks, headers, or provider response payloads.

For a clarification, send a second question with the first response's `thread_id`:

```bash
curl -sS http://localhost:8000/v1/chat \
  -H "Authorization: Bearer $EQUITY_STRATEGIST_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Use historical volatility for risk.","thread_id":"THREAD_ID_FROM_FIRST_RESPONSE"}'
```

Thread continuity lasts only while the server process lives. Restart and
redeployment lose in-memory checkpoints. While `InMemorySaver` is used, run one
Uvicorn worker AND one Railway replica. Multiple workers or replicas cannot share
clarification state. Durable or distributed checkpointing is a later milestone.

## Railway deployment

Connect this repository to a Railway service on the deployment branch. Railway
uses Python 3.12 from `.python-version` and the explicit `railway.toml` start
command, which binds to `0.0.0.0`, uses Railway's `PORT`, and starts one worker.
`requirements.txt` installs third-party dependencies; `--app-dir src` makes the
local source-layout package importable. Set the Railway service replica count to
exactly one; `--workers 1` controls Uvicorn workers, not Railway replicas.
The healthcheck is `/health`. Set `OPENAI_API_KEY` and
`EQUITY_STRATEGIST_API_KEY` in Railway service variables; optionally set
`EQUITY_STRATEGIST_MODEL`. Generate a public Railway domain after deploy.

To run the live acceptance battery against that domain, set
`EQUITY_STRATEGIST_BASE_URL` and `EQUITY_STRATEGIST_API_KEY` locally, then run:

```bash
python scripts/remote_api_smoke.py
```

The script calls the deployed API and requires live OpenAI and market-data access.
It is intentionally outside the deterministic test suite.

The deployed API passed all six remote acceptance checks: health, authentication
rejection, one-turn analysis, clarification, same-thread refinement, and horizon
plus benchmark evidence. Rerun the battery after deploying API changes.

## Persistence & Product Telemetry V1

The optional application path is:

```text
FastAPI -> AnalysisRunCoordinator -> EquityStrategistGraph
                    -> safe RunSnapshot -> RunRepository
```

`application/` owns run identity, UTC timestamps, monotonic duration, pipeline
observations and explicit snapshots. `persistence/` implements the repository
protocol with no-op and PostgreSQL adapters (SQLAlchemy 2 Core / Psycopg 3).
The graph and analytical engine remain independently usable without a database.
A connection/transaction is acquired only to save the completed snapshot, after
analysis and response mapping. Snapshot or database failures log only a fixed
message and generated request ID; they never suppress a successful answer.
There is no retry queue: a failed write loses that run's persisted record.
Connection, pool, statement and lock timeouts still protect ordinary database
operations. In addition, the application waits at most
`EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS` (default 2 seconds) for a run write.
This budget also covers recording analytical failures. On timeout, the completed
analytical response returns unchanged; only a fixed operational outcome and the
generated request ID are logged, never exception text or content.

One daemon run-write operation may be active per coordinator. While it remains
active, later snapshots are skipped immediately: no queue, replacement worker or
unbounded task accumulation is created. A timeout does not cancel a driver call;
that operation may still commit later. Do not interpret a timeout as proof that
no row exists. There are no retries. The slot becomes available when the operation
finishes. No database connection is acquired until that run's graph work finishes.

Shutdown stops admissions and waits at most the same budget. Repository disposal
runs once after the active write finishes, or in a bounded-wait daemon cleanup
when idle. A permanently stalled operation retains at most one run-write worker,
one snapshot and its connection until process exit; it cannot block process exit.
Feedback remains an acknowledged repository operation, not best-effort run recording.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | unset | PostgreSQL connection URL; used only when enabled or by operators |
| `EQUITY_STRATEGIST_PERSISTENCE_ENABLED` | `false` | Explicit `true` enables run persistence |
| `EQUITY_STRATEGIST_PERSIST_CONTENT` | `false` | Explicit `true` enables pilot content storage |
| `EQUITY_STRATEGIST_RETENTION_DAYS` | `30` | Positive retention period used by cleanup |
| `EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS` | `2` | Finite positive application budget for waiting on a run write or shutdown |

Missing/invalid database configuration degrades to no-op persistence with a
sanitized warning. The API starts without `DATABASE_URL`. `/health` remains a
liveness check, not a persistence-readiness check. Database credentials must be
supplied through environment variables; never put them in Alembic configuration.

Metadata-only rows omit question, request JSON, evidence, answer and feedback
comments. They retain IDs, statuses, validation issue codes, planned capabilities,
stage observations, versions and model identifiers. Full mode explicitly selects
structured request fields and the existing deterministic evidence serializer;
`include_evidence=false` affects only the HTTP response, not this storage policy.
System/developer prompts, raw provider payloads, downloaded price histories,
exception text/tracebacks and the HTTP request envelope (headers, cookies, IP,
Bearer authentication) are never snapshot inputs. Known configured secrets and
recognizable Bearer/OpenAI-token/PostgreSQL-URL strings are redacted from content.
Full mode intentionally retains user questions, answers and comments; it is for
this internal pilot, not a general personal-data anonymization service.

Persistent thread identity is always `thread-v1:` plus the SHA-256 hex digest of
a versioned domain prefix and the exact UTF-8 external thread ID. The shared
`application/thread_identity.py` helper is used for snapshot construction and
thread deletion. IDs are never trimmed, case-folded or generically redacted.
The API and LangGraph continue to use the original ID. This is deterministic
pseudonymization, not encryption or protection against guessing a known ID.

Snapshot version is `1`. `analysis_run` contains UUID `request_id` (PK), a
74-character `thread_id` digest with a format CHECK constraint, UTC `created_at`/`completed_at`, nonnegative `duration_ms`,
`outcome_status`, `validation_status`, nullable `question`/`request_json`/
`evidence_json`/`answer`, `validation_issue_codes`, `planned_capabilities`,
`error_category`, allowlisted `error_metadata`, `telemetry_json`, `model_metadata`,
optional `app_version`/`git_version`, `snapshot_version`, and `content_mode`.
JSON fields use JSONB. Indexes support creation-time cleanup and thread deletion.
`feedback` has UUID `feedback_id` (PK), `request_id` (indexed FK with cascading
delete), strict boolean `useful`, nullable 2,000-character `comment`, and UTC
`created_at`. These are the only two product tables; Alembic also maintains its
own migration revision table. Exact DDL is in
`migrations/versions/0001_product_telemetry.py`.

Validation response objects add `issue_codes` alongside existing human-readable
`issues`. Codes originate in validator branches (for example
`missing_start_date`, `missing_metric`, `constraints_unsupported`); unresolved
understanding semantics use `unresolved_semantics`. Older checkpoints default to
an empty code list. No prose classification is performed.
Known error categories are `provider_failure`, `insufficient_data`,
`ambiguous_asset`, and `asset_not_found`; unknown exceptions remain
`internal_error`. Yahoo's typed `YFPricesMissingError` is `insufficient_data`;
rate-limit and network errors remain `provider_failure`. No exception-string
classification is used. Error metadata permits only a fixed pipeline stage. HTTP failures
retain the sanitized 500 response; these categories are stored for operators.

Telemetry stages are understanding or refinement, validation, planning, execution,
interpretation, interpretation fallback and response serialization, plus initial
runtime construction when needed. Each observation contains duration and failure
status. Interpretation duration includes any fallback duration, so stage durations
must not be blindly summed. Run duration includes graph-lock waiting, graph work
and response mapping; it excludes snapshot storage latency. Completed request,
validation and plan information is retained even if a later stage fails. Observer
callbacks are isolated from analytical behavior and never enter checkpoint state.

### Feedback

```bash
curl -sS "$EQUITY_STRATEGIST_BASE_URL/v1/feedback" \
  -H "Authorization: Bearer $EQUITY_STRATEGIST_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"UUID_FROM_CHAT","useful":true,"comment":"Helpful comparison"}'
```

A successful write returns 201 with `feedback_id`, `request_id`, and
`status: "stored"`. Unknown/deleted/unpersisted runs return 404. Disabled or
unavailable storage returns 503. Invalid bodies return 422; the existing 64 KiB
body limit also applies to feedback. Multiple feedback submissions are permitted
as separate records; no user identity or deduplication is implied. All feedback
calls require the same Bearer authentication as chat. There are no history APIs.

### Migrations and operator commands

Run from the repository root with the virtual environment activated:

```bash
alembic upgrade head
python -m equity_strategist.persistence.cli cleanup
python -m equity_strategist.persistence.cli delete-request REQUEST_UUID
python -m equity_strategist.persistence.cli delete-thread THREAD_ID
```

The CLI requires `DATABASE_URL`, even when application persistence is disabled.
Cleanup deletes runs strictly older than the UTC cutoff and cascades to their
feedback. Thread deletion accepts the original external thread ID and applies the
same identity helper used for storage. Pass the API-returned ID, not its stored
digest. It does not clear in-memory
conversation checkpoints. Run cleanup daily; the retention variable alone does
not schedule deletion. Default 30-day retention is therefore enforced at the next
scheduled cleanup. Backups are governed separately by the database operator.
Neither application startup nor HTTP requests create tables or run migrations.
To review DDL without a database, run `alembic upgrade head --sql`.

### Exact Railway deployment sequence

1. Validate the working tree locally, then make this revision available to Railway
   through your normal deployment workflow. This implementation does not commit
   or deploy changes.
2. Add a PostgreSQL service in the same Railway project/environment. Keep the API
   at **one replica and one Uvicorn worker**; durable run rows do not replace
   `InMemorySaver`, and conversations are never reconstructed from run history.
3. Add an API-service reference variable `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   (use the actual database service name). Retain `OPENAI_API_KEY` and
   `EQUITY_STRATEGIST_API_KEY`; optionally retain `EQUITY_STRATEGIST_MODEL`.
   Set `EQUITY_STRATEGIST_PERSISTENCE_ENABLED=true`,
   `EQUITY_STRATEGIST_PERSIST_CONTENT=false` (or explicitly `true` for full pilot
   content), and `EQUITY_STRATEGIST_RETENTION_DAYS=30`. The optional
   `EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS` defaults to `2`.
4. Configure the API service's **Pre-deploy Command** as `alembic upgrade head`.
   This separate deployment step has access to Railway's private network and
   service variables; failure prevents the new deployment. Do not put migrations
   into the Uvicorn startup command. See
   [Railway pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command).
5. Deploy using the existing `railway.toml` start command and `/health` check.
   Confirm the migration is at `0001_product_telemetry` before sending pilot
   traffic. The existing `requirements.txt` includes all persistence dependencies;
   `alembic.ini` adds `src` to the migration import path.
6. Set local `EQUITY_STRATEGIST_BASE_URL`, `EQUITY_STRATEGIST_API_KEY`, and
   `EQUITY_STRATEGIST_SMOKE_EXPECT_PERSISTENCE=true`, then run
   `python scripts/remote_api_smoke.py`. This extends the existing battery with
   authenticated feedback, unknown-run feedback, and validation-code assertions.
   With persistence intentionally disabled, set the smoke expectation to `false`.
7. Schedule a daily operator job with access to the database. For a separate
   Railway cron service built from this revision, use a dedicated service config
   (not the API's `railway.toml`), no HTTP healthcheck, and the start command
   `PYTHONPATH=src python -m equity_strategist.persistence.cli cleanup`.
   Set `DATABASE_URL` and `EQUITY_STRATEGIST_RETENTION_DAYS=30`; configure a daily
   schedule such as `0 3 * * *`. Monitor its exit status. No OpenAI/API keys are
   needed by this cleanup job. See
   [Railway cron jobs](https://docs.railway.com/cron-jobs).
8. If storage causes operational trouble, set
   `EQUITY_STRATEGIST_PERSISTENCE_ENABLED=false` and redeploy. If PostgreSQL is
   unavailable, remove the migration pre-deploy command for this disabled-mode
   recovery deployment. Do not downgrade/drop tables merely to disable writes.

Railway variable changes must be deployed to take effect; use
[reference variables](https://docs.railway.com/variables) instead of copying database
credentials. The migration and cleanup are explicit operator actions, not runtime
background jobs.

### Verification

```bash
python -m pytest
ruff check .
ruff format --check .
git diff --check
```

The default suite is deterministic and excludes PostgreSQL tests even if a URL is
present. To opt into real PostgreSQL testing, supply an isolated test database via
`EQUITY_STRATEGIST_TEST_DATABASE_URL` and run:

```bash
python -m pytest -m postgres tests/integration/test_postgres_persistence.py
```

Integration tests create a unique schema, apply/round-trip migrations, test JSONB,
FK enforcement, feedback cascade, hashed-thread deletion/constraints, retention
and targeted deletion, then remove
only that schema. The test role needs schema-creation permission. Do not point this
at a production database. Live OpenAI/Yahoo checks remain in the existing scripts.
