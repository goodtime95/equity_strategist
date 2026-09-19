# Current State

Last update: 2026-09-19

---

## Current Milestone

The current milestone implements **Persistence & Product Telemetry V1** around the
existing authenticated FastAPI service. The analytical engine remains independently
usable without PostgreSQL; database or snapshot failures never suppress a successful
analysis. This revision has not been deployed or verified against a real database.
The earlier API deployment passed the six original remote acceptance checks; rerun
the extended battery after deployment rather than treating that result as V1 proof.

`FastAPI -> AnalysisRunCoordinator -> EquityStrategistGraph` adds run identity,
UTC timestamps, monotonic duration and optional stage observations. After execution
and response mapping, the coordinator builds an explicit version-1 snapshot and
best-effort writes it through `RunRepository`. No connection is held during graph,
OpenAI or Yahoo execution. A no-op adapter is the default; the PostgreSQL adapter
uses SQLAlchemy 2 Core and Psycopg 3. An application-level run-write budget
(`EQUITY_STRATEGIST_PERSISTENCE_TIMEOUT_SECONDS`, default 2 seconds) bounds waiting
independently of database/socket behavior. One admitted daemon write operation is
allowed; later snapshots are skipped while it is busy, without queues or replacement
workers. Shutdown is bounded and defers repository disposal until the active write
returns. A permanently stalled daemon/connection is released at process exit.
Timed-out writes may commit later; they are never retried. Responses can succeed
without durable rows. Feedback remains an acknowledged repository operation.

Alembic migration `0001_product_telemetry` creates only two product tables:
`analysis_run` (identity, timestamps, statuses, issue codes, capabilities, optional
content/evidence, safe errors, observations, model/app/git metadata and content/
snapshot versions; persisted thread IDs must match a versioned digest format) and `feedback` (UUID, cascading run FK, usefulness, bounded
optional comment and timestamp). Alembic's revision table is migration machinery.
Application startup and requests never create tables or run migrations.

Persistence is enabled explicitly with `EQUITY_STRATEGIST_PERSISTENCE_ENABLED=true`
and `DATABASE_URL`. The default content policy is metadata-only; full pilot content
requires `EQUITY_STRATEGIST_PERSIST_CONTENT=true`. The existing deterministic evidence
serializer is the quantitative storage contract. Prompts, raw provider data,
price histories, request envelopes, exception messages and tracebacks are excluded.
Known configured secrets and recognizable credential strings are redacted from
content. Cleanup defaults to 30 days (`EQUITY_STRATEGIST_RETENTION_DAYS`) and must be
scheduled by an operator; request/thread deletion cascades to feedback.

A single `persistent_thread_id()` helper produces a versioned SHA-256 digest of
the exact external ID in both content modes. This prevents raw caller-controlled
thread content from entering storage and avoids redaction collisions. Deletion
accepts the external ID and uses the same transformation. The API and LangGraph
retain original IDs; only persistence uses the digest. The initial undeployed
migration includes the digest format constraint; no compatibility migration is
needed.

`POST /v1/feedback` uses the existing Bearer authentication: 201 stored, 404 unknown
run, 503 storage unavailable, 422 invalid body. Its comment limit is 2,000 characters;
metadata-only mode discards comments. The 64 KiB body limit covers chat and feedback.
There are no history browsing endpoints. Validation responses add stable
`issue_codes`, assigned directly at validator branches, with defaults for older
checkpoints. Known provider, data-availability and asset-resolution failures have
typed categories; unknown failures remain `internal_error` with stage-only metadata.
Yahoo's typed missing-price error now maps to `insufficient_data`; network and
rate-limit failures remain `provider_failure`.

Understanding/refinement, validation, planning, execution, interpretation,
interpretation fallback and serialization emit optional isolated timing observations.
Completed intent and plan metadata remain observable if a later stage fails.
Runtime observations and datasets never enter checkpoint state. Deterministic tests
cover policy, privacy, failure isolation, feedback and offline migrations. Real
PostgreSQL tests require an explicit test URL and `-m postgres`; remote acceptance
extends `scripts/remote_api_smoke.py`. See README for the exact Railway deployment,
migration, cleanup and rollback sequence.

Conversation checkpoints use `InMemorySaver`. Thread continuity survives only
while the single server process remains alive; restart or redeployment loses it.
The service must run with one Uvicorn worker AND one Railway replica. The worker
flag does not configure the Railway replica count. Durable or distributed
checkpointing is a later milestone.

Equity Strategist now supports a complete conversational quantitative workflow:

```text
Natural-language question
        |
        v
UnderstandingProvider
        |
        +---------------------------+
        |                           |
        v                           v
RuleBasedUnderstanding       LLMUnderstanding
        |                           |
        +-------------+-------------+
                      |
                      v
               AnalysisRequest
                      |
                      v
          AnalysisRequestValidator
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
        READY   NEEDS_CLARIFICATION UNSUPPORTED
          |
          v
              EquityPlanner
          |
          v
              AnalysisPlan
          |
          v
             EquityExecutor
          |
          v
       Deterministic services
          |
          v
        Market data + compute
          |
          v
       Structured execution results
          |
          v
       InterpretationProvider
          |
          +-------------------------+
          |                         |
          v                         v
DeterministicInterpretation   LLMInterpretation
          |                         |
          +------------+------------+
                       |
                       v
                      User
```

The core principle remains:

```text
LLM decides WHAT.
Python decides HOW.
```

More precisely:

* the LLM may interpret user intent;
* Python validates, plans, retrieves data, and calculates quantitative results;
* deterministic execution produces structured evidence;
* the LLM may explain, compare, and summarize that evidence.

Python execution remains the authoritative source of quantitative facts.

---

## Current Product Baseline

The full LLM-powered product path has been exercised through a live E2E battery.

The product battery contains 26 analyst-style cases and passed live:

```text
26 / 26 cases
```

The battery covers:

* external equity resolution;
* performance comparison;
* volatility comparison;
* performance + volatility in one request;
* correlation;
* drawdown;
* point-in-time price on a non-trading date;
* explicit-asset performance ranking;
* explicit-asset volatility ranking;
* highest/top-N ranking;
* lowest/bottom-N ranking;
* universe performance ranking;
* ambiguous risk clarification;
* missing metric clarification;
* missing asset clarification;
* unsupported capability handling;
* executable benchmark performance;
* relative performance and excess return;
* standard and multi-horizon performance;
* unsupported free-form constraints;
* assets-versus-universe ambiguity;
* multi-turn clarification.

The live battery is implemented in:

```text
scripts/e2e_question_battery.py
```

It is the main product-regression harness and should be extended as new capabilities are introduced rather than replaced by parallel E2E frameworks.

---

## Implemented Architecture

### Domain

The domain layer defines typed contracts including:

* `Asset`;
* `DailyPriceObservation`;
* `MarketSeries`;
* `MarketDataset`;
* `PriceOnDateResult`;
* `AnalysisRequest`;
* `AnalysisPlan`;
* `PlanStep`;
* `Capability`;
* `AnalysisExecutionResult`;
* `StepExecutionResult`;
* `PerformanceAnalysisResult`;
* `PerformancePeriodResult`;
* `VolatilityComparisonResult`;
* `CorrelationAnalysisResult`;
* `DrawdownComparisonResult`;
* `RankingResult`;
* `Universe`;
* `RequestValidationResult`.

`AnalysisRequest` represents structured user intent.

It may intentionally be incomplete.

Execution readiness is decided later by `AnalysisRequestValidator`.

---

## Understanding Layer

Two implementations currently exist.

### RuleBasedUnderstanding

Provides a deterministic reference path for supported simple request shapes.

It is intentionally limited and conservative, and is not intended to become a general NLP engine. Historical horizon anchors it cannot parse and incomplete horizon lists require clarification; they must not silently become today's date or a partial analysis. `LLMUnderstanding` is the product path for broad natural-language interpretation.

### LLMUnderstanding

Uses the OpenAI Responses API with structured output to convert natural-language questions into `AnalysisRequest`.

The request currently captures concepts including:

* objective;
* metrics;
* assets;
* universe;
* start date;
* end date;
* target date;
* benchmark;
* constraints;
* unresolved information;
* ranking direction;
* top-N.
* performance measure;
* typed performance horizons.

Current objectives include:

* `GET`;
* `COMPARE`;
* `RANK`;
* `ANALYZE`.

Current metrics include:

* `PRICE`;
* `PERFORMANCE`;
* `VOLATILITY`;
* `CORRELATION`;
* `DRAWDOWN`.

The LLM is expected to extract only user intent.

Implementation details such as financial methodology or standard deterministic conventions are not automatically turned into user clarification questions.

---

## Validation

`AnalysisRequestValidator` sits between Understanding and Planning.

It returns:

* `READY`;
* `NEEDS_CLARIFICATION`;
* `UNSUPPORTED`.

### READY

The request contains enough information and its supported semantics satisfy execution preconditions.

`READY` does not guarantee that:

* asset resolution will succeed;
* Yahoo Finance will respond;
* enough market data will exist.

Those are later execution concerns.

### NEEDS_CLARIFICATION

The request is incomplete or ambiguous in a way the user can repair.

Examples include:

* missing assets;
* missing universe;
* missing metric;
* missing analysis period;
* ambiguous concepts such as generic "risk";
* simultaneous explicit assets and universe.

### UNSUPPORTED

The request is understood, but the current quantitative engine does not support the requested semantics.

Examples include currently unsupported combinations such as:

```text
RANK + DRAWDOWN
```

and unsupported modifiers such as free-form constraint requests.

The validator prevents unsupported or incomplete semantics from being silently discarded.

---

## Ranking Semantics

Ranking requests support:

* explicit highest/lowest direction;
* optional positive `top_n`.

If the user explicitly requests ranking direction, it is represented structurally.

If the user simply asks to rank assets without specifying direction, understanding may leave direction unspecified and deterministic execution owns the default ordering convention.

Ranking controls are applied by deterministic ranking services.

They are not implemented through LLM sorting.

---

## Planning

`EquityPlanner` is currently deterministic.

Current capability mapping includes:

```text
GET + PRICE
    -> PRICE_ON_DATE

COMPARE + PERFORMANCE
    -> COMPARE_PERFORMANCE

GET/ANALYZE + PERFORMANCE
    -> COMPARE_PERFORMANCE

COMPARE + VOLATILITY
    -> COMPARE_VOLATILITY

COMPARE + DRAWDOWN
    -> COMPARE_DRAWDOWN

ANALYZE + CORRELATION
    -> ANALYZE_CORRELATION

RANK + PERFORMANCE
    -> RANK_PERFORMANCE

RANK + VOLATILITY
    -> RANK_VOLATILITY
```

The planner supports multi-step analysis.

Example:

```text
COMPARE
metrics:
- PERFORMANCE
- VOLATILITY
- DRAWDOWN
```

produces three deterministic plan steps.

The planner is intentionally deterministic at the current stage.

A hybrid or LLM-assisted planner remains a possible future evolution once the capability space becomes sufficiently broad.

---

## Execution

`EquityExecutor` executes `AnalysisPlan` steps deterministically.

It currently routes work to services including:

* `MarketQueryService`;
* `PerformanceAnalysisService`;
* `VolatilityAnalysisService`;
* `CorrelationAnalysisService`;
* `DrawdownAnalysisService`;
* `RankingAnalysisService`;
* `UniverseConstituentService`.

Execution results remain structured domain objects before interpretation.

The executor coordinates operations but does not own financial calculations.
For compatible explicit-period price-history steps, it builds one runtime dataset
and reuses it across performance, volatility, correlation, and drawdown services.
The dataset is never persisted in LangGraph state.

---

## Market-Data Architecture

Yahoo Finance is currently the primary market-data provider.

It is not treated as:

* an authoritative security master;
* an institutional-quality historical constituent source;
* a complete fundamentals platform;
* a production-grade benchmark methodology source.

The main historical-data dependency flow is:

```text
YahooFinanceProvider
        |
        v
AssetResolver
        |
        v
MarketSeriesService
        |
        v
MarketDatasetService
        |
        +-----------------------------+
        |             |               |
        v             v               v
 Performance     Volatility      Correlation
        |             |               |
        v             v               v
   Drawdown        Ranking          ...
```

The same provider/resolution infrastructure is reused by:

* `PriceTool`;
* `MarketQueryService`;
* `UniverseAssetResolver`.

A global cache or MarketStore has intentionally not yet been introduced.

---

## Asset Resolution

Asset resolution no longer depends only on the small local registry.

The current conceptual flow is:

```text
natural-language asset reference
        |
        v
AssetResolver
        |
        v
AssetRegistry
        |
    local match?
      /      \
    yes       no
    |          |
    v          v
  Asset   provider fallback
               |
          resolved?
           /     \
         yes      no
         |         |
         v         v
       Asset     failure
```

The local `AssetRegistry` remains useful for:

* stable known identities;
* aliases;
* known tickers;
* known ISIN mappings.

Provider fallback broadens real-world coverage.

The live E2E suite has successfully exercised externally resolved names including European equities outside the small original registry.

Ambiguous or unresolved identities should fail explicitly rather than being silently approximated.

---

## Universe Architecture

The project contains explicit universe abstractions.

Current universe types include:

* `STATIC`;
* `DYNAMIC`.

Examples include:

* a static Luxury Europe universe;
* CAC 40 through the configured Euronext universe provider.

Universe resolution is intentionally separated from asset resolution.

Current universe-based analytical support remains limited.

Performance ranking over an available universe is supported.

The current CAC 40 implementation represents a current constituent snapshot.

It should not be interpreted as historical CAC 40 composition for past dates.

The project currently has no historical constituent database or historical index-weight system.

---

## MarketSeries and MarketDataset

### MarketSeries

`MarketSeries` is the normalized internal time-series representation.

Supported series kinds include:

* `PRICE`;
* `RETURN`;
* `RATE`;
* `VOLATILITY`;
* `CORRELATION`;
* `DRAWDOWN`;
* `SPREAD`;
* `VOLUME`.

It validates properties including:

* `DatetimeIndex`;
* sorted dates;
* no duplicate dates;
* numeric values;
* no missing values.

### MarketDataset

`MarketDataset` represents a coherent collection of `MarketSeries`.

It is used by analysis services to perform deterministic calculations across multiple assets.

Datasets can currently be built from:

* asset queries;
* already resolved `Asset` objects.

The resolved-asset path is used by universe workflows.

---

## Compute Engine

Implemented deterministic calculations include:

### Returns

* simple returns;
* logarithmic returns.

### Performance

* total performance;
* period performance;
* annualized performance;
* cumulative performance series.

Total and annualized performance are exposed over explicit or typed standard
horizons. Benchmark-relative and excess-return calculations are also executable.

### Volatility

* annualized historical volatility;
* rolling volatility.

Historical volatility is exposed.

Rolling volatility exists as a compute primitive but is not yet a user-facing capability.

### Correlation

* pairwise correlation;
* rolling correlation;
* common-date alignment.

Pairwise correlation is exposed.

Rolling correlation is not yet a user-facing capability.

### Drawdown

* drawdown series;
* maximum drawdown;
* peak date;
* trough date;
* recovery date.

Maximum drawdown analysis is exposed.

All authoritative quantitative calculations are performed in Python.

---

## Current User-Facing Analyses

### Point-in-Time Price

Example:

```text
What was LVMH's price on March 15, 2020?
```

For non-trading dates, the engine may use the previous available session according to its deterministic policy.

### Performance Comparison

Analyze total or annualized performance for one or several assets over an explicit
period or the typed 1M, 3M, 6M, YTD, 1Y, and 3Y horizons. Multiple horizons can be
calculated from one market-data download.

### Benchmark Performance

An explicit benchmark is calculated and exposed for total or annualized requests.
Relative performance uses relative wealth evolution. Excess return subtracts the
benchmark's total period return from the asset's total period return.

### Volatility Comparison

Compare annualized historical volatility across several assets.

### Correlation Analysis

Analyze historical pairwise correlations.

### Drawdown Comparison

Compare maximum historical drawdowns.

### Performance Ranking

Rank explicit assets or a supported universe by historical performance for every
requested horizon, with independent highest/lowest and top-N selection.

### Volatility Ranking

Rank explicit assets by historical volatility.

### Multi-Metric Analysis

A single request may execute several deterministic analytical steps.

For example:

```text
Compare Schneider Electric and Safran in performance and volatility
over the last two years.
```

can produce:

```text
COMPARE_PERFORMANCE
COMPARE_VOLATILITY
```

within one analysis.

---

## Interpretation Layer

Two interpretation implementations exist.

### DeterministicInterpretation

Provides stable deterministic formatting.

It is used by the deterministic reference pipeline and as fallback for failed LLM interpretation.

### LLMInterpretation

Receives serialized evidence generated from deterministic execution results.

The LLM may:

* summarize;
* compare;
* explain;
* reason over supplied evidence.

It is instructed not to:

* introduce new quantitative facts;
* independently calculate metrics;
* add unsupported forecasts;
* add causal explanations;
* introduce external market context.

Client failures and malformed or empty LLM responses fall back to deterministic formatting.

Validation and clarification responses remain deterministic.

The project intentionally does not currently use:

* a second LLM judge;
* regex-based prose policing;
* a deterministic semantic validator of generated prose.

Auditability comes from preserving deterministic structured evidence.

---

## Builders

Two application pipelines are available.

### Deterministic Reference Pipeline

```python
build_equity_strategist()
```

Uses:

* `RuleBasedUnderstanding`;
* `DeterministicInterpretation`.

### LLM-Powered Pipeline

```python
build_llm_equity_strategist()
```

Uses:

* `LLMUnderstanding`;
* `LLMInterpretation`.

The LLM builder shares the same injected OpenAI client between understanding and interpretation.

Both pipelines share the same:

* validator;
* planner;
* executor;
* market-data layer;
* deterministic services;
* compute engine.

---

## Conversational Clarification

LangGraph checkpointing supports local multi-turn analytical clarification.

For example:

```text
User:
Compare Schneider Electric and Safran in performance and risk
over the last two years.

System:
"risk" needs clarification.

User:
Volatility.
```

The previous structured request can be refined into a complete request rather than reconstructed from scratch.

Conversation state is intended for local Equity Strategist workflow continuity.

It is not intended to become general long-term user memory.

---

## LangGraph State

LangGraph is used for orchestration and conversational state.

Persisted state is kept serializable.

Large runtime objects such as:

* `MarketDataset`;
* provider clients;
* execution service instances

are not intended to be checkpointed.

When persisted request fields evolve, deserialization must remain backward-compatible with older checkpoints.

---

## Current Limitations

### Historical Period Alignment

Comparisons and rankings use the latest common trading session available on or
before each requested boundary. Requested and effective dates are both preserved.
All compared assets and the benchmark use the same effective endpoints.

### Correlation Return Intervals

A known pre-existing limitation remains: correlation computes returns independently
before aligning their observation dates. When calendars or intermediate sessions
differ, paired returns may span different intervals. Common effective endpoints
do not fix this limitation; return-interval/calendar redesign is outside this batch.

### Quantitative Traceability

Structured price-history results now expose, where relevant:

* requested versus effective dates;
* observation counts;
* price field;
* return methodology;
* annualization conventions;
* currency.

Provider retrieval timestamps and a generic provenance framework remain outside
the current scope.

### Repeated Market-Data Retrieval

A multi-step request such as:

```text
performance + volatility + drawdown
```

reuse one execution-level dataset when the requested period and price convention
are compatible. Independent service calls still retrieve their own data.

### Currency

Historical performance is currently based on each asset's native quoted series.

There is no common-currency FX conversion layer.

The engine must not claim common-currency performance unless such conversion is explicitly implemented.

### Universe Coverage

Only selected capabilities currently support universe execution.

The current universe model does not provide:

* historical constituent membership;
* historical weights;
* index contribution methodology.

### Data Quality

Yahoo Finance is suitable for the current product-development stage and historical-price analytics.

It is not sufficient by itself for institutional-grade:

* historical constituent databases;
* index weights and contributions;
* documented FX fixing methodology;
* risk-free rate curves;
* historical fundamentals;
* consensus estimates;
* news;
* authoritative exchange calendars.

---

## Completed Performance Milestone

The implemented milestone is:

```text
Stage 0 — Quantitative foundations
        +
Stage 1 — Performance, horizons and benchmark
```

This work is implemented on:

```text
feat/performance-horizons-benchmark
```

### Stage 0 — Quantitative Foundations

Implemented foundations:

* explicit common effective endpoints for multi-asset comparisons and rankings;
* preservation of requested versus effective dates;
* richer structured calculation metadata;
* observation counts;
* price-field visibility;
* return-method visibility;
* annualization metadata where relevant;
* asset currency in analytical results;
* propagation of these facts into structured interpretation evidence;
* coherent execution-level reuse of compatible historical datasets.

The executor may coordinate compatible dataset reuse.

It must not implement:

* market-data alignment;
* financial calculations;
* horizon resolution;
* slicing methodology.

Those responsibilities remain in deterministic services.

### Stage 1 — Performance, Horizons and Benchmark

Implemented typed performance measures:

```text
TOTAL
ANNUALIZED
RELATIVE
EXCESS_RETURN
```

Implemented standard horizons:

```text
1M
3M
6M
YTD
1Y
3Y
```

Implemented behavior includes:

* total performance;
* annualized performance;
* standard-horizon performance;
* multi-horizon performance;
* executable benchmark support;
* relative performance;
* excess return;
* ranking by horizon;
* top/bottom selection per horizon.

No separate capability should be created for each horizon.

Existing performance operations should remain parameterized by structured request fields.

### Endpoint Policy

For historical comparison or ranking:

1. requested dates remain unchanged;
2. each boundary represents a valuation date;
3. the effective endpoint is the latest common session available on or before that boundary;
4. all compared assets and benchmarks use the same effective endpoints;
5. at least two distinct common endpoints are required;
6. series are sliced inclusively between effective endpoints;
7. observation count may remain asset-specific because intermediate sessions may differ;
8. each start and end boundary independently admits observations from the preceding ten calendar days through the requested date, inclusively; missing eligible common sessions cause an explicit failure;
9. fetching a longer interval for companion horizons never widens another boundary's eligibility window.

For YTD, the theoretical starting boundary is January 1 and should resolve to the latest common session on or before January 1, allowing the calculation to use the previous year-end close.

This is the current deterministic service behavior. Deterministic responses disclose requested and effective periods when they differ, including previous-session adjustments.

A resolved series may serve as both a requested asset and benchmark, with one download. Duplicate entries within the requested asset list remain invalid.

### Live Product Battery

`scripts/e2e_question_battery.py` contains 26 live cases. Horizon cases assert the
requested anchor, horizons, and performance measure in requests and results. The
historical YTD case also asserts known effective endpoints. Conservative rejection
of mixed supported/unparsed horizons in the rule-based reference path is covered
by deterministic regression tests.

---

## Subsequent Capability Batches

After the performance/horizon/benchmark milestone, the current roadmap is:

### Risk and Dependence

Potential capabilities:

* rolling volatility;
* drawdown duration and recovery;
* downside volatility with explicit threshold;
* beta;
* tracking error;
* return/volatility;
* Calmar;
* correlation matrix;
* rolling correlation;
* covariance.

Sharpe and Sortino should not be introduced with an implicit risk-free rate or target return.

### Momentum and Technical Analytics

Potential capabilities:

* moving averages;
* above/below moving average;
* distance to moving average;
* distance to period high/low;
* configurable momentum;
* momentum rankings;
* deterministic trend classification;
* best/worst day;
* positive-session ratio.

### Breadth and Universe Analytics

Potential capabilities:

* percentage of constituents positive;
* percentage above a moving average;
* mean/median constituent performance;
* cross-sectional dispersion;
* strongest/weakest constituents;
* ranking by performance, volatility, drawdown, or momentum.

These capabilities must preserve:

* universe snapshot provenance;
* coverage;
* exclusions;
* partial failures.

---

## Longer-Term Direction

Equity Strategist is intended to become the first specialist inside a broader financial reasoning system.

Potential future modules include:

* Fixed Income;
* FX;
* Credit;
* Cross Asset;
* Structured Products.

The long-term pattern remains:

```text
Natural language
        |
        v
Financial reasoning
        |
        v
Structured analytical request
        |
        v
Validation
        |
        v
Analytical plan
        |
        v
Deterministic financial tools
        |
        v
Structured quantitative evidence
        |
        v
LLM synthesis
```

The immediate priority is to validate V1 against PostgreSQL and redeploy the
extended remote acceptance battery while
preserving:

* request fidelity;
* quantitative authority;
* traceability;
* testability;
* architectural boundaries;
* useful analyst-facing behavior.
