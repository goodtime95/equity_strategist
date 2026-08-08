# Roadmap

## Phase 1 — Foundations

- [x] Project setup
- [x] Git
- [x] Tests
- [x] Domain model
- [x] Dependency injection
- [x] Documentation structure

---

## Phase 2 — Market Data Layer

- [x] MarketDataProvider protocol
- [x] YahooFinanceProvider
- [x] DailyPriceObservation
- [x] Internal Asset Registry
- [x] AssetResolver
- [x] PriceTool
- [x] Price-series extraction
- [x] MarketSeriesService
- [ ] Market Store / local cache
- [ ] Automatic refresh
- [ ] Historical persistence
- [ ] Additional frequencies / resampling when required

---

## Phase 3 — Quantitative Engine

- [x] MarketSeries
- [x] Simple and logarithmic returns
- [x] Performance metrics
- [x] Historical volatility
- [x] Rolling volatility
- [x] Correlation
- [x] Rolling correlation
- [x] Drawdown
- [x] Maximum drawdown
- [ ] Rankings

---

## Phase 4 — Multi-Asset Analysis

- [x] MarketDataset
- [x] MarketDatasetService
- [x] First multi-asset analysis service
- [x] Volatility comparison
- [ ] Performance analysis service
- [ ] Correlation analysis service
- [ ] Drawdown analysis service
- [ ] Rankings / top-bottom analysis

These services should only be expanded as real agent use cases require them.

---

## Phase 5 — Equity Strategist MVP

- [ ] Minimal LLM integration
- [ ] Natural-language intent detection
- [ ] Service routing
- [ ] Structured tool/service outputs
- [ ] Natural-language answer generation
- [ ] Terminal conversation loop
- [ ] Initial conversation state
- [ ] Test with real analyst questions

---

## Phase 6 — Equity Knowledge

- [ ] Market-period registry
  - Covid
  - Global Financial Crisis
  - Lehman
  - European sovereign crisis
  - inflation shock
- [ ] Universe registry
  - CAC 40
  - Euro Stoxx 50
  - Stoxx Europe 600
  - Nasdaq 100
  - S&P 500
- [ ] Sector / industry metadata
- [ ] Benchmark handling
- [ ] Market calendar

---

## Phase 7 — Financial Reasoning Framework

- [ ] Fixed Income Strategist
- [ ] FX Strategist
- [ ] Credit Strategist
- [ ] Cross Asset Strategist

---

## Phase 8 — Structured Products Sales Assistant

- [ ] Transform market analysis into underlying ideas
- [ ] Connect investment views to payoff families
- [ ] Build structured-product recommendation workflows
