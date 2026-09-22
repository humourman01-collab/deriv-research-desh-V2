import argparse
import json

import pandas as pd

from config import settings
from deriv_api import resolve_symbol, backfill_candles
from storage import Store
from strategy import StrategyParams, prepare
from validation import full_validation
from red_team import run as red_run
from blue_team import run as blue_run
from manager import manager_report, compact_text
from llm import explain
from telegram import send


TF = {
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


def _last(series):
    try:
        if series is None or len(series) == 0:
            return None

        val = series.iloc[-1]

        if pd.isna(val):
            return None

        return float(val)
    except Exception:
        return None


def resolve_or_fail(symbol_name):
    candidates = settings.symbol_queries.get(symbol_name, [symbol_name])
    resolved = resolve_symbol(candidates)

    if not resolved or not resolved.get("code"):
        raise RuntimeError(f"Could not resolve Deriv symbol: {symbol_name}")

    return resolved


def analyze(symbol_name, timeframe, days=None, save=True):
    if timeframe not in TF:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    days = int(days or settings.default_days)

    resolved = resolve_or_fail(symbol_name)
    code = resolved["code"]

    granularity = TF[timeframe]
    min_days = max(days, int((300 * granularity) / 86400) + 10)

    df = backfill_candles(code, granularity, days=min_days)

    if save and not df.empty:
        Store().upsert(code, timeframe, df)

    if df.empty:
        df = Store().read(code, timeframe)

    if df.empty:
        raise RuntimeError(f"No candle data for {symbol_name} ({code}) {timeframe}.")

    max_bars = max(700, int(days * 86400 / granularity) + 500)
    df = df.tail(max_bars).reset_index(drop=True)

    params = StrategyParams(
        rsi_long=settings.rsi_long_threshold,
        rsi_short=settings.rsi_short_threshold,
        stop_atr=settings.stop_atr,
        target_atr=settings.target_atr,
        max_hold_bars=settings.max_hold_bars,
    )

    prepared = prepare(df)
    validation = full_validation(prepared, params)

    analysis = {
        "resolved_code": code,
        "display_name": resolved.get("name", symbol_name),
        "last_price": _last(prepared["close"]),
        "rsi14": _last(prepared["rsi14"]),
        "ema50": _last(prepared["ema50"]),
        "ema200": _last(prepared["ema200"]),
        "macd": _last(prepared["macd"]),
        "macd_signal": _last(prepared["macd_signal"]),
        "macd_hist": _last(prepared["macd_hist"]),
        "atr14": _last(prepared["atr14"]),
    }

    red = red_run(validation)
    blue = blue_run(validation, red)

    report = manager_report(
        symbol_name,
        timeframe,
        analysis,
        validation,
        red,
        blue,
    )

    report["llm"] = explain(report)

    return report


def report_text(report):
    text = compact_text(report)

    if settings.dashboard_link:
        text += f"\nDashboard: {settings.dashboard_link}"

    return text


def main():
    ap = argparse.ArgumentParser(description="Run one Deriv research report.")

    ap.add_argument("--symbol", default="Volatility 25")
    ap.add_argument("--timeframe", default="1h", choices=list(TF))
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--telegram", action="store_true")

    args = ap.parse_args()

    report = analyze(args.symbol, args.timeframe, args.days)

    print(json.dumps(report, indent=2, default=str))
    text = report_text(report)
    print("\n" + text)

    if args.telegram:
        sent = send(text)
        print("Telegram sent." if sent else "Telegram not configured; message printed only.")


if __name__ == "__main__":
    main()
