# Current State

Last update: 2026-08-08

---

## Current Milestone

The deterministic financial engine now supports its first complete multi-asset analysis workflow.

```text
User asset queries
      |
      v
AssetResolver / AssetRegistry
      |
      v
MarketSeriesService
      |
      v
MarketDatasetService
      |
      v
MarketDataset
      |
      v
VolatilityAnalysisService
      |
      v
Structured comparison result
```

The first real multi-asset test successfully compared historical volatility for LVMH, Hermès and ASML.

---

## Implemented

### Project

- Project structure
- Git repository
- Testing infrastructure
- Ruff
- Pytest
- Project documentation

### Domain

- Asset
- DailyPriceObservation
- MarketSeries
- MarketDataset
- PriceOnDateResult
- DrawdownResult
- VolatilityComparisonResult

### Asset Identity

- Internal AssetRegistry
- Asset resolution by ticker
- Asset resolution by name
- Asset resolution by alias
- Asset resolution by ISIN
- Provider-independent asset identity

### Data Providers

- MarketDataProvider protocol
- YahooFinanceProvider
- Historical daily price retrieval

Yahoo Finance is used for market-data retrieval only, not as the authoritative source of instrument identity.

### Extractors

- DailyPriceObservation -> price MarketSeries
- adjusted-close extraction
- close extraction

### Compute Engine

Implemented:

- simple returns
- logarithmic returns
- total performance
- period performance
- annualized performance
- cumulative performance series
- annualized historical volatility
- rolling volatility
- correlation
- rolling correlation
- common-date alignment
- drawdown series
- maximum drawdown
- peak date
- trough date
- recovery date

Not yet implemented:

- rankings

### Tools

- AssetResolver
- PriceTool
- handling of non-trading days for point-in-time price queries

### Services

- MarketQueryService
- MarketSeriesService
- MarketDatasetService
- VolatilityAnalysisService

### Multi-Asset Analysis

The application can build a coherent `MarketDataset` from several asset queries and apply quantitative analysis across that dataset.

Validated real-world example:

```text
LVMH
Hermès
ASML
  |
  v
MarketDataset
  |
  v
log returns
  |
  v
annualized historical volatility
  |
  v
ranked comparison
```

---

## Current Architecture Levels

```text
Asset
= identity of one financial instrument

MarketSeries
= one financial variable through time

MarketDataset
= a coherent collection of MarketSeries

Analysis Service
= deterministic multi-step financial workflow

Equity Strategist
= future LLM reasoning and orchestration layer
```

---

## Next Milestone

Build the first minimal Equity Strategist and terminal conversation loop.

Initial objective:

1. accept a natural-language question;
2. identify a supported intent;
3. route the request to an existing deterministic service;
4. return a clear natural-language answer;
5. begin testing the usefulness of the agent with real questions.

The goal is now to validate the product vertically before expanding the quantitative engine further.

---

## Known Future Improvements

These are intentionally deferred until real agent usage demonstrates the need:

- rankings
- market periods such as Covid and GFC
- investment-universe registry
- sector and industry metadata
- market calendar
- local Market Store / cache
- additional frequencies and resampling
- broader asset registry
- additional analysis services
- conversation state

---

## Long-Term Target

```text
User
  |
  v
Equity Strategist
  |
  v
Deterministic Services
  |
  +----------------------+
  |                      |
  v                      v
Market Data Engine     Compute Engine
  |                      |
  +----------+-----------+
             |
             v
     Structured Results
             |
             v
     LLM Interpretation
```

The current priority is to connect the existing deterministic engine to a minimal conversational agent and learn from real usage.
