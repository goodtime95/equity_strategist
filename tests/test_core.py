from equity_strategist.core import project_status


def test_project_status() -> None:
    assert project_status() == "Equity Strategist is ready"
