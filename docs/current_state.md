# Current State

Last update: 2026-08-23

---

## Current Milestone

The Equity Strategist now supports a complete conversational quantitative workflow.

A natural-language equity question can be:

1. interpreted by an LLM into a strict structured request;
2. validated before execution;
3. translated into a deterministic analysis plan;
4. executed through Python financial services;
5. returned as a readable quantitative answer.

Validated end-to-end example:

```text
"Compare LVMH, Hermès and ASML in performance and volatility
over the last two years."
        |
        v
LLMUnderstanding
        |
        v
AnalysisRequest
        |
        v
AnalysisRequestValidator
        |
        v
EquityPlanner
        |
        +----------------------+
        |                      |
        v                      v
COMPARE_PERFORMANCE     COMPARE_VOLATILITY
        |                      |
        +----------+-----------+
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
          Structured results
                   |
                   v
             Interpretation



The LLM determines what the user wants.

Python determines how the financial analysis is calculated.

Core Design Principle
Probabilistic intelligence at the top.
Deterministic financial computation at the bottom.

The LLM is currently used only for natural-language understanding.

It does not:

calculate returns;
calculate volatility;
calculate drawdowns;
calculate correlations;
rank assets numerically;
retrieve market data.

Those responsibilities remain inside deterministic Python components.

Implemented
Project
Python 3.12
package structure under src/
Git repository
Ruff
Pytest
editable package installation
GitHub source control
generated packaging artifacts ignored by Git
Domain

Implemented domain objects include:

Asset
DailyPriceObservation
MarketSeries
MarketDataset
PriceOnDateResult
AnalysisRequest
AnalysisPlan
PlanStep
Capability
AnalysisExecutionResult
StepExecutionResult
PerformanceComparisonResult
VolatilityComparisonResult
CorrelationAnalysisResult
DrawdownComparisonResult
RankingResult
Universe
RequestValidationResult

AnalysisRequest represents what the understanding layer extracted.

It may intentionally be incomplete.

Execution readiness is determined later by AnalysisRequestValidator.

Understanding Layer

Two understanding implementations currently exist.

RuleBasedUnderstanding

Deterministic understanding used as a stable reference pipeline.

LLMUnderstanding

Uses an OpenAI model with structured outputs to convert natural-language questions into AnalysisRequest.

The structured output currently extracts:

objective;
metrics;
assets;
universe;
start date;
end date;
target date;
benchmark;
constraints;
unresolved information.

Current objective types:

get
compare
rank
analyze

Current metrics:

price
performance
volatility
correlation
drawdown

The understanding layer follows the principle:

LLM decides WHAT.
Quantitative engine decides HOW.

Implementation details such as return methodology, annualization, standard historical correlation methodology and non-trading-day handling are not treated as user clarifications.

Request Validation

AnalysisRequestValidator sits between Understanding and Planning.

It currently classifies a request as:

READY
NEEDS_CLARIFICATION
UNSUPPORTED
READY

The request contains enough information and the current engine supports it.

NEEDS_CLARIFICATION

The user intent is incomplete or ambiguous.

Examples:

missing assets;
missing universe;
missing metric;
missing analysis period;
ambiguous concept such as risk.
UNSUPPORTED

The request is understood and complete, but the current quantitative engine does not yet support the requested objective/metric combination.

Example:

RANK + DRAWDOWN

The Validator prevents unsupported or incomplete requests from reaching the Planner and Executor.

Planning

EquityPlanner is currently deterministic.

It maps structured (objective, metric) combinations into capabilities.

Current capability mapping includes:

GET + PRICE -> PRICE_ON_DATE
COMPARE + PERFORMANCE -> COMPARE_PERFORMANCE
COMPARE + VOLATILITY -> COMPARE_VOLATILITY
COMPARE + DRAWDOWN -> COMPARE_DRAWDOWN
ANALYZE + CORRELATION -> ANALYZE_CORRELATION
RANK + PERFORMANCE -> RANK_PERFORMANCE
RANK + VOLATILITY -> RANK_VOLATILITY

The planner supports multi-step requests.

Example:

COMPARE

metrics:
- PERFORMANCE
- VOLATILITY
- DRAWDOWN

produces three deterministic plan steps.

The planner may become hybrid or LLM-assisted later, but deterministic planning is intentionally kept for the current stage.

Execution

EquityExecutor executes each PlanStep deterministically.

The Executor currently routes capabilities to:

MarketQueryService
PerformanceAnalysisService
VolatilityAnalysisService
CorrelationAnalysisService
DrawdownAnalysisService
RankingAnalysisService

Execution results remain structured domain objects before interpretation.

Market Data Architecture

Yahoo Finance is currently used as the market-data provider.

It is not treated as the authoritative security master.

The current shared dependency graph is:

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

The same provider and resolver instances are also reused by:

PriceTool
MarketQueryService
UniverseAssetResolver

This prepares the architecture for a future cache / MarketStore without introducing one prematurely.

Asset Identity

Current asset identity flow:

user asset reference
        |
        v
AssetResolver
        |
        v
AssetRegistry
        |
        v
Asset

The registry currently supports resolution by:

ticker;
company name;
alias;
ISIN.

Known registered examples include:

LVMH
Hermès
ASML
Nvidia
CAC 40
Euro Stoxx 50
S&P 500

Asset coverage is intentionally limited at this stage.

A fallback asset-resolution mechanism is the next major planned improvement.

MarketSeries

MarketSeries is the generic normalized time-series representation.

Supported series kinds include:

PRICE
RETURN
RATE
VOLATILITY
CORRELATION
DRAWDOWN
SPREAD
VOLUME

It validates:

DatetimeIndex;
sorted dates;
no duplicated dates;
numeric values;
no missing values.
MarketDataset

MarketDataset represents a coherent collection of MarketSeries.

It is used by analysis services to apply deterministic financial calculations across several assets.

Datasets can currently be built from:

asset queries;
already resolved Asset objects.

The resolved-asset path is used notably by universe-based workflows.

Compute Engine

Implemented deterministic calculations include:

Returns
simple returns;
logarithmic returns.
Performance
total performance;
period performance;
annualized performance;
cumulative performance series.
Volatility
annualized historical volatility;
rolling volatility.
Correlation
correlation;
rolling correlation;
common-date alignment.
Drawdown
drawdown series;
maximum drawdown;
peak date;
trough date;
recovery date.

All calculations are performed in Python.

Analysis Services

Implemented services:

MarketQueryService
MarketSeriesService
MarketDatasetService
PerformanceAnalysisService
VolatilityAnalysisService
CorrelationAnalysisService
DrawdownAnalysisService
RankingAnalysisService
UniverseConstituentService

The distinction is:

compute
= pure mathematical functions

tool
= focused technical capability

service
= deterministic financial workflow

strategist
= orchestration and reasoning
Current Supported Analyses
Price

Point-in-time price queries.

Example:

"What was LVMH's price on March 15, 2020?"

Non-trading dates may use the previous available trading session.

Performance Comparison

Compare historical performance across several assets.

Volatility Comparison

Compare annualized historical volatility across several assets.

Correlation Analysis

Analyze historical pairwise correlations.

Drawdown Comparison

Compare maximum historical drawdowns.

Performance Ranking

Rank assets by historical performance.

Volatility Ranking

Rank assets by historical volatility.

Multi-Metric Analysis

A single user question can generate several plan steps.

Validated example:

performance + volatility

for:

LVMH
Hermès
ASML
Universes

The project now contains explicit universe abstractions.

Current universe types:

STATIC
DYNAMIC

Examples:

Luxury Europe

Static universe including:

LVMH
Hermès
CAC 40

Dynamic universe with Euronext as the configured constituent provider.

Universe resolution is separated from asset resolution.

Current universe-based execution support is intentionally limited to selected capabilities.

Performance ranking over a universe is currently supported.

Builders

Two Equity Strategist pipelines are currently available.

Deterministic Reference Pipeline
build_equity_strategist()

Uses:

RuleBasedUnderstanding
LLM-Powered Pipeline
build_llm_equity_strategist()

Uses:

LLMUnderstanding

Both pipelines share the same:

Validator;
Planner;
Executor;
market-data layer;
deterministic financial services;
compute engine.
Validated End-to-End LLM Workflow

The following question has been successfully executed end-to-end:

Entre LVMH, Hermès et ASML, compare leur performance
et leur volatilité sur les deux dernières années.

The system produced:

Understanding:
COMPARE
PERFORMANCE + VOLATILITY
LVMH / Hermès / ASML
2024-08-15 -> 2026-08-15

Validation:
READY

Plan:
COMPARE_PERFORMANCE
COMPARE_VOLATILITY

The deterministic engine then retrieved market data and calculated the performance and historical volatility results.

This validates the full path:

Natural language
    |
    v
LLM
    |
    v
Structured financial intent
    |
    v
Deterministic validation
    |
    v
Deterministic planning
    |
    v
Market data
    |
    v
Python financial calculations
    |
    v
Readable answer
Known Limitations
Asset Coverage

Direct asset queries currently depend primarily on the local AssetRegistry.

A user may correctly ask for a company that the LLM understands but the registry does not yet know.

A fallback resolution mechanism is planned.

Repeated Market-Data Retrieval

Although analysis services now share the same provider and MarketDatasetService, separate metrics may still independently request the same historical data.

Example:

performance + volatility + drawdown

may still cause repeated retrieval of the same price history.

A future cache / MarketStore should solve this naturally.

Universe Coverage

Only selected capabilities currently support universe-based execution.

Ranking Semantics

Ranking direction and top_n are not yet represented as dedicated structured fields.

Some ranking intent is currently stored in free-text constraints.

Conversation State

The agent does not yet maintain conversational context across questions.

Final LLM Interpretation

The final answer is currently deterministic formatting.

The LLM is not yet used to interpret or synthesize quantitative results.

Planner

The planner is deterministic.

A hybrid or LLM-assisted planner may be introduced later when the capability set becomes sufficiently broad to justify it.

Current Architecture
USER
 |
 v
UnderstandingProvider
 |
 +--------------------------+
 |                          |
 v                          v
RuleBasedUnderstanding   LLMUnderstanding
 |                          |
 +------------+-------------+
              |
              v
       AnalysisRequest
              |
              v
 AnalysisRequestValidator
              |
    +---------+----------+
    |         |          |
    v         v          v
 READY   CLARIFY    UNSUPPORTED
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
    +--------------------------------------+
    |             |            |           |
    v             v            v           v
Performance   Volatility   Correlation   Drawdown
    |             |            |           |
    +-------------+------------+-----------+
                  |
                  v
          MarketDatasetService
                  |
                  v
          MarketSeriesService
                  |
                  v
        YahooFinanceProvider
                  |
                  v
          Structured Results
                  |
                  v
        Deterministic Interpreter
                  |
                  v
                 USER
Next Milestone

Improve asset resolution without building a proprietary security master.

Target flow:

natural-language asset reference
        |
        v
AssetRegistry
        |
      found?
     /      \
   yes       no
   |         |
   v         v
 Asset    provider / external lookup
             |
         unique match?
          /       \
        yes        no
        |           |
        v           v
      Asset     clarification

The objective is broader real-world equity coverage while keeping the architecture lightweight.

Longer-Term Direction

The Equity Strategist is intended to become the first specialization of a broader Financial Reasoning Framework.

Potential future modules:

Fixed Income
FX
Credit
Cross Asset
Structured Products

The long-term pattern remains:

Natural language
        |
        v
Financial reasoning
        |
        v
Structured analytical plan
        |
        v
Deterministic financial tools
        |
        v
Structured quantitative evidence
        |
        v
LLM synthesis

The immediate priority remains to test the Equity Strategist against real analyst questions and expand capabilities only where usage demonstrates value.