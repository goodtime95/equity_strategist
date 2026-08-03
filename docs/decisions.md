# Architecture Decisions

## 2026-08-02

### New project

Equity Strategist starts as a brand new project.

Reason:

A clean architecture is easier to evolve than adapting Instit Watch.

---

### Market data provider

Yahoo Finance is used for the MVP.

Reason:

- free
- long history
- simple API

The architecture must remain provider independent.

---

### Data Providers

The package is named data_providers.

Reason:

The project will probably include other provider types in the future:

- LLM providers
- Storage providers
- Report providers

---

### Dependency Injection

Tools never instantiate providers.

Providers are assembled inside app.py.

All tools depend only on MarketDataProvider.

## 2026-08-02

### PriceSeries as the central quantitative object

Decision

Introduce a `PriceSeries` domain object before implementing quantitative metrics.

Motivation

Most financial computations operate on a time series rather than directly on a market data provider.

By introducing a dedicated `PriceSeries`, all Compute Tools will share the same input representation.

Consequences

- Data Providers retrieve raw market data.
- PriceSeries represents normalized historical prices.
- Compute Tools operate only on PriceSeries.
- Business services orchestrate these building blocks.

---

## 2026-08-02 — MarketSeries as the central time-series object

### Decision

Introduce a generic `MarketSeries` domain object as the central time-series representation of the Financial Reasoning Framework.

A `MarketSeries` may represent:

- prices;
- returns;
- rates;
- volatility;
- spreads;
- volumes;
- other market time series.

The semantic nature of the data is identified through a `SeriesKind` value and business metadata.

### Motivation

Most quantitative computations operate on time series with the same structural characteristics:

- dated observations;
- numerical values;
- units;
- identifiers;
- metadata;
- data-quality requirements.

Creating separate classes such as `PriceSeries`, `RateSeries`, and `VolatilitySeries` immediately would introduce duplication before distinct behaviours are known.

### Consequences

- Data Providers retrieve and normalize raw external data.
- Series builders convert domain observations into `MarketSeries`.
- Compute Tools operate primarily on `MarketSeries`.
- Specialized subclasses will only be introduced if materially different behaviours emerge.
- Pandas remains the internal numerical representation, while `MarketSeries` adds financial meaning and validation.

---

## 2026-08-03 — Internal Asset Registry

### Decision

Asset identity and name resolution are handled by an internal registry.

Yahoo Finance is used only to retrieve market data for an already identified asset.

### Motivation

Provider search results may contain several listings, ADRs, OTC instruments, certificates or secondary quotations.

For example, searching for LVMH through Yahoo may return several instruments and does not reliably guarantee selection of the primary Paris listing.

The application therefore needs its own stable representation of asset identity.

### Consequences

The data flow becomes:

User query
→ AssetResolver
→ AssetRegistry
→ identified Asset
→ Data Provider
→ market observations

The MVP registry contains only the main equities and indices required by the initial use cases.

The registry can later be replaced by a larger reference dataset without modifying the market-data providers or quantitative engine.
