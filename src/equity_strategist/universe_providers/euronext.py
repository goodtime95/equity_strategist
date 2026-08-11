from equity_strategist.domain.universe_constituent import (
    UniverseConstituent,
)


def _paris_constituent(
    name: str,
    isin: str,
) -> UniverseConstituent:
    """Build a constituent listed on Euronext Paris."""
    return UniverseConstituent(
        name=name,
        isin=isin,
        exchange="Paris",
    )


class EuronextUniverseProvider:
    """
    Provide Euronext index constituents.

    Temporary MVP implementation using a local snapshot of official
    Euronext constituent data.

    The provider contract remains independent from this storage choice,
    allowing the snapshot to be replaced later by a live Euronext
    data source without changing downstream services.
    """

    CAC40_IDENTIFIER = "FR0003500008-XPAR"

    CAC40_CONSTITUENTS = (
        _paris_constituent(
            "ACCOR",
            "FR0000120404",
        ),
        _paris_constituent(
            "AIR LIQUIDE",
            "FR0000120073",
        ),
        _paris_constituent(
            "AIRBUS",
            "NL0000235190",
        ),
        _paris_constituent(
            "ARCELORMITTAL SA",
            "LU1598757687",
        ),
        _paris_constituent(
            "AXA",
            "FR0000120628",
        ),
        _paris_constituent(
            "BNP PARIBAS ACT.A",
            "FR0000131104",
        ),
        _paris_constituent(
            "BOUYGUES",
            "FR0000120503",
        ),
        _paris_constituent(
            "BUREAU VERITAS",
            "FR0006174348",
        ),
        _paris_constituent(
            "CAPGEMINI",
            "FR0000125338",
        ),
        _paris_constituent(
            "CARREFOUR",
            "FR0000120172",
        ),
        _paris_constituent(
            "CREDIT AGRICOLE",
            "FR0000045072",
        ),
        _paris_constituent(
            "DANONE",
            "FR0000120644",
        ),
        _paris_constituent(
            "DASSAULT SYSTEMES",
            "FR0014003TT8",
        ),
        _paris_constituent(
            "EIFFAGE",
            "FR0000130452",
        ),
        _paris_constituent(
            "ENGIE",
            "FR0010208488",
        ),
        _paris_constituent(
            "ESSILORLUXOTTICA",
            "FR0000121667",
        ),
        _paris_constituent(
            "EUROFINS SCIENT.",
            "FR0014000MR3",
        ),
        _paris_constituent(
            "EURONEXT",
            "NL0006294274",
        ),
        _paris_constituent(
            "HERMES INTL",
            "FR0000052292",
        ),
        _paris_constituent(
            "KERING",
            "FR0000121485",
        ),
        _paris_constituent(
            "L'OREAL",
            "FR0000120321",
        ),
        _paris_constituent(
            "LEGRAND",
            "FR0010307819",
        ),
        _paris_constituent(
            "LVMH",
            "FR0000121014",
        ),
        _paris_constituent(
            "MICHELIN",
            "FR001400AJ45",
        ),
        _paris_constituent(
            "ORANGE",
            "FR0000133308",
        ),
        _paris_constituent(
            "PERNOD RICARD",
            "FR0000120693",
        ),
        _paris_constituent(
            "PUBLICIS GROUPE SA",
            "FR0000130577",
        ),
        _paris_constituent(
            "RENAULT",
            "FR0000131906",
        ),
        _paris_constituent(
            "SAFRAN",
            "FR0000073272",
        ),
        _paris_constituent(
            "SAINT GOBAIN",
            "FR0000125007",
        ),
        _paris_constituent(
            "SANOFI",
            "FR0000120578",
        ),
        _paris_constituent(
            "SCHNEIDER ELECTRIC",
            "FR0000121972",
        ),
        _paris_constituent(
            "SOCIETE GENERALE",
            "FR0000130809",
        ),
        _paris_constituent(
            "STELLANTIS NV",
            "NL00150001Q9",
        ),
        _paris_constituent(
            "STMICROELECTRONICS",
            "NL0000226223",
        ),
        _paris_constituent(
            "THALES",
            "FR0000121329",
        ),
        _paris_constituent(
            "TOTALENERGIES",
            "FR0000120271",
        ),
        _paris_constituent(
            "UNIBAIL-RODAMCO-WE",
            "FR0013326246",
        ),
        _paris_constituent(
            "VEOLIA ENVIRON.",
            "FR0000124141",
        ),
        _paris_constituent(
            "VINCI",
            "FR0000125486",
        ),
    )

    def get_constituents(
        self,
        provider_identifier: str,
    ) -> tuple[UniverseConstituent, ...]:
        """Return constituents for a supported Euronext index."""

        if provider_identifier == self.CAC40_IDENTIFIER:
            return self.CAC40_CONSTITUENTS

        raise ValueError(f"unsupported Euronext universe: {provider_identifier}")
