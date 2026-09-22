from dataclasses import asdict
import math

import numpy as np
import pandas as pd

from config import settings
from strategy import StrategyParams, prepare, signal_series


def wilson_interval(wins, n, z=1.959963984540054):
    if n == 0:
        return float("nan"), float("nan")

    p = wins / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom

    return centre - margin, centre + margin


def backtest(df_raw, params=None, fee_r=None, slippage_atr=None):
    p = params or StrategyParams()

    fee_r = settings.fee_r if fee_r is None else float(fee_r)
    slippage_atr = settings.slippage_atr if slippage_atr is None else float(slippage_atr)

    df = prepare(df_raw)

    if p.stop_atr <= 0 or p.target_atr <= 0 or p.max_hold_bars <= 0:
        return {
            "status": "INVALID_PARAMS",
            "reason": "Stop/target/max_hold must be positive.",
            "params": asdict(p),
            "trades": [],
        }

    if len(df) < 250:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Need at least 250 candles.",
            "params": asdict(p),
            "trades": [],
        }

    sig = signal_series(df, p)
    trades = []
    i = 0

    while i < len(df) - 1:
        if sig.iloc[i] == 0:
            i += 1
            continue

        row = df.iloc[i]
        atr_value = row["atr14"]

        if not pd.notna(atr_value):
            i += 1
            continue

        atr_value = float(atr_value)

        if not math.isfinite(atr_value) or atr_value <= 0:
            i += 1
            continue

        direction = int(sig.iloc[i])
        entry_bar = df.iloc[i + 1]

        try:
            raw_entry = float(entry_bar["open"])
        except Exception:
            i += 1
            continue

        if not math.isfinite(raw_entry):
            i += 1
            continue

        entry = raw_entry + direction * atr_value * slippage_atr
        risk_distance = atr_value * float(p.stop_atr)

        if risk_distance <= 0:
            i += 1
            continue

        stop = entry - direction * risk_distance
        target = entry + direction * atr_value * float(p.target_atr)

        future = df.iloc[i + 1 : i + 1 + int(p.max_hold_bars)]

        if future.empty:
            break

        outcome_r = None
        hold = 0
        reason = ""
        ambiguous = False

        for j in range(len(future)):
            bar = future.iloc[j]

            if direction == 1:
                hit_stop = bar["low"] <= stop
                hit_target = bar["high"] >= target
            else:
                hit_stop = bar["high"] >= stop
                hit_target = bar["low"] <= target

            if hit_stop and hit_target:
                outcome_r = -1.0
                hold = j + 1
                ambiguous = True
                reason = "AMBIGUOUS_STOP_AND_TARGET"
                break

            if hit_stop:
                outcome_r = -1.0
                hold = j + 1
                reason = "STOP"
                break

            if hit_target:
                outcome_r = float(p.target_atr / p.stop_atr)
                hold = j + 1
                reason = "TARGET"
                break

        if outcome_r is None:
            last = future.iloc[-1]

            if direction == 1:
                move = float(last["close"]) - entry
            else:
                move = entry - float(last["close"])

            outcome_r = move / risk_distance
            hold = len(future)
            reason = "TIME"

        net_r = float(outcome_r - fee_r)

        trades.append(
            {
                "signal_epoch": int(row["epoch"]),
                "entry_epoch": int(entry_bar["epoch"]),
                "direction": "LONG" if direction == 1 else "SHORT",
                "entry": entry,
                "stop": stop,
                "target": target,
                "r": net_r,
                "hold_bars": hold,
                "exit_reason": reason,
                "ambiguous": ambiguous,
            }
        )

        i += max(1, hold + 1)

    trade_df = pd.DataFrame(trades)

    if trade_df.empty:
        return {
            "status": "NO_TRADES",
            "params": asdict(p),
            "trades": [],
        }

    r = trade_df["r"].astype(float)

    wins = int((r > 0).sum())
    losses = int((r < 0).sum())

    gross_profit = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = 999.0 if gross_profit > 0 else 0.0

    equity = r.cumsum()
    peak = equity.cummax()
    dd = equity - peak
    max_dd = float(dd.min())

    avg_r = float(r.mean())
    lo, hi = wilson_interval(wins, len(r))

    losing_streak = 0
    max_losing_streak = 0

    for x in r:
        if x < 0:
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0

    return {
        "status": "OK",
        "params": asdict(p),
        "fee_r": fee_r,
        "slippage_atr": slippage_atr,
        "trade_count": int(len(r)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(r)),
        "win_rate_ci95": [float(lo), float(hi)],
        "avg_r": avg_r,
        "expectancy_r": avg_r,
        "profit_factor": float(profit_factor),
        "max_drawdown_r": max_dd,
        "max_losing_streak": int(max_losing_streak),
        "avg_hold_bars": float(trade_df["hold_bars"].mean()),
        "total_r": float(r.sum()),
        "ambiguous_trades": int(trade_df["ambiguous"].sum()),
        "trades": trades,
        "trade_table": trade_df,
    }
