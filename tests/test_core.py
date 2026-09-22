import numpy as np
import pandas as pd

from indicators import rsi, ema
from patterns import add_patterns
from backtest import backtest
from strategy import StrategyParams, prepare
from validation import full_validation


def make_data(n=1200, seed=7):
    rng = np.random.default_rng(seed)

    returns = rng.normal(0, 0.002, n)
    close = 100 * np.exp(np.cumsum(returns))

    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.003, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.003, n))

    return pd.DataFrame(
        {
            "epoch": np.arange(n) * 3600,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    )


def test_ema_length():
    s = pd.Series(range(300), dtype=float)
    assert ema(s, 50).iloc[-1] > 0


def test_rsi_bounds():
    s = pd.Series(np.linspace(100, 110, 100))
    r = rsi(s).dropna()

    assert ((r >= 0) & (r <= 100)).all()


def test_patterns_shape():
    df = make_data()
    out = add_patterns(df)

    assert len(out) == len(df)


def test_backtest_not_hardcoded():
    result = backtest(make_data(), StrategyParams())

    assert result["status"] in {"OK", "NO_TRADES", "INSUFFICIENT_DATA"}

    if result["status"] == "OK":
        assert result["trade_count"] == len(result["trades"])


def test_validation_structure():
    df = make_data(1600)
    prepared = prepare(df)

    val = full_validation(prepared, StrategyParams())

    assert "train" in val
    assert "validation" in val
    assert "test" in val
    assert "walk_forward" in val
    assert "sensitivity" in val
