import json
import urllib.request

from config import settings


def explain(report):
    if not (settings.llm_url and settings.llm_key and settings.llm_model):
        return None

    summary = {
        "symbol": report.get("symbol"),
        "timeframe": report.get("timeframe"),
        "state": report.get("state"),
        "analysis": report.get("analysis"),
        "backtest": report.get("backtest"),
        "red_team": report.get("red_team"),
        "blue_team": report.get("blue_team"),
    }

    prompt = (
        "You are a quantitative research report editor. "
        "Never invent statistics. Only use numeric values present in the report. "
        "Explain this research report in simple language. "
        "State what is proven, what is unproven, and what Red Team objections remain. "
        "Do not give buy or sell instructions.\n\n"
        f"Report JSON:\n{json.dumps(summary, default=str)}"
    )

    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful research assistant. Never invent numbers.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    req = urllib.request.Request(
        settings.llm_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.llm_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"LLM unavailable: {exc}"
