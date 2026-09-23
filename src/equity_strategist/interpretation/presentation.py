"""Deterministic display rules; raw evidence is never rounded or replaced."""

from decimal import MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, Context, Decimal, localcontext


def display_value(value: float | Decimal | str, metric: str) -> str:
    # A fresh context isolates precision, rounding, exponent limits and traps.
    with localcontext(
        Context(rounding=ROUND_HALF_EVEN, Emin=MIN_EMIN, Emax=MAX_EMAX)
    ) as context:
        number = Decimal(str(value))
        context.prec = max(28, len(number.as_tuple().digits) + 4)
        if metric == "correlation":
            return f"{number:.3f}"
        if metric == "price":
            return _display_price(number)
        if metric == "excess_return":
            return f"{number * 100:.2f} pp"
        return f"{number * 100:.2f}%"


def _display_price(number: Decimal) -> str:
    """Two decimals ordinarily; four significant digits below 1, at most 8 dp."""
    if number.is_zero() or number.copy_abs() >= 1:
        return f"{number:.2f}"
    decimals = max(2, 3 - number.adjusted())
    if decimals <= 8:
        return f"{number:.{decimals}f}".rstrip("0").rstrip(".")
    mantissa, exponent = f"{number:.3E}".split("E")
    return f"{mantissa.rstrip('0').rstrip('.')}E{exponent}"


def add_display_values(evidence: dict[str, object]) -> None:
    """Add formatted representations with metric-specific units recursively."""
    metric = str(evidence["metric"])
    measure = str(evidence.get("measure", metric))

    def visit(node: object, benchmark: bool = False) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item, benchmark)
        elif isinstance(node, dict):
            for key, value in list(node.items()):
                if key in {
                    "value",
                    "price",
                    "total_performance",
                    "asset_performance",
                    "benchmark_performance",
                } and value not in (None, "None"):
                    kind = metric
                    if key == "value" and measure == "excess_return" and not benchmark:
                        kind = "excess_return"
                    node[f"{key}_display"] = display_value(value, kind)
                    node[f"{key}_unit"] = (
                        "percentage_points"
                        if kind == "excess_return"
                        else "coefficient"
                        if kind == "correlation"
                        else node.get("currency", "unknown")
                        if kind == "price"
                        else "percent"
                    )
                elif isinstance(value, (dict, list)):
                    visit(value, benchmark=key == "benchmark")

    visit(evidence)
