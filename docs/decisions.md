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
