import numpy as np
import pandas as pd


def ema(series, period):
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rsi(series, period=14):
    delta = series.diff()

    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.where(avg_loss != 0, 100.0)
    out = out.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)

    return out


def macd(series, fast=12, slow=26, signal=9):
    line = ema(series, fast) - ema(series, slow)
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def true_range(df):
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr


def atr(df, period=14):
    return true_range(df).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def build_features(df, rsi_period=14, atr_period=14):
    out = df.copy()

    if "epoch" in out.columns:
        out = out.sort_values("epoch")
    else:
        out = out.sort_index()

    out = out.reset_index(drop=True)

    for col in ["open", "high", "low", "close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["rsi14"] = rsi(out["close"], rsi_period)

    macd_line, macd_signal, macd_hist = macd(out["close"])
    out["macd"] = macd_line
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist

    out["atr14"] = atr(out, atr_period)

    out["ret1"] = out["close"].pct_change()
    out["vol20"] = out["ret1"].rolling(20).std()

    out["range"] = out["high"] - out["low"]
    out["body"] = (out["close"] - out["open"]).abs()
    out["upper_wick"] = out["high"] - out[["open", "close"]].max(axis=1)
    out["lower_wick"] = out[["open", "close"]].min(axis=1) - out["low"]

    return out
