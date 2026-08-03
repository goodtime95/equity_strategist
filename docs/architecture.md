# Equity Strategist Architecture

## Design Philosophy

The project is built around one fundamental idea:

> The value of the application comes from financial reasoning, not from market data storage.

Market data providers are interchangeable.

Financial calculations are implemented once in Python.

The LLM orchestrates tools but never performs financial calculations.

---

# High-Level Architecture

```text
                 User
                   │
                   ▼
          Equity Strategist Agent
                   │
                   ▼
          Conversation Layer
                   │
                   ▼
              Service Layer
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
     Data Tools         Compute Tools
         │                   │
         └─────────┬─────────┘
                   ▼
          MarketDataProvider
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
YahooFinanceProvider   BloombergProvider
        │
        ▼
External Market Data
```

---

# Layers

## Domain

Contains the business objects used throughout the application.

Examples:

- Asset
- PriceBar
- PriceOnDateResult

The Domain layer never depends on any external provider.

---

## Data Providers

Responsible only for retrieving market data.

Examples:

- Yahoo Finance
- Bloomberg
- Alpha Vantage
- Polygon

They convert external data into internal domain objects.

They never contain business logic.

---

## Data Tools

Answer business questions that require market data.

Examples:

- AssetResolver
- PriceTool

They only depend on the `MarketDataProvider` protocol.

---

## Compute Tools

Perform reusable quantitative calculations.

Examples:

- Returns
- Performance
- Volatility
- Correlation
- Drawdown
- Beta

They never download market data.

---

## Services

Coordinate several tools to implement a business use case.

Examples:

- Price of LVMH on a given date
- Compare volatility between two stocks

---

## LLM

The LLM:

- understands the user's request;
- plans the execution;
- selects the appropriate tools;
- interprets the results.

The LLM never performs financial calculations.

---

# Dependency Injection

Concrete implementations are instantiated only once during application startup.

Example:

```text
YahooFinanceProvider
        │
        ▼
PriceTool
        │
        ▼
MarketQueryService
```

Business logic never depends directly on Yahoo Finance.

# Recap 

---

# Current Application Flow

The application follows a layered architecture where each layer has a single responsibility.

```
User Request
      │
      ▼
Service
      │
      ▼
Asset Resolver
      │
      ▼
Asset Registry
      │
      ▼
Asset
      │
      ▼
Market Data Provider
      │
      ▼
DailyPriceObservation
      │
      ▼
Extractor
      │
      ▼
MarketSeries
      │
      ▼
Compute
      │
      ▼
Structured Result
```

## Architecture Overview

### Asset Registry

The Asset Registry owns the identity of financial instruments.

It maps names, aliases, ISINs and tickers to a unique `Asset` object.

It is independent from external data providers.

Examples:

- LVMH
- Louis Vuitton
- FR0000121014
- MC.PA

all resolve to the same Asset.

---

### Data Providers

A data provider retrieves raw market data for an already identified asset.

Its only responsibility is communicating with an external API.

Current implementation:

- Yahoo Finance

Future implementations may include:

- Bloomberg
- Polygon
- Alpha Vantage
- Financial Modeling Prep

Changing the provider should not affect the rest of the application.

---

### Domain

The Domain package contains the financial language shared by the application.

Typical objects are:

- Asset
- DailyPriceObservation
- MarketSeries
- result objects

These classes do not depend on Yahoo, pandas, the LLM or the terminal.

---

### Extractors

Extractors transform market observations into normalized financial time series.

Example:

DailyPriceObservation

↓

Adjusted Close

↓

MarketSeries(kind=PRICE)

The same observations may later produce:

- close series
- adjusted close series
- volume series
- high series
- low series

---

### Compute

Compute contains pure quantitative functions.

Inputs:

- MarketSeries

Outputs:

- returns
- performance
- volatility
- correlation
- drawdown

Compute never downloads market data.

---

### Tools

Tools implement elementary business operations.

Examples:

- resolve an asset
- retrieve a price on a requested date
- manage non-trading days

A tool performs one operation only.

---

### Services

Services orchestrate several components to answer a complete business request.

Example:

Compare the volatility of LVMH and Hermès.

The service:

1. resolves both assets
2. downloads observations
3. extracts price series
4. computes returns
5. computes volatility
6. assembles the final result

---

### app.py

`app.py` is the composition root.

It creates and connects concrete implementations.

Example:

```
Asset Registry
        +
Yahoo Finance Provider
        │
        ▼
Services
```

Only this layer knows which provider is used.

---

# Directory Structure

```
src/equity_strategist/
│
├── app.py
│
├── asset_registry/
│      Asset identity
│
├── data_providers/
│      External APIs
│
├── domain/
│      Financial objects
│
├── extractors/
│      Observation → MarketSeries
│
├── compute/
│      Quantitative calculations
│
├── tools/
│      Elementary business operations
│
└── services/
       Business use cases
```

## Design Principle

Each directory has one reason to change.

- asset_registry → financial reference data changes
- data_providers → external API changes
- domain → financial model changes
- extractors → data transformation changes
- compute → quantitative formulas change
- tools → elementary business rules change
- services → business workflows change
- app.py → dependency wiring changes

This separation keeps the system modular, testable and provider-independent.