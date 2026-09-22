import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import settings
from deriv_api import resolve_symbol, backfill_candles
from storage import Store
from strategy import StrategyParams, prepare
from validation import full_validation
from red_team import run as red_run
from blue_team import run as blue_run
from manager import manager_report, compact_text


st.set_page_config(page_title="Deriv Research Desk v2", layout="wide")
st.title("Deriv Research Desk v2")
st.caption("Research/backtesting only. No order execution. No hardcoded performance.")


def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def fmt_percent(value):
    try:
        val = float(value)
        if pd.isna(val):
            return "n/a"
        return f"{val:.2%}"
    except Exception:
        return "n/a"


def fmt_num(value, digits=3):
    try:
        val = float(value)
        if pd.isna(val):
            return "n/a"
        return f"{val:.{digits}f}"
    except Exception:
        return "n/a"


with st.sidebar:
    symbol_name = st.selectbox("Symbol", list(settings.symbol_queries))
    timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    days = st.slider("Historical days", 30, 365, settings.default_days)
    run = st.button("Run analysis", type="primary")

    st.caption("Optional Telegram/LLM are controlled by environment variables.")

if run:
    with st.spinner("Resolving symbol and downloading candles..."):
        resolved = resolve_symbol(settings.symbol_queries.get(symbol_name, [symbol_name]))

        if not resolved:
            st.error("Could not resolve symbol from Deriv active_symbols.")
            st.stop()

        code = resolved["code"]

        granularity = {
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }[timeframe]

        min_days = max(days, int((300 * granularity) / 86400) + 10)

        df = backfill_candles(code, granularity, days=min_days)

        if df.empty:
            st.error("No candle data returned.")
            st.stop()

        Store().upsert(code, timeframe, df)

    with st.spinner("Computing indicators, backtest, validation, red/blue review..."):
        prepared = prepare(df)

        params = StrategyParams(
            rsi_long=settings.rsi_long_threshold,
            rsi_short=settings.rsi_short_threshold,
            stop_atr=settings.stop_atr,
            target_atr=settings.target_atr,
            max_hold_bars=settings.max_hold_bars,
        )

        validation = full_validation(prepared, params)

        red = red_run(validation)
        blue = blue_run(validation, red)

        analysis = {
            "resolved_code": code,
            "display_name": resolved.get("name", symbol_name),
            "last_price": safe_float(prepared["close"].iloc[-1]),
            "rsi14": safe_float(prepared["rsi14"].iloc[-1]),
            "ema50": safe_float(prepared["ema50"].iloc[-1]),
            "ema200": safe_float(prepared["ema200"].iloc[-1]),
            "macd": safe_float(prepared["macd"].iloc[-1]),
            "macd_signal": safe_float(prepared["macd_signal"].iloc[-1]),
            "macd_hist": safe_float(prepared["macd_hist"].iloc[-1]),
            "atr14": safe_float(prepared["atr14"].iloc[-1]),
        }

        report = manager_report(
            symbol_name,
            timeframe,
            analysis,
            validation,
            red,
            blue,
        )

    st.subheader(f"{resolved.get('name', symbol_name)} — {timeframe.upper()}")
    st.code(compact_text(report))

    b = report.get("backtest", {}) or {}

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("OOS trades", b.get("trade_count", 0))
    c2.metric("OOS win rate", fmt_percent(b.get("win_rate")))
    c3.metric("OOS expectancy", fmt_num(b.get("expectancy_r"), 3) + "R")
    c4.metric("OOS profit factor", fmt_num(b.get("profit_factor"), 2))

    st.subheader("Price")

    chart = df.copy()
    chart["time"] = pd.to_datetime(chart["epoch"], unit="s", utc=True)

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=chart["time"],
                open=chart["open"],
                high=chart["high"],
                low=chart["low"],
                close=chart["close"],
                name="OHLC",
            )
        ]
    )

    fig.update_layout(height=520, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Latest indicators")
    st.json(analysis)

    st.subheader("Red Team")
    st.json(red)

    st.subheader("Blue Team")
    st.json(blue)

    st.subheader("Walk-forward")
    st.json(validation.get("walk_forward", {}))

    st.subheader("Parameter sensitivity")

    sens = validation.get("sensitivity")

    if hasattr(sens, "empty"):
        st.dataframe(sens, use_container_width=True)
    else:
        st.json(sens)

    if report.get("llm"):
        st.subheader("LLM explanation")
        st.write(report["llm"])

else:
    st.info(
        "Press Run analysis. This app calculates all statistics from Deriv historical candles. "
        "It does not use hardcoded win rates or fake confidence."
    )
