# Development Guide

## Philosophy

The project is developed vertically.

Each feature must be completed before starting the next one.

Development cycle:

1. Design
2. Implement
3. Test
4. Ruff
5. Pytest
6. Commit
7. Update documentation

## Principles

- The LLM never performs financial calculations.
- Python performs every financial calculation.
- Data Providers only retrieve data.
- Tools contain business logic.
- Services orchestrate tools.
- Every feature must be tested.

## Source of Truth

The code is the source of truth.

Documentation explains architecture and decisions.

Git records the project's history.
