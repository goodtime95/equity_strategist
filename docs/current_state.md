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

---

# Next Milestone

Implement volatility metrics:

1. historical volatility;
2. configurable annualization factor;
3. volatility computed from simple or logarithmic returns;
4. rolling volatility.

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