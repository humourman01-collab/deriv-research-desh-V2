import json
import time

import pandas as pd
import websocket

from config import settings


class DerivAPIError(RuntimeError):
    pass


_ACTIVE_CACHE = {
    "ts": 0.0,
    "items": [],
}


def empty_df():
    return pd.DataFrame(columns=["epoch", "open", "high", "low", "close"])


def _request(payload, timeout=30, retries=3):
    last_error = None

    for attempt in range(retries):
        try:
            ws = websocket.create_connection(settings.ws_endpoint, timeout=timeout)
            try:
                ws.send(json.dumps(payload))

                while True:
                    raw = ws.recv()
                    if not raw:
                        continue

                    data = json.loads(raw)
                    error = data.get("error")

                    if error:
                        if isinstance(error, dict):
                            message = error.get("message", str(error))
                        else:
                            message = str(error)
                        raise DerivAPIError(message)

                    if data.get("msg_type") in {"active_symbols", "candles", "history"}:
                        return data
            finally:
                ws.close()

        except DerivAPIError:
            raise
        except Exception as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))

    raise DerivAPIError(f"Deriv request failed after {retries} attempts: {last_error}")


def active_symbols(force=False):
    now = time.time()

    if not force and _ACTIVE_CACHE["items"] and now - _ACTIVE_CACHE["ts"] < 3600:
        return _ACTIVE_CACHE["items"]

    data = _request(
        {
            "active_symbols": "brief",
            "product_type": "basic",
            "req_id": 1,
        }
    )

    items = data.get("active_symbols", [])
    if not isinstance(items, list):
        items = []

    _ACTIVE_CACHE["ts"] = now
    _ACTIVE_CACHE["items"] = items
    return items


def _symbol_code(item):
    return str(item.get("symbol") or item.get("underlying_symbol") or item.get("code") or "")


def _symbol_name(item):
    return str(
        item.get("display_name")
        or item.get("underlying_symbol_name")
        or item.get("name")
        or ""
    )


def resolve_symbol(query_candidates):
    candidates = []

    for candidate in query_candidates or []:
        text = str(candidate).strip().lower()
        if text and text not in candidates:
            candidates.append(text)

    if not candidates:
        return None

    items = active_symbols()

    def make(item):
        return {
            "code": _symbol_code(item),
            "name": _symbol_name(item),
            "raw": item,
        }

    # Exact match.
    for candidate in candidates:
        for item in items:
            code = _symbol_code(item).lower()
            name = _symbol_name(item).lower()
            if candidate == code or candidate == name:
                return make(item)

    # Compact exact match.
    for candidate in candidates:
        compact = candidate.replace(" ", "")
        for item in items:
            code = _symbol_code(item).lower().replace(" ", "")
            name = _symbol_name(item).lower().replace(" ", "")
            if compact == code or compact == name:
                return make(item)

    # Partial match.
    for candidate in candidates:
        for item in items:
            code = _symbol_code(item).lower()
            name = _symbol_name(item).lower()
            if candidate in code or candidate in name:
                return make(item)

    return None


def get_candles(symbol, granularity, count=500, end="latest"):
    payload = {
        "ticks_history": symbol,
        "end": end,
        "style": "candles",
        "granularity": int(granularity),
        "count": int(count),
        "subscribe": 0,
        "req_id": 2,
    }

    data = _request(payload)
    rows = data.get("candles", [])

    if not rows:
        return empty_df()

    df = pd.DataFrame(rows)
    required = ["epoch", "open", "high", "low", "close"]

    if any(col not in df.columns for col in required):
        return empty_df()

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)
    df["epoch"] = df["epoch"].astype("int64")
    df = df.drop_duplicates(subset=["epoch"]).sort_values("epoch").reset_index(drop=True)

    return df


def backfill_candles(symbol, granularity, days, chunk=None):
    chunk = chunk or settings.fetch_chunk
    target_bars = int(days * 86400 / granularity) + 10

    end = "latest"
    pieces = []
    remaining = target_bars
    seen_oldest = None

    while remaining > 0:
        take = min(chunk, remaining)

        try:
            df = get_candles(symbol, granularity, take, end=end)
        except DerivAPIError:
            if take > 100:
                chunk = max(100, take // 2)
                continue
            raise

        if df.empty:
            break

        pieces.append(df)
        oldest = int(df["epoch"].min())

        if seen_oldest is not None and oldest >= seen_oldest:
            break

        seen_oldest = oldest
        remaining -= len(df)

        if len(df) < take:
            chunk = max(100, len(df))

        end = oldest - 1

        if end <= 0:
            break

        time.sleep(settings.request_sleep)

    if not pieces:
        return empty_df()

    out = pd.concat(pieces, ignore_index=True)
    out = out.drop_duplicates(subset=["epoch"]).sort_values("epoch").reset_index(drop=True)

    cutoff = out["epoch"].max() - days * 86400
    return out[out["epoch"] >= cutoff].reset_index(drop=True)
