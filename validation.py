from dataclasses import replace

import numpy as np
import pandas as pd

from backtest import backtest
from strategy import StrategyParams


def split_data(df, train=0.60, validation=0.20):
    n = len(df)
    a = int(n * train)
    b = int(n * (train + validation))

    return df.iloc[:a].copy(), df.iloc[a:b].copy(), df.iloc[b:].copy()


def walk_forward(df, params, max_segments=5):
    n = len(df)

    if n < 1000:
        return {
            "status": "INSUFFICIENT_DATA",
            "segments": [],
        }

    segments = []
    train_len = max(400, int(n * 0.50))
    test_len = max(100, int(n * 0.10))

    start = 0

    while start + train_len + test_len <= n and len(segments) < max_segments:
        test = df.iloc[start + train_len : start + train_len + test_len]
        bt = backtest(test, params)

        segments.append(
            {
                "start": int(start),
                "train_bars": int(train_len),
                "test_bars": int(len(test)),
                "test": {
                    k: v
                    for k, v in bt.items()
                    if k not in {"trades", "trade_table"}
                },
            }
        )

        start += test_len

    valid = [s for s in segments if s["test"].get("status") == "OK"]

    return {
        "status": "OK" if valid else "NO_VALID_SEGMENTS",
        "segments": segments,
    }


def sensitivity(df, base):
    rows = []

    for rsi_long in [30.0, 35.0, 40.0]:
        for stop_atr in [0.75, 1.0, 1.25]:
            p = replace(
                base,
                rsi_long=float(rsi_long),
                rsi_short=float(100.0 - rsi_long),
                stop_atr=float(stop_atr),
            )

            bt = backtest(df, p)

            rows.append(
                {
                    "rsi_long": p.rsi_long,
                    "rsi_short": p.rsi_short,
                    "stop_atr": p.stop_atr,
                    "target_atr": p.target_atr,
                    "trades": bt.get("trade_count", 0),
                    "win_rate": bt.get("win_rate", np.nan),
                    "profit_factor": bt.get("profit_factor", np.nan),
                    "expectancy_r": bt.get("expectancy_r", np.nan),
                    "max_drawdown_r": bt.get("max_drawdown_r", np.nan),
                }
            )

    return pd.DataFrame(rows)


def full_validation(df, params):
    train, val, test = split_data(df)

    train_bt = backtest(train, params)
    val_bt = backtest(val, params)
    test_bt = backtest(test, params)

    wf = walk_forward(df, params)
    sens = sensitivity(train, params)

    return {
        "train": train_bt,
        "validation": val_bt,
        "test": test_bt,
        "walk_forward": wf,
        "sensitivity": sens,
    }
