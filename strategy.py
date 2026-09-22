from dataclasses import dataclass

from indicators import build_features
from patterns import add_patterns


@dataclass(frozen=True)
class StrategyParams:
    rsi_long: float = 35.0
    rsi_short: float = 65.0
    stop_atr: float = 1.0
    target_atr: float = 2.0
    max_hold_bars: int = 20


REQUIRED_COLUMNS = {
    "ema50",
    "ema200",
    "rsi14",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr14",
    "doji",
    "hammer",
    "shooting_star",
    "bullish_engulfing",
    "bearish_engulfing",
}


def prepare(df):
    if all(col in df.columns for col in REQUIRED_COLUMNS):
        out = df.copy()
    else:
        out = add_patterns(build_features(df))

    if "epoch" in out.columns:
        out = out.sort_values("epoch").reset_index(drop=True)

    return out


def signal_series(df, params):
    rsi14 = df["rsi14"]

    ema_bull = df["ema50"] > df["ema200"]
    ema_bear = df["ema50"] < df["ema200"]

    macd_bull = df["macd"] > df["macd_signal"]
    macd_bear = df["macd"] < df["macd_signal"]

    long_reclaim = (rsi14.shift(1) < params.rsi_long) & (rsi14 >= params.rsi_long)
    short_reject = (rsi14.shift(1) > params.rsi_short) & (rsi14 <= params.rsi_short)

    long_sig = (
        ema_bull
        & macd_bull
        & long_reclaim
        & (df["hammer"] | df["bullish_engulfing"])
    ).fillna(False)

    short_sig = (
        ema_bear
        & macd_bear
        & short_reject
        & (df["shooting_star"] | df["bearish_engulfing"])
    ).fillna(False)

    signal = pd.Series(0, index=df.index, dtype="int8")

    signal[long_sig & ~short_sig] = 1
    signal[short_sig & ~long_sig] = -1

    return signal
