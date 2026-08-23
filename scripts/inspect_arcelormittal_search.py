import yfinance as yf

QUERIES = (
    "ARCELORMITTAL SA",
    "ArcelorMittal",
    "ArcelorMittal Paris",
)


def main() -> None:
    for query in QUERIES:
        print()
        print("=" * 100)
        print(f"QUERY: {query}")

        search = yf.Search(
            query,
            max_results=10,
            news_count=0,
        )

        for rank, quote in enumerate(
            search.quotes,
            start=1,
        ):
            print()
            print(
                rank,
                quote.get("symbol"),
                "|",
                quote.get("longname") or quote.get("shortname"),
                "|",
                quote.get("exchDisp"),
                "|",
                quote.get("quoteType"),
            )


if __name__ == "__main__":
    main()
