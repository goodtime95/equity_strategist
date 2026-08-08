# Equity Strategist Architecture

## Design Philosophy

The project is built around one fundamental idea:

> The value of the application comes from financial reasoning, not from market data storage.

Market data providers are interchangeable.

Financial calculations are implemented once in Python.

The LLM will orchestrate deterministic services and interpret results, but it will never perform financial calculations itself.

---

## High-Level Architecture

```text
User
  |
  v
Equity Strategist (LLM, future)
  |
  v
Analysis Services
  |
  +-----------------------------+
  |                             |
  v                             v
Tools / Market Services       Compute
  |                             |
  v                             |
Asset Registry                  |
  |                             |
  v                             |
Data Provider                   |
  |                             |
  v                             |
DailyPriceObservation           |
  |                             |
  v                             |
Extractor                       |
  |                             |
  v                             |
MarketSeries -------------------+
  |
  v
MarketDataset
  |
  v
Structured Results
```

The architecture separates language understanding from deterministic financial logic.

---

## Core Financial Objects

### Asset

Represents the identity of a financial instrument.

It contains stable business information such as:

- symbol
- name
- exchange
- currency
- ISIN
- aliases

Asset identity is independent from any market-data provider.

### DailyPriceObservation

Represents all daily OHLCV information observed for one asset on one date.

It is the normalized output of the market-data provider.

### MarketSeries

Represents one financial variable evolving through time.

Examples:

- adjusted prices
- returns
- interest rates
- volatility
- spreads

`MarketSeries` is the central object of the quantitative engine.

### MarketDataset

Represents a coherent collection of `MarketSeries`.

It is the natural object used for multi-asset analysis, rankings and universe-level studies.

The abstraction levels are therefore:

```text
Asset
  -> one instrument

MarketSeries
  -> one variable through time

MarketDataset
  -> several coherent time series
```

---

## Layers

### Domain

The `domain/` package defines the financial vocabulary shared by the application.

Current concepts include:

- Asset
- DailyPriceObservation
- MarketSeries
- MarketDataset
- PriceOnDateResult
- DrawdownResult
- VolatilityComparisonResult

The Domain layer does not depend on Yahoo Finance, the LLM or the terminal interface.

### Asset Registry

The `asset_registry/` package owns asset identity and name resolution.

It maps user-facing references such as:

- LVMH
- Louis Vuitton
- MC.PA
- FR0000121014

to one internal `Asset`.

Yahoo Finance is not used as the authoritative source of instrument identity.

### Data Providers

The `data_providers/` package communicates with external data sources.

Current implementation:

- Yahoo Finance

Future implementations may include:

- Bloomberg
- Polygon
- Alpha Vantage
- Financial Modeling Prep

A provider retrieves data for an already identified asset and converts it into normalized domain observations.

It does not perform financial calculations.

### Extractors

The `extractors/` package converts rich observations into normalized time series.

Example:

```text
list[DailyPriceObservation]
        |
        | select adjusted close
        v
MarketSeries(kind=PRICE)
```

The same observations may later produce close, volume, high or low series.

### Compute

The `compute/` package contains pure quantitative functions.

Implemented calculations include:

- simple and logarithmic returns
- total, period and annualized performance
- cumulative performance
- historical volatility
- rolling volatility
- correlation
- rolling correlation
- drawdown
- maximum drawdown

Compute functions never download market data.

They operate only on normalized domain objects, mainly `MarketSeries`.

### Tools

The `tools/` package contains elementary reusable business operations.

Current examples:

- AssetResolver
- PriceTool

A tool performs one focused operation.

Examples:

- resolve a user query into an Asset
- return the relevant price for a requested date
- handle non-trading days

### Services

The `services/` package contains deterministic workflows.

A service coordinates several lower-level components without performing the financial formulas itself.

Current examples:

- MarketQueryService
- MarketSeriesService
- MarketDatasetService
- VolatilityAnalysisService

Example workflow:

```text
Compare volatility of LVMH, Hermès and ASML
        |
        v
MarketDatasetService
        |
        v
MarketDataset
        |
        v
compute_returns
        |
        v
compute_volatility
        |
        v
VolatilityComparisonResult
```

Services are the deterministic capabilities that the future Equity Strategist will call.

### Strategists

A future `strategists/` layer will contain LLM-driven reasoning.

The Equity Strategist will:

- understand natural-language questions
- infer intent and missing context
- select deterministic services
- combine several services when needed
- interpret structured results
- maintain conversational context

The LLM will not replace the deterministic engine.

### app.py

`app.py` is the composition root.

It creates and connects concrete implementations such as:

```text
Default AssetRegistry
        +
YahooFinanceProvider
        |
        v
MarketSeriesService
        |
        v
MarketDatasetService
        |
        v
Analysis Services
```

Changing the provider or registry should mainly affect this assembly layer.

---

## Directory Structure

```text
src/equity_strategist/
|
├── app.py
├── asset_registry/
├── compute/
├── data_providers/
├── domain/
├── extractors/
├── services/
└── tools/
```

Future:

```text
src/equity_strategist/
└── strategists/
```

Each directory has one main reason to change:

- `asset_registry/` -> asset reference data changes
- `data_providers/` -> an external API changes
- `domain/` -> the internal financial model changes
- `extractors/` -> observation-to-series transformation changes
- `compute/` -> a quantitative formula changes
- `tools/` -> an elementary business rule changes
- `services/` -> a deterministic business workflow changes
- `strategists/` -> LLM reasoning or orchestration changes
- `app.py` -> dependency wiring changes

This separation keeps the system modular, testable, provider-independent and ready for LLM orchestration.
