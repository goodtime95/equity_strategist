# Architecture Decisions

## 2026-08-02 — New project

### Decision

Equity Strategist starts as a brand new project.

### Motivation

A clean architecture is easier to evolve than adapting Instit Watch.

---

## 2026-08-02 — Yahoo Finance for the MVP

### Decision

Yahoo Finance is used as the first market-data provider.

### Motivation

- free
- long historical coverage
- simple Python integration
- sufficient for the initial quantitative use cases

### Consequence

The architecture remains provider-independent so Yahoo Finance can later be replaced.

---

## 2026-08-02 — Data Providers package

### Decision

The external market-data layer is named `data_providers`.

### Motivation

The project may later contain other provider categories such as:

- LLM providers
- storage providers
- reporting providers

The explicit name avoids ambiguity.

---

## 2026-08-02 — Dependency injection

### Decision

Business components do not instantiate concrete providers themselves.

Concrete dependencies are assembled in `app.py`.

### Motivation

This keeps the business logic independent from Yahoo Finance and makes testing easier.

---

## 2026-08-02 — MarketSeries as the central time-series object

### Decision

Use a generic `MarketSeries` as the central time-series representation.

A `MarketSeries` may represent:

- prices
- returns
- rates
- volatility
- spreads
- volumes
- other market time series

The semantic nature of the series is identified by `SeriesKind`, unit and metadata.

### Motivation

Most financial calculations operate on time series with the same structural characteristics.

Creating separate classes such as PriceSeries, RateSeries and VolatilitySeries immediately would introduce unnecessary duplication.

### Consequences

- pandas remains the internal numerical representation;
- MarketSeries adds financial meaning and validation;
- Compute functions operate primarily on MarketSeries;
- specialized subclasses will only be added if genuinely different behaviours appear.

---

## 2026-08-02 — Separate observations from time series

### Decision

Use `DailyPriceObservation` for normalized daily OHLCV observations and keep `MarketSeries` as the quantitative time-series abstraction.

Use an extractor layer to move from observations to a selected time series.

### Motivation

A daily market observation and a financial time series represent different levels of abstraction.

A provider should expose what the data source provides, while the application decides which financial variable to analyse.

### Consequences

The data flow is:

```text
External provider
      |
      v
DailyPriceObservation
      |
      v
Extractor
      |
      v
MarketSeries
      |
      v
Compute
```

The former `series_builders` concept is replaced by `extractors`.

---

## 2026-08-03 — Internal Asset Registry

### Decision

Asset identity and name resolution are handled by an internal registry.

Yahoo Finance is used only to retrieve market data for an already identified asset.

### Motivation

Provider search results may contain several listings, ADRs, OTC instruments, certificates or secondary quotations.

For example, searching for LVMH through Yahoo did not reliably select the primary Paris listing.

### Consequences

The data flow becomes:

```text
User query
      |
      v
AssetResolver
      |
      v
AssetRegistry
      |
      v
Identified Asset
      |
      v
Data Provider
```

The MVP registry contains only the assets required by initial use cases and can later be replaced by a larger reference dataset.

---

## 2026-08-08 — MarketDataset as the multi-asset abstraction

### Decision

Introduce `MarketDataset` as a coherent collection of `MarketSeries`.

### Motivation

Analysts frequently work on groups of assets, investment universes and rankings rather than on one isolated series.

Without a dataset abstraction, every analysis service would repeat the same multi-asset loading logic.

### Consequences

The abstraction levels are:

```text
Asset
  -> one instrument

MarketSeries
  -> one variable through time

MarketDataset
  -> several coherent time series
```

`MarketDatasetService` centralizes the construction of multi-asset datasets.

Future performance, correlation, drawdown and ranking services can reuse the same object.

---

## 2026-08-08 — Separate deterministic services from LLM reasoning

### Decision

Keep all existing services deterministic and introduce the future LLM reasoning layer above them.

### Motivation

Financial calculations and business workflows must remain:

- reproducible;
- testable;
- independent from a specific LLM;
- usable through interfaces other than chat.

### Consequences

Future architecture:

```text
Equity Strategist (LLM)
        |
        v
Deterministic Services
        |
        v
Tools / Compute / Data
```

The LLM understands, plans, routes and interprets.

Python services and compute functions execute the financial logic.

---

## 2026-08-08 — Validate the agent before broadening the engine

### Decision

After the first multi-asset volatility workflow, development shifts toward a minimal conversational Equity Strategist rather than immediately implementing every possible analysis service.

### Motivation

Real natural-language usage should reveal which missing capabilities are actually valuable.

### Consequence

Rankings, market calendars, additional frequencies, Market Store and other enhancements remain intentionally deferred until agent testing demonstrates their priority.
