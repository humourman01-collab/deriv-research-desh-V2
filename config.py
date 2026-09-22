from dataclasses import dataclass, field
import os


def _get_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


DEFAULT_SYMBOL_QUERIES = {
    "Volatility 1s 150": [
        "Volatility 150 (1s)",
        "Volatility 150(1s)",
        "1HZ150V",
        "R_150_1s",
    ],
    "Jump 100": [
        "Jump 100",
        "Jump 100 Index",
        "JD100",
    ],
    "Drift Switch 10": [
        "Drift Switch 10",
        "Drift Switch 10 Index",
        "DS10",
    ],
    "Drift Switch 20": [
        "Drift Switch 20",
        "Drift Switch 20 Index",
        "DS20",
    ],
    "Volatility 1s 75": [
        "Volatility 75 (1s)",
        "Volatility 75(1s)",
        "1HZ75V",
        "R_75_1s",
    ],
    "Volatility 25": [
        "Volatility 25",
        "Volatility 25 Index",
        "R_25",
    ],
    "Jump 10": [
        "Jump 10",
        "Jump 10 Index",
        "JD10",
    ],
}


@dataclass(frozen=True)
class Settings:
    api_url: str = os.getenv("DERIV_WS_URL", "wss://ws.derivws.com/websockets/v3")
    app_id: str = os.getenv("DERIV_APP_ID", "1089")
    db_path: str = os.getenv("DB_PATH", "data/deriv_research.sqlite")

    default_days: int = _get_int("BACKTEST_DAYS", 365)
    fetch_chunk: int = _get_int("FETCH_CHUNK", 500)
    request_sleep: float = _get_float("REQUEST_SLEEP", 0.25)

    rsi_period: int = 14
    atr_period: int = 14

    rsi_long_threshold: float = _get_float("RSI_LONG_THRESHOLD", 35.0)
    rsi_short_threshold: float = _get_float("RSI_SHORT_THRESHOLD", 65.0)
    stop_atr: float = _get_float("STOP_ATR", 1.0)
    target_atr: float = _get_float("TARGET_ATR", 2.0)
    max_hold_bars: int = _get_int("MAX_HOLD_BARS", 20)

    fee_r: float = _get_float("FEE_R", 0.0)
    slippage_atr: float = _get_float("SLIPPAGE_ATR", 0.0)

    schedule_symbols: str = os.getenv("SCHEDULE_SYMBOLS", "ALL")
    schedule_timeframes: str = os.getenv("SCHEDULE_TIMEFRAMES", "1h,4h")

    llm_url: str = os.getenv("LLM_API_URL", "")
    llm_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")

    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID", "")
    dashboard_link: str = os.getenv("DASHBOARD_LINK", "")

    symbol_queries: dict = field(default_factory=lambda: DEFAULT_SYMBOL_QUERIES.copy())

    @property
    def ws_endpoint(self):
        if not self.app_id:
            return self.api_url
        sep = "&" if "?" in self.api_url else "?"
        return f"{self.api_url}{sep}app_id={self.app_id}"


settings = Settings()
