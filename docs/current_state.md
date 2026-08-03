# Current State

Last update: 2026-08-02

---

# Current Milestone

The project now has its first complete vertical slice.

```text
Company name
      │
      ▼
AssetResolver
      │
      ▼
PriceTool
      │
      ▼
Yahoo Finance
      │
      ▼
Structured Result
```

---

# Implemented

## Project

- Project structure
- Git repository
- Testing infrastructure
- Documentation

## Domain

- Asset
- PriceBar
- PriceOnDateResult

## Data Providers

- MarketDataProvider protocol
- YahooFinanceProvider

## Data Tools

- AssetResolver
- PriceTool

## Services

- MarketQueryService

---

# Working Features

The application can currently:

- search for an equity;
- retrieve historical daily prices;
- convert Yahoo Finance data into domain objects;
- retrieve the latest available market price for a requested date;
- correctly handle weekends.
- generic MarketSeries representation;
- conversion of PriceBar observations into a price series;
- simple and logarithmic return computation.
- total performance;
- period performance;
- annualized performance;
- cumulative performance series.
- annualized historical volatility;
- rolling historical volatility;
- explicit annualization factor;
- volatility computed from return series.
- correlation between aligned return series;
- rolling correlation;
- automatic alignment on common dates;
- rejection of insufficient overlapping observations.
- drawdown time series;
- maximum drawdown;
- peak and trough dates;
- recovery date when available.
- internal asset registry;
- resolution by ticker, name, alias and ISIN;
- provider-independent asset identity;
- Yahoo Finance used only for market-data retrieval.

---

# Next Milestone

Implement drawdown metrics:

1. drawdown series;
2. maximum drawdown;
3. peak date;
4. trough date;
5. recovery date when available.

---

# Long-Term Target

Current architecture:

```text
Yahoo Finance
      │
      ▼
Price Tool
      │
      ▼
Service
```

Target architecture:

```text
LLM
      │
      ▼
Services
      │
      ▼
Data Tools
      │
      ▼
Compute Tools
      │
      ▼
Market Store
      │
      ▼
Data Providers
```

The Compute Tools layer will progressively become the core of the Financial Reasoning Framework.