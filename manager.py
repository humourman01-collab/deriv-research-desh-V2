from datetime import datetime, timezone
import math


def _float(value, default=0.0):
    try:
        if value is None:
            return default
        out = float(value)
        return out
    except Exception:
        return default


def _fmt(value, pattern="{:.2f}", default="n/a"):
    try:
        if value is None:
            return default

        val = float(value)

        if not math.isfinite(val):
            return default

        return pattern.format(val)
    except Exception:
        return default


def _json_safe(obj):
    if hasattr(obj, "item"):
        try:
            obj = obj.item()
        except Exception:
            pass

    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]

    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj

    return obj


def manager_report(symbol_name, timeframe, analysis, validation, red, blue, llm_text=None):
    test = validation.get("test", {}) or {}

    if test.get("status") == "INSUFFICIENT_DATA":
        state = "INSUFFICIENT_DATA"
    elif test.get("status") != "OK":
        state = "NO_VALID_TEST"
    elif red.get("status") == "FAIL":
        state = "RESEARCH_FAILED"
    elif (
        blue.get("status") == "SUPPORT"
        and _float(test.get("expectancy_r")) > 0.0
        and _float(test.get("profit_factor")) > 1.0
    ):
        state = "RESEARCH_VALID"
    else:
        state = "UNPROVEN"

    sensitivity = validation.get("sensitivity")

    if hasattr(sensitivity, "to_dict"):
        sensitivity_records = sensitivity.to_dict(orient="records")
    else:
        sensitivity_records = sensitivity

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol_name,
        "timeframe": timeframe,
        "state": state,
        "analysis": analysis,
        "validation": {
            "train": {
                k: v
                for k, v in (validation.get("train") or {}).items()
                if k not in {"trades", "trade_table"}
            },
            "validation": {
                k: v
                for k, v in (validation.get("validation") or {}).items()
                if k not in {"trades", "trade_table"}
            },
            "test": {
                k: v
                for k, v in test.items()
                if k not in {"trades", "trade_table"}
            },
            "walk_forward": validation.get("walk_forward", {}),
            "sensitivity": sensitivity_records,
        },
        "backtest": {
            k: v
            for k, v in test.items()
            if k not in {"trades", "trade_table"}
        },
        "red_team": red,
        "blue_team": blue,
        "llm": llm_text,
    }

    return _json_safe(report)


def compact_text(report):
    b = report.get("backtest", {}) or {}

    ci = b.get("win_rate_ci95") or []

    if len(ci) == 2:
        try:
            ci_text = f"{float(ci[0]):.2%} to {float(ci[1]):.2%}"
        except Exception:
            ci_text = "n/a"
    else:
        ci_text = "n/a"

    lines = [
        "DERIV RESEARCH REPORT",
        f"Symbol: {report.get('symbol', 'n/a')} | TF: {report.get('timeframe', 'n/a')}",
        f"State: {report.get('state', 'n/a')}",
        f"OOS trades: {b.get('trade_count', 'n/a')}",
        f"OOS win rate: {_fmt(b.get('win_rate'), '{:.2%}')}",
        f"OOS win-rate 95% CI: {ci_text}",
        f"OOS expectancy: {_fmt(b.get('expectancy_r'), '{:.3f}')}R",
        f"OOS profit factor: {_fmt(b.get('profit_factor'))}",
        f"OOS max drawdown: {_fmt(b.get('max_drawdown_r'), '{:.2f}')}R",
        f"Max losing streak: {b.get('max_losing_streak', 'n/a')}",
        f"Ambiguous stop/target trades: {b.get('ambiguous_trades', 'n/a')}",
        f"Red Team: {report.get('red_team', {}).get('status', 'n/a')}",
        f"Blue Team: {report.get('blue_team', {}).get('status', 'n/a')}",
    ]

    return "\n".join(lines)
