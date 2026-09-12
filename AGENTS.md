# Repository Guidelines

## Product and Architecture Goal

Equity Strategist is an independent specialist agent for equity-market analysis.

Its immediate goal is to provide reliable, deterministic, traceable, and testable equity analytics from structured or natural-language requests.

Its longer-term role is to become one specialist component inside a broader agentic architecture that may include:

- Market News Agent
- Fixed Income Strategist
- X-Asset Sales Agent

Equity Strategist must remain independently usable, independently testable, and independently deployable.

The future X-Asset Sales Agent must interact with Equity Strategist through a stable, structured public contract and must not depend on internal implementation details such as:

- LangGraph state
- Yahoo Finance implementation details
- internal services
- planner implementation
- provider-specific objects
- internal domain reconstruction logic

Do not introduce dependencies on future agents until a real integration requirement exists.

Design Equity Strategist for composition, but keep it decoupled from the future multi-agent system.

## Project Structure and Architecture

Source lives in `src/equity_strategist/`.

`domain/` defines requests, plans, assets, series, datasets, statuses, and results.

`data_providers/` and `universe_providers/` retrieve external data or constituent snapshots.

`asset_registry/` and `universe_registry/` define known instruments and universes.

`extractors/` normalize provider observations into internal market representations.

`compute/` implements pure deterministic financial calculations.

`tools/` expose narrow operational capabilities such as asset resolution or point-in-time price retrieval.

`services/` coordinate acquisition, datasets, calculations, and construction of typed business results.

`understanding/` transforms natural language into structured analysis requests.

`strategists/` handle validation, planning, execution, orchestration, and LangGraph integration.

`interpretation/` transforms structured results and statuses into user-facing responses.

`app.py` assembles concrete dependencies.

Keep financial calculations in Python, never in LLM prompts.

Lower layers must not depend on the strategist, LangGraph, or LLM.

Preserve provider protocols, dependency injection, and typed domain boundaries.

Provider-specific representations must not leak into business services or public specialist contracts.

The LLM should interpret intent and produce structured requests; it must not become the source of truth for deterministic financial calculations.

Tests belong in `tests/`; live integration checks and demos belong in `scripts/`.

Documentation is in `docs/`, notably `architecture_updated.md` and `current_state.md`.

Treat code as authoritative when documentation lags, but update documentation when behavior or architecture materially changes.

## Public Specialist Contract

The project should evolve toward a stable public interface that allows another agent or application to request an equity analysis and receive a structured result.

The future caller must not need to understand LangGraph, internal services, provider implementations, or planner details.

Public results should distinguish, where relevant:

- success
- clarification required
- unsupported request
- insufficient data
- external provider error
- partial success

Public results should expose enough structured information for a caller to understand:

- what was requested
- what was actually calculated
- which assets or universes were resolved
- requested period versus effective period
- methodology and conventions
- data source and provenance
- limitations or missing data
- clarification requirements when the request cannot yet be executed

Do not expose internal LangGraph state, provider objects, or implementation-specific domain objects through the public contract unless they are deliberately promoted to stable public types.

The long-term integration target is conceptually:

```text
X-Asset Sales Agent
        |
        +-- Equity Strategist
        +-- Fixed Income Strategist
        +-- Market News Agent
```

Equity Strategist must remain usable without the X-Asset Sales Agent.

## Request Fidelity

Never silently ignore a user request parameter.

Any parameter accepted by the understanding layer must be one of:

1. executed;
2. explicitly clarified;
3. explicitly rejected as unsupported.

A request must never be reported as successfully handled if part of its meaning was silently discarded.

Validator, planner, executor, and interpretation must remain aligned on supported capabilities.

If a capability is only partially supported, encode that limitation explicitly rather than approximating silently.

Examples of parameters requiring explicit handling include benchmark, constraints, ranking direction, top-N requests, requested metrics, date ranges, universes, and asset lists.

## Quantitative Traceability

Every financial result should progressively become auditable.

Prefer structured result objects that preserve, where relevant:

- requested dates
- effective dates
- resolved instruments
- number of observations
- price type
- return methodology
- annualization convention
- frequency
- currency
- data source
- retrieval timestamp
- universe snapshot or version
- exclusions
- data-quality limitations
- calculation coverage

Do not rely on prose alone to communicate methodology.

If the effective calculation period differs from the requested period, expose that difference explicitly.

If multiple metrics are calculated for the same request, prefer using a consistent execution-level market-data snapshot where practical so that results are comparable.

## Financial and Data Conventions

Financial conventions must be explicit and deterministic.

Do not introduce implicit changes to:

- adjusted versus raw prices
- simple versus logarithmic returns
- annualization factors
- date inclusivity
- business-day handling
- market-calendar alignment
- currency treatment
- universe composition methodology

When a convention changes, update tests and documentation.

Missing or ambiguous market data must result in an explicit policy: reject, clarify, degrade with documented fallback, or return insufficient-data status.

Do not silently mix inconsistent calendars, currencies, or price conventions.

## State and LangGraph

LangGraph is an orchestration and state-management layer, not a financial-calculation layer.

Financial calculations belong in deterministic services and compute functions.

Keep graph state small, stable, and serializable.

Checkpoint only information necessary to continue or reconstruct a conversation or analysis.

Avoid storing large runtime objects when stable identifiers or structured representations are sufficient.

Conversation memory inside Equity Strategist should primarily support local analytical clarification.

The broader conversational memory of a future X-Asset Sales Agent should remain the responsibility of the higher-level orchestrator unless a concrete requirement demonstrates otherwise.

Do not couple the public specialist contract to LangGraph-specific state structures.

## Future Multi-Agent Architecture

Do not prematurely create shared abstractions for Equity, Fixed Income, Market News, or X-Asset Sales.

Create shared abstractions only after at least two real implementations reveal a stable common pattern.

Do not move code into a shared package merely because it might be reusable later.

Prefer duplication of a small concept over a premature abstraction whose domain boundaries are not yet understood.

Equity Strategist should be designed for composition, but not coupled to future agents.

When a future specialist is implemented, compare its real requirements with Equity Strategist before extracting common infrastructure.

## Error Handling

Prefer structured, domain-relevant failures over generic exceptions at public boundaries.

Distinguish, where relevant:

- invalid request
- clarification required
- unsupported capability
- ambiguous asset identity
- insufficient data
- provider failure
- internal execution failure
- partial success

Do not convert every failure into generic prose.

Errors that can reasonably be resolved by the user should be surfaced in a form that allows the conversation layer to ask for clarification.

Preserve successful partial results if the public contract explicitly supports partial success; otherwise fail deterministically and consistently.

## Development Commands

Use Python 3.12 and run commands from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m pytest tests/test_returns.py
ruff check .
ruff format --check .
ruff format .
python scripts/demo_equity_strategist.py
```

The demo uses rule-based understanding but retrieves live Yahoo data.

`python scripts/e2e_conversation_smoke.py` additionally calls OpenAI.

Verify older scripts against current signatures before using them; several may reference retired APIs.

Do not treat a live integration script as part of the deterministic default test suite.

## Coding Style and Naming

Use four-space indentation, double-quoted strings, and an 88-character line limit.

Ruff targets Python 3.12 and checks imports, common errors, bug risks, and modernization.

Use:

- `snake_case` for modules and functions;
- `PascalCase` for classes;
- `UPPER_SNAKE_CASE` for constants.

Add type annotations.

Prefer typed domain models over raw dictionaries at architectural boundaries.

Return structured domain results from services.

Prefer small cohesive services over oversized classes.

Avoid hidden global state.

Avoid duplicated financial calculations.

Do not put provider logic inside services when it belongs behind a provider protocol.

Do not put financial logic in prompts or interpretation code.

Do not introduce dependencies solely because they make a small local task shorter.

## Testing Guidelines

Use pytest with `test_*.py` files and top-level `test_*` functions.

Replace providers and LLM clients with fakes or `monkeypatch`; deterministic unit tests must not depend on external services.

Cover:

- financial calculations;
- invalid inputs;
- request fidelity;
- capability routing;
- validator/planner/executor alignment;
- clarification behavior;
- ambiguous identities;
- missing data;
- public result contracts;
- state isolation;
- important error paths.

For numerical tests, prefer independently derived expected results rather than reproducing the same implementation logic in the assertion.

Fakes should validate relevant inputs when argument propagation is part of the behavior being tested.

No coverage threshold is currently configured.

Keep live checks separate from the default suite.

When fixing a bug, add a regression test unless there is a clear reason not to.

Do not modify a test merely to make an incorrect implementation pass.

## Definition of Done

Before considering a code task complete:

1. inspect the existing implementation and relevant tests;
2. explain how the requested change fits the current architecture when the task is substantial;
3. identify the smallest coherent set of files to modify;
4. preserve current architectural boundaries unless the task explicitly requires changing them;
5. implement the requested behavior;
6. add or update tests for that behavior;
7. run relevant focused tests during implementation;
8. run the full deterministic test suite;
9. run Ruff checks;
10. run formatting checks;
11. update documentation if behavior, public contracts, or architecture materially changed;
12. summarize:
    - files changed;
    - behavior changed;
    - architectural impact;
    - tests added or updated;
    - validation results;
    - remaining risks or limitations.

A task is not complete if the relevant deterministic test suite or Ruff checks fail.

Do not perform broad refactors unless they are explicitly required by the task or a blocking architectural inconsistency makes the requested change unsafe.

If a broader refactor appears desirable but is not required, propose it separately rather than silently including it.

## Commits and Pull Requests

Recent history predominantly uses `feat: <description>`; follow concise, imperative messages with an appropriate prefix.

Keep commits focused.

Prefer feature branches for non-trivial changes.

PRs should explain:

- the problem;
- changed behavior;
- architectural impact when relevant;
- relevant issue;
- validation commands and results;
- known limitations.

Update documentation when capabilities, public contracts, or architecture change.

Do not merge unrelated cleanup into a feature PR unless explicitly requested.

## Configuration and Secrets

Supply `OPENAI_API_KEY` through the environment for LLM runs.

Never commit:

- credentials;
- `.env` files;
- virtual environments;
- caches;
- generated packaging artifacts;
- local machine-specific configuration.

Configuration that affects model choice, provider behavior, or public application behavior should be explicit and injectable where practical rather than hidden in constructors.
