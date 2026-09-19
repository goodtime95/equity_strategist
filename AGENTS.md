# Repository Guidelines

## Product and Architecture Goal

Equity Strategist is an independent specialist agent for equity-market analysis.

Its immediate goal is to provide reliable, deterministic, traceable, and testable equity analytics from structured or natural-language requests.

Its longer-term role is to become one specialist component inside a broader agentic architecture that may include:

* Market News Agent;
* Fixed Income Strategist;
* X-Asset Sales Agent.

Equity Strategist must remain independently usable, independently testable, and independently deployable.

A future higher-level agent must interact with Equity Strategist through a stable structured contract and must not depend on internal implementation details such as:

* LangGraph state;
* Yahoo Finance implementation details;
* internal services;
* planner implementation;
* provider-specific objects;
* internal domain reconstruction logic.

Design Equity Strategist for composition, but keep it decoupled from future agents until a real integration requirement exists.

---

## Core Design Principle

The architectural principle is:

```text
Probabilistic intelligence at the top.
Deterministic financial computation at the bottom.
```

Conceptually:

```text
Natural-language question
        |
        v
Understanding
        |
        v
Structured financial intent
        |
        v
Validation
        |
        v
Planning
        |
        v
Deterministic execution
        |
        v
Structured quantitative evidence
        |
        v
Interpretation
        |
        v
User
```

The LLM determines what the user is asking for and may explain deterministic evidence.

Python is the authoritative source for financial calculations and quantitative facts.

Do not put financial calculations in prompts, LLM interpretation code, or orchestration logic.

---

## Project Structure and Layer Responsibilities

Source lives in `src/equity_strategist/`.

### `domain/`

Defines stable financial and analytical contracts:

* requests;
* plans;
* capabilities;
* assets;
* universes;
* market series;
* datasets;
* validation statuses;
* structured results;
* execution results.

Domain objects must not depend on Yahoo Finance, OpenAI, LangGraph, or concrete infrastructure.

### `data_providers/` and `universe_providers/`

Retrieve external market data or universe constituent information.

Provider-specific representations must not leak into financial services or public specialist contracts.

### `asset_registry/` and `universe_registry/`

Provide stable known identities, aliases, and universe definitions.

They are not intended to become proprietary security masters.

### `extractors/`

Normalize provider observations into internal market representations.

### `compute/`

Contains pure deterministic financial calculations.

Functions in this layer should:

* receive explicit inputs;
* produce deterministic outputs;
* avoid network access;
* avoid orchestration logic;
* avoid provider-specific types.

### `tools/`

Expose narrow operational capabilities such as:

* asset resolution;
* point-in-time price retrieval.

Tools should remain focused and deterministic apart from explicit provider access.

### `services/`

Coordinate deterministic financial workflows:

* market-data acquisition;
* normalized dataset construction;
* alignment;
* financial calculations;
* typed result construction.

Financial methodology belongs here or in `compute/`, not in the planner, executor, LLM, or graph.

### `understanding/`

Transforms natural-language questions into typed `AnalysisRequest` objects.

Understanding extracts intent. It does not calculate financial results.

`RuleBasedUnderstanding` is a limited deterministic reference implementation, not a broad natural-language parser. When it cannot faithfully represent the full request, it must fail conservatively through explicit unresolved semantics or clarification rather than guess, substitute dates, or partially interpret the request.

`LLMUnderstanding` is the product path for broad natural-language interpretation.

### `strategists/`

Handle:

* request validation;
* planning;
* deterministic execution coordination;
* orchestration;
* LangGraph integration.

### `interpretation/`

Transforms validation states and structured execution evidence into user-facing responses.

### `app.py`

Is the composition root that assembles concrete dependencies.

### `api/`

Is a transport boundary only. It maps graph outcomes into dedicated, JSON-safe
public DTOs. Keep financial calculations, validation policy, planning, provider
access, asset resolution, and LLM prompts in their existing layers. Do not expose
LangGraph state or internal domain implementation objects in the HTTP contract.
Authenticate every endpoint except `/health`; keep API and OpenAI secrets in
environment variables only. The first HTTP milestone uses one process and one
worker with in-memory conversation checkpoints.

---

## Capability and Service Boundaries

A `Capability` represents an analytical operation that the planner can select and the executor can execute.

A capability does **not** need to map one-to-one to a service.

A capability may compose several services, and a service may support several capabilities.

Do not create a new capability merely because:

* the user uses a different phrasing;
* a parameter changes;
* a horizon changes;
* ranking direction changes;
* an existing analytical operation gains a new deterministic option.

Prefer parameterized reusable capabilities when the underlying operation remains conceptually the same.

The planner decides **what analytical operation is required**.

The executor coordinates **how planned operations are invoked and how compatible runtime dependencies can be reused**.

The executor must not become a financial-calculation or market-data-alignment layer.

Financial calculations, market-data alignment, slicing, horizon resolution, and methodology belong in deterministic services and compute functions.

---

## Request Fidelity

Never silently ignore part of the user's request.

Any parameter accepted by the understanding layer must be one of:

1. executed;
2. explicitly clarified;
3. explicitly rejected as unsupported.

A request must never be reported as successfully handled if part of its meaning was silently discarded.

Validator, planner, executor, services, and interpretation must remain aligned on supported semantics.

If a feature is only partially supported, encode that limitation explicitly rather than approximating silently.

Examples of request parameters requiring explicit treatment include:

* metrics;
* assets;
* universes;
* benchmark;
* constraints;
* ranking direction;
* top-N;
* explicit dates;
* target dates;
* horizons;
* performance methodology;
* rolling windows;
* requested currency;
* market periods.

The validator is the authoritative semantic boundary for deciding whether a structured request is:

* `READY`;
* `NEEDS_CLARIFICATION`;
* `UNSUPPORTED`.

Intrinsic type and object invariants belong in domain construction.

Do not duplicate the validator's full semantic policy inside the planner or executor.

---

## Quantitative Authority and Evidence

Deterministic Python execution is the authoritative source of quantitative evidence.

The intended model is:

```text
deterministic calculations
        ↓
structured evidence
        ↓
LLM reasoning and explanation
        ↓
user-facing answer
```

The LLM may:

* summarize;
* compare;
* explain;
* reason qualitatively from supplied deterministic evidence.

The LLM must not become the authoritative source for:

* prices;
* returns;
* volatility;
* drawdowns;
* correlations;
* rankings;
* benchmark-relative metrics;
* dates;
* asset identities;
* quantitative methodology.

Generated prose is a presentation layer, not an authoritative quantitative source.

Do not ask the LLM to independently recalculate financial metrics.

At this stage, do not introduce a second LLM judge or brittle deterministic prose validator.

Prefer:

* structured evidence;
* provenance;
* methodology;
* auditability;
* deterministic fallback.

LLM interpretation prompts should prohibit unsupported:

* forecasts;
* causal claims;
* external market context;
* recommendations;
* invented facts;
* LLM-generated quantitative calculations.

If LLM interpretation fails, deterministic interpretation is the fallback.

Validation and clarification responses should remain deterministic.

---

## Quantitative Traceability

Every financial result should progressively become auditable.

Structured results should preserve, where relevant:

* requested dates;
* effective dates;
* resolved instruments;
* symbol and name;
* currency;
* number of observations;
* price field;
* return methodology;
* annualization convention;
* frequency;
* benchmark;
* universe snapshot;
* exclusions;
* data-quality limitations;
* calculation coverage.

Do not rely on prose alone to communicate methodology.

If the effective calculation period differs from the requested period, expose the difference explicitly.

When several assets are compared or ranked, do not silently calculate them over incompatible effective endpoints.

The alignment policy must be:

* explicit;
* deterministic;
* testable;
* represented in structured results.

When several metrics in one execution require compatible historical data, prefer reusing a coherent execution-level dataset rather than independently fetching the same history for every metric.

Data-download breadth must not alter financial boundary eligibility. Each requested boundary must obey its explicit eligibility policy independently of other requested periods. Optimization of data reuse must never change calculation semantics.

Runtime market datasets must not be persisted into LangGraph state.

Do not build a global cache or market-data repository until real usage demonstrates that it is needed.

---

## Financial and Data Conventions

Financial conventions must be explicit and deterministic.

Do not silently change:

* adjusted versus raw prices;
* simple versus logarithmic returns;
* annualization factors;
* date inclusivity;
* business-day handling;
* market-calendar alignment;
* benchmark methodology;
* currency treatment;
* universe composition methodology.

When a convention changes:

1. update deterministic tests;
2. update structured result contracts where necessary;
3. update interpretation evidence;
4. update documentation.

Missing or ambiguous market data must follow an explicit policy:

* reject;
* clarify;
* degrade with a documented fallback;
* or return a structured insufficient-data failure.

Do not silently mix:

* inconsistent calendars;
* different currencies when the requested analysis assumes a common currency;
* incompatible price conventions;
* unrelated effective periods.

Yahoo Finance is currently a market-data provider, not an authoritative security master or institutional data source.

---

## Asset Identity

Asset resolution should prefer stable known identities when available.

The intended flow is:

```text
user asset reference
        |
        v
AssetRegistry
        |
    known locally?
      /     \
    yes      no
    |         |
    v         v
  Asset   provider fallback
              |
         unique match?
          /       \
        yes        no
        |           |
        v           v
      Asset     explicit failure
```

Do not silently select an ambiguous listing.

Provider fallback is intended to broaden real-world coverage without turning the local registry into a proprietary security master.

---

## Universe Semantics

Universe resolution is distinct from asset resolution.

Universe-based historical analysis must clearly distinguish between:

* current constituent snapshots;
* historical index composition;
* index-level data;
* constituent-level data.

Do not imply historical constituent membership when only a current snapshot is available.

Do not call raw constituent performance an index "contribution" unless weights and a valid contribution methodology are available.

Coverage, exclusions, and partial failures should become explicit when universe analytics require them.

---

## State and LangGraph

LangGraph is an orchestration and state-management layer, not a financial-calculation layer.

Keep graph state:

* small;
* stable;
* serializable;
* limited to information required to continue or reconstruct the conversation.

Do not store large runtime objects when identifiers or structured representations are sufficient.

Market datasets and provider objects are runtime dependencies and should remain outside persisted graph state.

Conversation state inside Equity Strategist primarily supports local analytical clarification.

General long-term user memory belongs to a higher-level conversational system.

When new fields are added to persisted graph state:

* preserve backward compatibility with older checkpoints;
* use explicit defaults when old checkpoints lack the field;
* test deserialization of historical state shapes.

Do not couple the public specialist contract to LangGraph-specific state structures.

---

## Planner Strategy

`EquityPlanner` is currently deterministic.

This is intentional.

The planner maps validated structured intent into supported capabilities.

The planner may become hybrid or LLM-assisted later when the capability set becomes broad enough to justify additional reasoning.

Do not introduce an LLM planner simply because more capabilities exist.

A future planner change must preserve:

* request fidelity;
* deterministic execution;
* explicit capability contracts;
* testability.

---

## Public Specialist Contract

The project should evolve toward a stable public interface that allows another agent or application to request an equity analysis and receive a structured result.

A future caller must not need to understand:

* LangGraph;
* internal services;
* provider implementations;
* internal planner details.

Public outcomes should distinguish, where relevant:

* success;
* clarification required;
* unsupported request;
* insufficient data;
* provider failure;
* internal execution failure;
* partial success.

Public results should eventually expose enough information to understand:

* what was requested;
* what was calculated;
* which assets or universes were resolved;
* requested versus effective period;
* methodology;
* conventions;
* benchmark;
* data limitations;
* exclusions;
* clarification requirements.

Do not expose internal implementation objects unless they are deliberately promoted to stable public types.

---

## Future Multi-Agent Architecture

The long-term integration target is conceptually:

```text
X-Asset Sales Agent
        |
        +-- Equity Strategist
        +-- Fixed Income Strategist
        +-- Market News Agent
```

Equity Strategist must remain usable independently.

Do not prematurely extract shared abstractions for future specialist agents.

Create shared abstractions only after at least two real implementations reveal a stable common pattern.

Prefer a small amount of temporary duplication over premature cross-domain abstractions whose boundaries are not yet understood.

---

## Error Handling

Prefer structured, domain-relevant failures over generic exceptions at public boundaries.

Distinguish, where relevant:

* invalid request;
* clarification required;
* unsupported capability;
* ambiguous asset identity;
* insufficient data;
* provider failure;
* internal execution failure;
* partial success.

Errors that can reasonably be resolved by the user should retain enough structured context for the conversation layer to request clarification.

Do not convert every internal failure into generic prose.

Preserve successful partial results only when the public result contract explicitly supports partial success.

---

## Coding Style and Naming

Use:

* Python 3.12;
* four-space indentation;
* double-quoted strings;
* 88-character line limit.

Use:

* `snake_case` for modules and functions;
* `PascalCase` for classes;
* `UPPER_SNAKE_CASE` for constants.

Add type annotations.

Prefer:

* typed domain models over raw dictionaries at architectural boundaries;
* small cohesive services over oversized classes;
* explicit dependency injection;
* provider protocols;
* immutable domain objects where practical;
* deterministic functions for financial calculations.

Avoid:

* hidden global state;
* duplicated financial calculations;
* financial logic in prompts;
* provider-specific logic leaking into services;
* large refactors unrelated to the requested feature;
* dependencies introduced solely to simplify a small local implementation.

---

## Testing Strategy

Tests belong in `tests/`.

Live integration checks, demonstrations, and product evaluation belong in `scripts/`.

Deterministic unit tests must not depend on:

* OpenAI;
* Yahoo Finance;
* external network access.

Use fakes, stubs, fixtures, or monkeypatching for external dependencies.

Tests should cover, where relevant:

* financial calculations;
* invalid inputs;
* domain invariants;
* request fidelity;
* validator behavior;
* capability routing;
* planner/executor alignment;
* clarification flows;
* ranking semantics;
* ambiguous identities;
* missing data;
* market-data alignment;
* effective date handling;
* evidence fidelity;
* LangGraph state compatibility;
* public result contracts;
* important error paths.

For numerical tests, prefer independently derived expected results rather than reproducing implementation logic inside assertions.

When fixing a bug, add a regression test unless there is a clear reason not to.

Do not modify a correct test merely to make an incorrect implementation pass.

The live E2E product battery should be extended as capabilities grow rather than replaced by parallel test frameworks.

Live integration scripts are not part of the deterministic default test suite.

---

## Development Commands

Run commands from the repository root.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

python -m pytest
ruff check .
ruff format --check .
git diff --check
```

Useful live/manual scripts may require external credentials and network access.

Supply `OPENAI_API_KEY` through the environment for LLM runs.

Always verify live scripts against current application signatures before relying on them.

---

## Definition of Done

Before considering a substantial task complete:

1. inspect the current implementation and relevant tests;
2. understand how the requested behavior fits the existing architecture;
3. identify the smallest coherent set of files to modify;
4. preserve architectural boundaries unless a change is explicitly justified;
5. implement the requested behavior;
6. add or update deterministic tests;
7. run focused tests during development;
8. run the full deterministic test suite;
9. run `ruff check .`;
10. run `ruff format --check .`;
11. run `git diff --check`;
12. run relevant live E2E checks when external credentials are available;
13. update documentation if behavior, contracts, or architecture changed;
14. report:

    * files changed;
    * behavioral changes;
    * architectural changes;
    * tests added or updated;
    * validation results;
    * remaining risks or limitations.

A task is not complete when relevant deterministic tests or static checks fail.

Do not perform broad refactors unless they are required by the feature or by a blocking architectural inconsistency.

If a broader refactor seems desirable but is not required, propose it separately.

---

## Commits and Pull Requests

Use focused feature branches for non-trivial changes.

Prefer concise conventional commit messages such as:

```text
feat: add performance horizons
fix: preserve ranking direction semantics
test: extend live e2e product battery
docs: align architecture guidance
```

Keep commits coherent.

PRs should explain:

* problem;
* changed behavior;
* architectural impact;
* validation commands and results;
* known limitations.

Do not mix unrelated cleanup into a feature PR unless explicitly requested.

---

## Configuration and Secrets

Never commit:

* credentials;
* `.env` files;
* virtual environments;
* caches;
* generated packaging artifacts;
* local machine-specific configuration.

Configuration that materially affects:

* model choice;
* provider behavior;
* calculation methodology;
* public application behavior

should be explicit and injectable where practical.

---

## Persistence and Product Telemetry V1

`application/run_coordinator.py` (`AnalysisRunCoordinator`) owns request IDs, timestamps, duration,
optional pipeline observations, explicit safe snapshots and best-effort storage.
It sits between HTTP transport and the graph and must not own financial logic.
The engine and graph must remain usable with no PostgreSQL configuration.
Neither telemetry, snapshot construction nor storage failures may suppress or
invalidate a successful financial analysis.

`persistence/` provides a `RunRepository` protocol, no-op adapter and PostgreSQL
adapter using SQLAlchemy 2 Core and Psycopg 3. Acquire connections/transactions only
for repository operations, never across graph/OpenAI/Yahoo execution. Use Alembic
for schema changes; never create tables or migrate during startup or requests.
V1 has only `analysis_run` and `feedback` product tables. Keep `InMemorySaver` and
never reconstruct conversations from telemetry history.

Default storage is metadata-only; full question/request/evidence/answer/comment
storage requires explicit `EQUITY_STRATEGIST_PERSIST_CONTENT=true`. Construct
snapshots from explicit fields and deterministic evidence, never generic graph or
provider-object serialization. Do not store secrets, request headers, cookies,
IP addresses, LLM prompts, environment dumps, raw provider payloads, tracebacks or
price histories. Error metadata is an allowlist (currently stage only), never
`str(exception)`. Codes originate where validation issues are created; unknown
exceptions remain `internal_error`. Preserve older checkpoints without issue codes.

Default retention is 30 days, enforced by the operator cleanup CLI scheduled
outside the API. Request/thread deletion cascades to feedback; it does not alter
conversation checkpoints. Feedback writes must explicitly report unavailable
storage rather than falsely acknowledge success. Keep database tests behind the
`postgres` marker and explicit test URL, outside the default deterministic suite.
Extend `scripts/remote_api_smoke.py` for API acceptance; do not create another
remote test framework.

Persist thread identity only through `application/thread_identity.py`; use the
same helper for storage and deletion by an external ID. Never redact identifiers
into shared placeholder values. API and LangGraph thread IDs remain unchanged.
Run writes must use the coordinator's bounded writer. Admit at most one operation,
drop subsequent snapshots while busy, and never spawn replacement workers for a
stalled operation. Timeouts leave commit status uncertain and must not trigger a
retry. Shutdown must remain bounded and defer disposal until an active write exits.
