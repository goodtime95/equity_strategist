# Equity Strategist — Product and Engineering Roadmap

> Status: authoritative roadmap
> Last updated: 2026-09-28
> Baseline commit: 6a5a542f32840291da46b75365b9e24cf6ff6a2c
> Scope: Equity Strategist only

## 1. Mission and Scope

Equity Strategist is an autonomous, independently testable and deployable Equity
specialist. It transforms natural-language questions into deterministic analysis.
The LLM understands intent, participates in conversational orchestration and
interprets evidence; Python remains the sole authority for financial calculations.
Validation, planning and execution are currently deterministic.

The specialist must eventually compose with other specialists through a stable
public contract, without exposing its internal implementation. Fixed Income, News,
Market Synthesis and Structured Products remain outside the current scope.

## 2. Current Baseline

Status: COMPLETED

The audited baseline on `main` provides:

- FastAPI deployment on Railway, usable from an iPhone, with Bearer authentication;
- operational `/v1/chat` and `/v1/feedback` endpoints;
- LLM understanding and conversational refinement;
- validation before planning, followed by deterministic planning and execution;
- point-in-time prices;
- total, annualized and relative performance, including excess return;
- 1M, 3M, 6M, YTD, 1Y and 3Y horizons;
- historical volatility, correlation and maximum drawdown;
- performance and volatility rankings;
- benchmark support and multi-metric calculations;
- structured evidence and French and English responses;
- PostgreSQL storage for runs, telemetry and feedback;
- structured error handling;
- last known deterministic validation: 760 tests passed, 3 deselected;
- a 26-case live product battery.

These are baseline facts, not validation results from this documentation update.
The product is a robust conversational quantitative engine. It is not yet a fully
relevant Equity Strategist that spontaneously constructs rich analytical answers.

## 3. Architectural Principles

- Probabilistic intelligence at the top, deterministic financial computation at
  the bottom. The LLM must never perform authoritative financial calculations.
- Domain contracts remain independent of providers, LangGraph and the LLM.
- Providers retrieve data; the provider/extractor boundary normalizes it into
  internal representations without leaking provider-specific objects.
- Services orchestrate deterministic workflows and enforce business rules. Pure
  financial formulas belong in `compute`; services must not duplicate them.
  Financial logic must never be moved into prompts, planning or graph orchestration.
- LangGraph orchestrates execution and maintains conversation state. Runtime
  market datasets remain outside persisted graph state.
- Every accepted parameter must be executed, explicitly clarified or explicitly
  rejected. No parameter may be silently ignored.
- Public contracts must not expose internal LangGraph or provider objects.
- Do not introduce premature shared abstractions with future specialists.
- Deliver improvements in small vertical increments with explicit acceptance
  cases, deterministic evidence and tests.

## 4. Known Limitations

All limitations below describe the current baseline, not completed roadmap work.

**Correctness and comparability**

- Correlations currently construct each asset's returns independently before
  alignment. When calendars differ, paired returns can represent different
  intervals. Return-interval alignment needs a dedicated correction.
- Historical universe analysis uses a current local CAC 40 constituent snapshot,
  without historical compositions, creating survivorship-bias risk.
- Historical constituent weights and index-contribution methodology are absent.
  Constituent performance must not be presented as index contribution.
- Performance is expressed in local currencies, without common-currency FX
  conversion. Cross-currency comparisons need an explicit convention policy.

**Data and traceability**

- Yahoo Finance is the only price source.
- There is no persistent MarketStore or market-data cache. PostgreSQL product
  telemetry does not constitute a market-data store.
- Complete retrieval timestamps and a general provenance framework are absent.
- Local asset and universe coverage is limited; the CAC 40 snapshot is not a
  historical constituent database.

**Analytical relevance**

- The planner still uses a static objective-plus-metric mapping.
- `AnalysisRequest` mainly supplies parameters shared across all execution steps,
  limiting analyses that need distinct periods or parameters per metric.
- LLM interpretation is confined to facts in supplied evidence. This is also an
  intentional boundary: richer prose cannot substitute for missing analytics.

**Operations and documentation**

- LangGraph conversation state remains in memory.
- Deployment uses one worker/replica and serializes requests.
- GitHub CI and mandatory protection of `main` are currently absent.
- Documentation is partially outdated; this roadmap update does not synchronize
  the other documents.

## 5. Delivery Workflow

Every implementation increment follows this mandatory cycle:

1. Real user usage.
2. Traces and feedback collection.
3. Read-only diagnosis.
4. Human architecture/product review.
5. Dedicated branch.
6. Smallest coherent implementation.
7. Targeted regression tests.
8. Full deterministic test suite.
9. Ruff and diff checks.
10. Independent review against `main`.
11. Commit, push and pull request.
12. Deployment only when the running service is affected.
13. Replay of the original production cases when production behavior is affected.
14. Before/after benchmark comparison when analytical behavior or relevance is affected.

Do not fix a data problem with a prompt. Do not fix an understanding problem in
the quantitative engine. Diagnose the responsible layer before choosing a change.
This document records future work; saving it does not authorize implementation,
publication or deployment of any lot.

## 6. Roadmap

Statuses have a single meaning throughout: COMPLETED is available at the audited
baseline; CURRENT denotes workstreams already active; multiple lots may be CURRENT
only when they do not conflict. NEXT is the next eligible work; LATER is deferred
until evidence and prerequisites justify it; BLOCKED cannot start until its stated
gate is satisfied. Lot numbers structure progression and dependencies, but statuses
and gates determine actual eligibility. Independent lots must not be artificially
bundled.

### Lot 0 — Repository Governance and Documentation

Status: CURRENT

- Add GitHub Actions for pytest, Ruff lint, format and diff checks.
- Protect `main` and require pull requests.
- Synchronize `docs/current_state.md`, `docs/architecture_updated.md` and this
  roadmap with actual behavior.
- Remove contradictions across documentation.

Exit criteria:

- No unvalidated merge.
- Documentation agrees with the actual code.
- Automated checks are required before merge.

### Lot 1 — Product Evaluation Baseline

Status: CURRENT

- Collect 100–200 real Equity questions, including production questions from
  iPhone usage.
- Retain the question, structured request, validation, plan, evidence, answer,
  feedback, comment and version in a versioned evaluation benchmark.
- Respect existing persistence controls: metadata-only is the default; full
  content storage requires explicit `EQUITY_STRATEGIST_PERSIST_CONTENT=true`.
  Evaluation capture must not silently expand production telemetry storage.
- Classify outcomes separately as understanding failure, validation failure,
  planning failure, execution failure, data failure, interpretation failure,
  missing capability or out-of-scope request.
- Measure understanding, parameter fidelity, correctness, traceability and
  usefulness against stable acceptance cases.

Exit criteria:

- Approximately 90% of representative questions are correctly understood and then
  either correctly executed, clarified for a genuine ambiguity or refused for a
  genuine limitation. Measure successful executions, legitimate clarifications,
  legitimate refusals, false clarifications and false refusals separately. A refusal
  does not automatically count as a success.
- No silent omission of requested semantics.
- Evaluation cases are stable, versioned and replayable.

### Lot 2 — Quantitative Correctness and Data Foundations

Status: NEXT

Deliver the following as independent changes. Each sub-lot requires its own
acceptance cases, tests, independent review and pull request.

| Sub-lot | Change | Acceptance focus |
| --- | --- | --- |
| 2A | Return-interval alignment for correlations. | Paired returns cover identical intervals, including when market calendars differ. |
| 2B | Universe snapshot date, provenance, coverage and exclusions. | Structured results identify the snapshot and disclose included and excluded constituents. |
| 2C | Explicit policy for historical constituent limitations and survivorship bias. | Current snapshots never imply historical membership; limitations and unsupported uses are explicit. |
| 2D | Market-data retrieval metadata and provenance. | Evidence exposes retrieval metadata and data origin through deliberate structured fields. |
| 2E | Minimal MarketStore/cache for reproducibility, latency and provider resilience. | Demonstrated usage justifies the scope; reuse preserves financial semantics and supports reproducibility. |
| 2F | Explicit currency-convention policy before common-currency comparisons. | Local-currency results are distinguished from any future FX-converted analysis; incompatible conventions are never silently mixed. |

Do not bundle these into a broad data-layer refactor. Select the smallest coherent
change from diagnosed cases; keep already identified quantitative corrections
separate from capability expansion. No cache design or new provider is selected
by this roadmap.

### Lot 3 — Strategist Analytics

Status: LATER

Add analytics progressively, guided by real requests and acceptance cases:

- rolling volatility and rolling correlation;
- beta and tracking error;
- downside volatility;
- drawdown duration and recovery;
- return/volatility and Calmar ratios;
- moving averages and distance to moving averages;
- distance to highs and lows;
- momentum and deterministic trend classification;
- best and worst sessions and positive-session ratio;
- breadth;
- mean and median constituent performance;
- cross-sectional dispersion;
- strongest and weakest constituents;
- multi-horizon market diagnostics.

Do not introduce Sharpe or Sortino with an implicit risk-free rate or threshold.
Existing low-level calculations alone do not establish an end-to-end capability.
Each capability must traverse:

`domain → compute → service → capability → evidence → interpretation → tests → live battery`

Prefer parameters on reusable capabilities when the analytical operation is
unchanged. Extend the existing live battery as supported analytics grow.

Exit criteria for each increment: accepted semantics are validated and executed,
methodology and limitations are structured, deterministic tests pass and the live
battery covers the user case.

### Lot 4 — Equity Daily Snapshot

Status: LATER

Build a deterministic daily Equity state comprising:

- index levels and performance;
- top and bottom movers;
- breadth and dispersion;
- trend and volatility;
- anomalies;
- methodology, coverage and limitations.

The snapshot remains an autonomous Equity product. It must not directly
incorporate news or rates. Anomalies and diagnostics require explicit deterministic
definitions rather than invented market explanations.

Exit criteria: the snapshot is reproducible from structured Equity evidence,
discloses coverage and limitations, and passes its acceptance cases.

### Lot 5 — Planner and Public Contract V2

Status: LATER

Start only after several new capabilities reveal concrete requirements for:

- per-step parameters;
- different periods for different metrics;
- dependencies between steps;
- a capability registry;
- richer multi-step plans;
- explicitly justified complementary diagnostics;
- a stable public contract exposing status, resolved assets, calculations,
  effective dates, methodology, provenance, coverage, exclusions and limitations.

Avoid speculative refactoring before these use cases exist. Greater planning
expressiveness does not itself require an LLM planner.

Exit criteria: demonstrated multi-step requests retain all accepted semantics and
external callers can consume the structured contract without internal LangGraph,
provider or service knowledge.

### Lot 6 — Equity Strategist Maturity Gate

Status: LATER

Exit criteria:

- 100–200 representative questions evaluated.
- Approximately 90% of representative questions are correctly understood and then
  either correctly executed, clarified for a genuine ambiguity or refused for a
  genuine limitation. Measure successful executions, legitimate clarifications,
  legitimate refusals, false clarifications and false refusals separately. A refusal
  does not automatically count as a success; excessive refusals must not satisfy
  the maturity gate.
- Reproducible and auditable calculations.
- Requested parameters respected without silent omissions.
- Structured, recoverable failures.
- Most reasonable new questions handled without adding code.
- Successive improvements have become marginal, as shown by evaluation.
- Public contract sufficiently stable for an external orchestrator.

Passing this gate requires evidence against all criteria, not merely a larger
capability count.

### Lot 7 — Broader Specialist Architecture

Status: BLOCKED until Lot 6

Target order after the maturity gate:

1. Fixed Income Strategist.
2. Market News / Financial Journalist Agent.
3. Market State / Market Synthesizer.
4. Specialist orchestration.
5. Structured Products Idea Generator / Sales Assistant.

Do not add Fixed Income or News inside Equity Strategist. Each specialist must
remain autonomous, independently testable and independently deployable. Extract
shared abstractions only after at least two real implementations reveal a stable
common pattern. The Market Synthesizer composes global market state instead of
duplicating that state within every specialist.

Entry criterion: Lot 6 is satisfied. Detailed implementation and acceptance
criteria belong to later specialist-specific work, not the current Equity scope.

## 7. Prioritization Rules

- Correctness before coverage.
- Provenance before institutional claims.
- Real user evidence before capability expansion.
- Deterministic facts before richer prose.
- Smallest coherent change before refactoring.
- Specialist maturity before orchestration.
- No new capability without acceptance cases.
- No production incident fix without a regression test.

## 8. Definition of Done for Each Lot

Each implementation lot, and each independently delivered sub-lot, requires:

- a clearly stated user problem;
- explicit scope and exclusions;
- acceptance criteria;
- targeted tests;
- a passing full deterministic test suite;
- passing Ruff lint, format and diff checks;
- updated documentation;
- independent review against `main`;
- human validation;
- post-deployment verification when runtime or deployment behavior changes;
- before/after measurement when the change affects analytical relevance.

Advance status only when evidence supports the exit criteria. Future capabilities
must never be described as already implemented. This documentation-only save is
validated with Git diff and status checks; it does not execute any lot.

## 9. Explicit Non-Goals for the Current Phase

- News inside Equity Strategist.
- Rates or credit inside Equity Strategist.
- Structured-product recommendations.
- Market causality invented by the LLM.
- Unsupported forecasts.
- Premature multi-agent refactoring.
- A complex frontend.
- A vector database without a demonstrated use case.
- Replacing Python calculations with the LLM.
- Institutional claims based solely on Yahoo Finance.

## 10. Immediate Next Action

- Continue real-world testing from the iPhone.
- Build the Lot 1 benchmark.
- Select the first functional implementation lot only after analyzing errors and
  feedback.
- Address already identified quantitative corrections separately within Lot 2.
