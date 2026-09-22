import pandas as pd


def ensure_geometry(df):
    out = df.copy()

    if "body" not in out.columns:
        out["body"] = (out["close"] - out["open"]).abs()

    if "range" not in out.columns:
        out["range"] = out["high"] - out["low"]

    if "upper_wick" not in out.columns:
        out["upper_wick"] = out["high"] - out[["open", "close"]].max(axis=1)

    if "lower_wick" not in out.columns:
        out["lower_wick"] = out[["open", "close"]].min(axis=1) - out["low"]

    return out


def add_patterns(df):
    out = ensure_geometry(df)

    body = out["body"].clip(lower=1e-12)
    rng = out["range"].clip(lower=1e-12)

    out["doji"] = (body / rng) <= 0.10

    out["hammer"] = (
        (out["lower_wick"] >= 2.0 * body)
        & (out["upper_wick"] <= 1.2 * body)
        & (out["close"] >= out["open"])
    )

    out["shooting_star"] = (
        (out["upper_wick"] >= 2.0 * body)
        & (out["lower_wick"] <= 1.2 * body)
        & (out["close"] <= out["open"])
    )

    prev_open = out["open"].shift(1)
    prev_close = out["close"].shift(1)

    out["bullish_engulfing"] = (
        (prev_close < prev_open)
        & (out["close"] > out["open"])
        & (out["open"] <= prev_close)
        & (out["close"] >= prev_open)
    )

    out["bearish_engulfing"] = (
        (prev_close > prev_open)
        & (out["close"] < out["open"])
        & (out["open"] >= prev_close)
        & (out["close"] <= prev_open)
    )

    bool_cols = [
        "doji",
        "hammer",
        "shooting_star",
        "bullish_engulfing",
        "bearish_engulfing",
    ]

    out[bool_cols] = out[bool_cols].fillna(False).astype(bool)

    return out
