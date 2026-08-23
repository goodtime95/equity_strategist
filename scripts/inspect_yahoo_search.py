from pprint import pprint

import yfinance as yf

QUERIES = (
    "Schneider Electric",
    "Safran",
    "Siemens",
    "TotalEnergies",
)


def main() -> None:
    for query in QUERIES:
        print()
        print("=" * 100)
        print(f"QUERY: {query}")
        print("=" * 100)

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
            print(f"RESULT #{rank}")
            pprint(quote)


if __name__ == "__main__":
    main()
