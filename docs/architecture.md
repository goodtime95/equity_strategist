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