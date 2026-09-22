# Deriv Research Desk v2

Educational research/backtesting desk for Deriv Synthetic Indices.

This project does **not** place orders. It does **not** auto-trade. It only researches historical price data and reports measured statistics.

## What it does

- Fetches Deriv synthetic candles using Deriv public WebSocket market-data API.
- Resolves symbols from `active_symbols` instead of assuming permanent codes.
- Calculates EMA, RSI, MACD, ATR, candle geometry, and candlestick patterns.
- Backtests a reproducible confluence rule.
- Uses next-candle-open entry.
- Uses ATR stop/target.
- Treats same-bar stop/target ambiguity conservatively.
- Splits data into train/validation/test.
- Runs walk-forward checks.
- Runs parameter sensitivity checks.
- Red Team attacks weak results.
- Blue Team supports only evidence-backed results.
- Sends optional Telegram reports.
- Provides a Streamlit dashboard.

## Important limitation

This is a price-series research framework. It does not prove that RSI, MACD, EMA, or candlestick patterns have an edge on synthetic indices. Any edge must be established empirically.

Synthetic indices are risky. This is not financial advice.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python backfill.py --symbol ALL --timeframe 1h 4h 1d --days 365
python runner.py --symbol "Volatility 25" --timeframe 1h
streamlit run app.py
python scheduler.py
```

## Telegram

Set in `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DASHBOARD_LINK=https://your-dashboard-link
```

## Tests

```bash
python -m pytest -q
```
