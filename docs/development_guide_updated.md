# Development Guide

## Philosophy

The project is developed vertically.

The objective is to maintain a working system while progressively adding financial capabilities.

A feature should normally move through the full stack required to make it testable before starting unnecessary adjacent infrastructure.

---

## Development Cycle

1. Design the smallest useful capability.
2. Implement the relevant domain or deterministic logic.
3. Add unit tests.
4. Run Ruff.
5. Run Pytest.
6. Run a real integration script when external data is involved.
7. Update documentation when architecture or project state changes.
8. Commit a coherent milestone.

---

## Core Principles

- The LLM never performs financial calculations.
- Python performs every financial calculation.
- The code is the source of truth.
- Domain objects define the shared financial vocabulary.
- Asset identity is independent from the market-data provider.
- Data Providers retrieve and normalize external data.
- Extractors transform observations into MarketSeries.
- Compute functions contain pure quantitative logic.
- Tools implement elementary reusable business operations.
- Services orchestrate deterministic workflows.
- Future Strategists perform LLM-driven reasoning above deterministic services.
- Every important deterministic capability must be testable without an LLM.
- External provider integration should be tested separately from unit tests.

---

## Preferred Development Direction

Prefer vertical validation over premature breadth.

Example:

```text
Natural-language question
        |
        v
one supported intent
        |
        v
existing deterministic service
        |
        v
structured result
        |
        v
natural-language answer
```

Then observe what is missing before adding more infrastructure.

This avoids building rankings, calendars, caching, additional frequencies or broader universes before real agent usage demonstrates that they are needed.

---

## Testing Strategy

### Unit Tests

Use fake or deterministic inputs for:

- Domain validation
- Compute functions
- Tools
- Services

Unit tests must not rely on Yahoo Finance.

### Integration Scripts

Use scripts under `scripts/` to validate real external workflows.

Examples:

- Yahoo historical retrieval
- MarketSeries construction
- MarketDataset construction
- multi-asset volatility comparison

Provider failures should not invalidate deterministic unit tests.

---

## Dependency Direction

Lower layers should not depend on higher layers.

Conceptually:

```text
Domain
  ^
  |
Data / Extractors / Compute
  ^
  |
Tools / Services
  ^
  |
Strategist
```

The LLM layer may depend on deterministic services.

The deterministic engine must never depend on the LLM.

---

## Source of Truth

- Code describes actual behaviour.
- Tests describe expected behaviour.
- `architecture.md` explains the structure and responsibilities.
- `decisions.md` records important architectural decisions and why they were made.
- `current_state.md` records what is currently implemented and what comes next.
- `roadmap.md` tracks future milestones.
- Git records the project history.
