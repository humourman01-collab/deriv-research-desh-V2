import math

import pandas as pd


def _num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def run(validation):
    attacks = []

    test = validation.get("test", {}) or {}
    train = validation.get("train", {}) or {}
    sens = validation.get("sensitivity")
    wf = validation.get("walk_forward", {}) or {}

    params = test.get("params") or train.get("params") or {}
    base_rsi = _num(params.get("rsi_long"), 35.0)
    base_stop = _num(params.get("stop_atr"), 1.0)

    if test.get("status") != "OK":
        attacks.append(
            {
                "severity": "HIGH",
                "finding": "Out-of-sample test did not produce valid trades. Either data is insufficient or the signal never fired.",
            }
        )
    else:
        trade_count = int(_num(test.get("trade_count"), 0))

        if trade_count < 100:
            attacks.append(
                {
                    "severity": "HIGH",
                    "finding": f"Out-of-sample sample is only {trade_count} trades; statistical uncertainty is high.",
                }
            )

        expectancy = _num(test.get("expectancy_r"), float("nan"))
        if not math.isfinite(expectancy) or expectancy <= 0.0:
            attacks.append(
                {
                    "severity": "HIGH",
                    "finding": "Out-of-sample expectancy is not positive.",
                }
            )

        pf = _num(test.get("profit_factor"), float("nan"))
        if not math.isfinite(pf) or pf < 1.0:
            attacks.append(
                {
                    "severity": "HIGH",
                    "finding": "Out-of-sample profit factor is below 1.0.",
                }
            )

        if train.get("status") == "OK":
            train_wr = _num(train.get("win_rate"), float("nan"))
            test_wr = _num(test.get("win_rate"), float("nan"))

            if math.isfinite(train_wr) and math.isfinite(test_wr):
                gap = train_wr - test_wr
                if gap > 0.10:
                    attacks.append(
                        {
                            "severity": "HIGH",
                            "finding": f"Train/test win-rate degradation is {gap:.1%}.",
                        }
                    )

        max_dd = _num(test.get("max_drawdown_r"), float("nan"))
        if math.isfinite(max_dd) and max_dd < -20.0:
            attacks.append(
                {
                    "severity": "HIGH",
                    "finding": f"Out-of-sample drawdown is {max_dd:.2f}R, which is severe.",
                }
            )

        ambiguous = int(_num(test.get("ambiguous_trades"), 0))
        if trade_count > 0 and ambiguous / trade_count > 0.10:
            attacks.append(
                {
                    "severity": "MEDIUM",
                    "finding": "More than 10% of trades had same-bar stop/target ambiguity.",
                }
            )

    if isinstance(sens, pd.DataFrame) and not sens.empty and "expectancy_r" in sens.columns:
        positive = sens["expectancy_r"].dropna()

        base_rows = pd.DataFrame()

        if {"rsi_long", "stop_atr"}.issubset(sens.columns):
            base_rows = sens[
                (sens["rsi_long"] == base_rsi)
                & (sens["stop_atr"] == base_stop)
            ]

        if not base_rows.empty:
            base_exp = _num(base_rows["expectancy_r"].iloc[0], float("nan"))

            if (
                math.isfinite(base_exp)
                and base_exp > 0
                and not positive.empty
                and float((positive > 0).mean()) < 0.50
            ):
                attacks.append(
                    {
                        "severity": "MEDIUM",
                        "finding": "Parameter sensitivity is weak; positive expectancy does not survive most nearby settings.",
                    }
                )
        elif not positive.empty and float((positive > 0).mean()) < 0.50:
            attacks.append(
                {
                    "severity": "MEDIUM",
                    "finding": "Parameter sensitivity is weak; positive expectancy does not survive most nearby settings.",
                }
            )

    segments = [
        s
        for s in wf.get("segments", [])
        if s.get("test", {}).get("status") == "OK"
    ]

    if segments:
        positive_segments = sum(
            1
            for s in segments
            if _num(s["test"].get("expectancy_r"), 0.0) > 0.0
        )

        if positive_segments / len(segments) < 0.50:
            attacks.append(
                {
                    "severity": "HIGH",
                    "finding": "Fewer than half of walk-forward test segments have positive expectancy.",
                }
            )
    else:
        if wf.get("status") == "NO_VALID_SEGMENTS":
            attacks.append(
                {
                    "severity": "MEDIUM",
                    "finding": "Walk-forward produced no valid test segments.",
                }
            )

    status = "FAIL" if any(a["severity"] == "HIGH" for a in attacks) else "PASS"

    return {
        "status": status,
        "attacks": attacks,
    }
