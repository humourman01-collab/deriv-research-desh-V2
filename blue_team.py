import pandas as pd


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def run(validation, red):
    evidence = []

    test = validation.get("test", {}) or {}

    if test.get("status") == "OK":
        trade_count = int(_num(test.get("trade_count"), 0))

        evidence.append(
            f"Out-of-sample test recomputed {trade_count} trades from historical OHLC."
        )

        ci = test.get("win_rate_ci95") or []

        if len(ci) == 2:
            try:
                evidence.append(
                    f"OOS win rate {_num(test.get('win_rate'), 0.0):.2%}, "
                    f"95% CI {float(ci[0]):.2%} to {float(ci[1]):.2%}."
                )
            except Exception:
                pass

        evidence.append(
            f"OOS expectancy {_num(test.get('expectancy_r'), 0.0):.3f}R; "
            f"profit factor {_num(test.get('profit_factor'), 0.0):.2f}; "
            f"max drawdown {_num(test.get('max_drawdown_r'), 0.0):.2f}R."
        )

    wf = validation.get("walk_forward", {}) or {}

    segments = [
        s
        for s in wf.get("segments", [])
        if s.get("test", {}).get("status") == "OK"
    ]

    if segments:
        positive = sum(
            1
            for s in segments
            if _num(s["test"].get("expectancy_r"), 0.0) > 0.0
        )

        evidence.append(
            f"Walk-forward: {positive}/{len(segments)} sequential test windows have positive expectancy."
        )

    sens = validation.get("sensitivity")

    if isinstance(sens, pd.DataFrame) and not sens.empty and "expectancy_r" in sens.columns:
        positive = sens["expectancy_r"].dropna()

        if not positive.empty:
            evidence.append(
                f"Sensitivity grid: {(positive > 0).mean():.0%} of nearby parameter sets have positive train expectancy."
            )

    unresolved = [
        a
        for a in red.get("attacks", [])
        if a.get("severity") == "HIGH"
    ]

    status = "SUPPORT" if not unresolved and evidence else "INSUFFICIENT"

    return {
        "status": status,
        "evidence": evidence,
        "unresolved_red_flags": unresolved,
    }
