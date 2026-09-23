"""Deterministic French validation and evidence templates."""

from equity_strategist.domain.request_validation import (
    RequestStatus,
    RequestValidationResult,
)

FRENCH_ISSUES = {
    "missing_asset_source": "Précisez au moins un actif ou un univers.",
    "conflicting_asset_sources": "Choisissez des actifs ou un univers, pas les deux.",
    "blank_asset": "Précisez un nom ou un symbole d’actif non vide.",
    "duplicate_asset": "Précisez des actifs distincts, sans doublons.",
    "blank_universe": "Précisez un univers non vide.",
    "missing_metric": "Précisez la métrique à analyser.",
    "horizon_start_conflict": (
        "Un horizon utilise la date de fin comme "
        "ancrage ; ne renseignez pas de date "
        "de début."
    ),
    "missing_horizon_anchor": "Précisez la date de fin servant d’ancrage à l’horizon.",
    "mixed_horizon_metrics": (
        "Les horizons de performance ne peuvent "
        "pas être combinés aux autres métriques "
        "de période ; utilisez une période explicite."
    ),
    "missing_start_date": "Précisez la date de début.",
    "missing_end_date": "Précisez la date de fin.",
    "missing_benchmark": (
        "Cette mesure de performance nécessite un indice ou actif de référence."
    ),
    "blank_benchmark": "Précisez un indice ou actif de référence non vide.",
    "missing_target_date": "Précisez la date du cours demandé.",
    "price_asset_count": "Une demande de cours nécessite exactement un actif.",
    "comparison_asset_count": (
        "Une comparaison ou un classement nécessite au moins deux actifs distincts."
    ),
    "correlation_asset_count": "Une corrélation nécessite au moins deux actifs.",
    "distinct_performance_dates_required": (
        "Une performance nécessite deux dates "
        "ou observations distinctes. Précisez "
        "un début et une fin sur deux séances "
        "distinctes."
    ),
    "benchmark_metric_unsupported": (
        "Un indice de référence est pris en charge uniquement pour la performance."
    ),
    "horizon_metric_unsupported": (
        "Les horizons sont pris en charge uniquement pour la performance."
    ),
    "performance_measure_metric_unsupported": (
        "Le choix de mesure de performance est réservé à l’analyse de performance."
    ),
    "constraints_unsupported": (
        "Les contraintes demandées ne sont pas prises en charge."
    ),
    "market_period_unsupported": (
        "Les périodes de marché nommées ne sont "
        "pas prises en charge ; seules les dates "
        "explicites sont disponibles."
    ),
    "ranking_direction_unsupported": (
        "Le sens de classement est réservé aux demandes de classement."
    ),
    "top_n_unsupported": "La sélection top_n est réservée aux demandes de classement.",
    "target_date_unsupported": "La date cible est réservée aux demandes de cours.",
    "period_dates_unsupported": (
        "Les dates de début et de fin sont réservées aux métriques de période."
    ),
}

METRIC_LABELS = {
    "performance": "Performance",
    "volatility": "Volatilité historique",
    "correlation": "Corrélation historique",
    "maximum_drawdown": "Baisse maximale depuis un sommet",
    "price": "Cours",
}


def french_validation_issues(validation: RequestValidationResult) -> list[str]:
    lines = []
    for index, issue in enumerate(validation.issues):
        code = (
            validation.issue_codes[index]
            if index < len(validation.issue_codes)
            else None
        )
        if code in FRENCH_ISSUES:
            lines.append(FRENCH_ISSUES[code])
        elif code == "analysis_combination_unsupported":
            combination = issue.rsplit(": ", 1)[-1]
            for source, target in {
                "rank": "classement",
                "compare": "comparaison",
                "analyze": "analyse",
                "get": "consultation",
                "drawdown": "baisse maximale",
                "price": "cours",
                "volatility": "volatilité",
                "correlation": "corrélation",
            }.items():
                combination = combination.replace(source, target)
            lines.append(f"Combinaison non prise en charge : {combination}.")
        elif code == "universe_capability_unsupported":
            lines.append(
                "Cette opération ne prend pas en charge les univers : "
                + issue.rsplit(": ", 1)[-1]
            )
        else:
            # Unknown/legacy issues retain their precise semantics, quoted as supplied.
            label = (
                "Ambiguïté relevée"
                if validation.status == RequestStatus.UNSUPPORTED
                else "Point à préciser"
            )
            lines.append(f"{label} : « {issue} »")
    return lines


def currency_note(period: dict, french: bool) -> str:
    if (
        not period.get("benchmark")
        and len(period.get("comparison_items") or period.get("items", [])) < 2
    ):
        return ""
    currencies = {
        item.get("currency")
        for item in (period.get("comparison_items") or period.get("items", []))
    }
    if period.get("benchmark"):
        currencies.add(period["benchmark"].get("currency"))
    mixed_or_unknown = len(currencies) > 1 or not period["currency_metadata_complete"]
    if french:
        note = (
            "Comparaison des rendements en devises natives, sans conversion "
            "ni effet de change"
        )
        if mixed_or_unknown:
            note += " ; ce n’est pas une surperformance dans une devise commune"
        note += "."
        if not period["currency_metadata_complete"]:
            note += " Certaines devises ne sont pas renseignées."
    else:
        note = (
            "Returns compared in native currencies, without FX conversion "
            "or exchange-rate effects"
        )
        if mixed_or_unknown:
            note += "; this is not common-currency outperformance"
        note += "."
        if not period["currency_metadata_complete"]:
            note += " Some currency metadata is unavailable."
    return note


def methodology_note(result: dict, french: bool) -> str:
    parts = []
    field = result.get("price_field") or result.get("price_type")
    if field:
        parts.append(
            ("cours ajustés" if field == "adjusted_close" else "cours bruts")
            if french
            else str(field)
        )
    method = result.get("return_method")
    if method:
        parts.append(
            ("rendements logarithmiques" if method == "log" else "rendements simples")
            if french
            else f"{method} returns"
        )
    factor = result.get("annualization_factor")
    if factor:
        parts.append(
            f"annualisation : {factor}" if french else f"annualization: {factor}"
        )
    return (
        ("Convention : " if french else "Convention: ") + ", ".join(parts)
        if parts
        else ""
    )


def french_result(result: dict) -> str:
    lines = [METRIC_LABELS[result["metric"]]]
    if result["metric"] == "price":
        lines.append(
            f"{result.get('name') or result['symbol']} "
            f"({result['symbol']}) : {result['price_display']} "
            f"{result.get('currency', '')}, le {result['effective_date']}."
        )
        if result["used_previous_session"]:
            lines.append(
                f"Date demandée : {result['requested_date']} "
                f"; utilisation de la séance disponible "
                f"précédente."
            )
    else:
        if "measure" in result:
            lines.append(
                {
                    "total": "Performance totale",
                    "annualized": "Performance annualisée",
                    "relative": (
                        "Performance relative (rapport des facteurs de croissance)"
                    ),
                    "excess_return": "Écart de rendement en points de pourcentage",
                }[result["measure"]]
            )
        periods = result.get("periods", [result])
        for period in periods:
            start = period.get("requested_start_date", period.get("start_date"))
            end = period.get("requested_end_date", period.get("end_date"))
            horizon = period.get("horizon")
            lines.append(
                f"{horizon.upper() + ' — ' if horizon else ''}Période "
                f"demandée : du {start} au {end}."
            )
            if period.get("effective_start_date") and period.get("effective_end_date"):
                lines.append(
                    f"Calcul : du {period['effective_start_date']} "
                    f"au {period['effective_end_date']}."
                )
            else:
                lines.append("Dates effectives non renseignées.")
            benchmark = period.get("benchmark")
            if benchmark:
                lines.append(f"Référence : {_item_line(benchmark)}")
            if period.get("comparison_items"):
                lines.append("Sélection :")
            lines.extend(_item_line(item) for item in period["items"])
            if period.get("comparison_items"):
                lines.append("Ensemble comparé (ordre du classement) :")
                lines.extend(_item_line(item) for item in period["comparison_items"])
            if "currency_convention" in period:
                lines.append(currency_note(period, True))
    lines.append(methodology_note(result, True))
    return "\n".join(line for line in lines if line)


def _item_line(item: dict) -> str:
    if "first_symbol" in item:
        name = (
            f"{item.get('first_name') or item['first_symbol']} "
            f"({item['first_symbol']}) / "
            f"{item.get('second_name') or item['second_symbol']} "
            f"({item['second_symbol']})"
        )
    else:
        name = f"{item.get('name') or item['symbol']} ({item['symbol']})"
    prefix = f"{item['rank']}. " if item.get("rank") is not None else ""
    line = f"{prefix}{name} : {item['value_display']}"
    if item.get("currency"):
        line += f" [devise : {item['currency']}]"
    if "peak_date" in item:
        line += (
            f" ; sommet : {item['peak_date']}, creux "
            f": {item['trough_date']}, récupération "
            f": {item.get('recovery_date') or 'non observée'}"
        )
    if item.get("asset_performance_display"):
        line += (
            f" ; actif : {item['asset_performance_display']}, "
            f"référence : {item['benchmark_performance_display']}"
        )
    return line
