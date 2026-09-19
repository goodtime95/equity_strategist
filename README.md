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
