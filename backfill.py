import argparse

from config import settings
from deriv_api import resolve_symbol, backfill_candles
from storage import Store


TF = {
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


def main():
    ap = argparse.ArgumentParser(description="Download historical Deriv candles into SQLite.")

    ap.add_argument("--symbol", default="ALL")
    ap.add_argument("--timeframe", nargs="+", default=["1h", "4h", "1d"], choices=list(TF))
    ap.add_argument("--days", type=int, default=settings.default_days)

    args = ap.parse_args()

    store = Store()

    if args.symbol.upper() == "ALL":
        names = list(settings.symbol_queries.keys())
    else:
        names = [args.symbol]

    for name in names:
        candidates = settings.symbol_queries.get(name, [name])
        resolved = resolve_symbol(candidates)

        if not resolved:
            print(f"SKIP: unable to resolve {name}")
            continue

        code = resolved["code"]

        for tf in args.timeframes:
            print(f"Fetching {name} [{code}] {tf} {args.days}d...")

            df = backfill_candles(code, TF[tf], args.days)
            store.upsert(code, tf, df)

            print(f"Saved {len(df)} candles")


if __name__ == "__main__":
    main()
