import os
import sqlite3

import pandas as pd

from config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS candles(
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    PRIMARY KEY(symbol, timeframe, epoch)
);

CREATE INDEX IF NOT EXISTS idx_candles_lookup
ON candles(symbol, timeframe, epoch);
"""


class Store:
    def __init__(self, path=None):
        self.path = path or settings.db_path
        directory = os.path.dirname(self.path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        with sqlite3.connect(self.path) as con:
            con.executescript(SCHEMA)

    def upsert(self, symbol, timeframe, df):
        if df.empty:
            return

        rows = []

        for r in df.itertuples():
            try:
                rows.append(
                    (
                        symbol,
                        timeframe,
                        int(r.epoch),
                        float(r.open),
                        float(r.high),
                        float(r.low),
                        float(r.close),
                    )
                )
            except Exception:
                continue

        if not rows:
            return

        with sqlite3.connect(self.path) as con:
            con.executemany(
                "INSERT OR REPLACE INTO candles VALUES(?,?,?,?,?,?,?)",
                rows,
            )

    def read(self, symbol, timeframe, limit=None):
        if limit:
            query = """
                SELECT epoch, open, high, low, close
                FROM (
                    SELECT epoch, open, high, low, close
                    FROM candles
                    WHERE symbol=? AND timeframe=?
                    ORDER BY epoch DESC
                    LIMIT ?
                )
                ORDER BY epoch
            """
            params = [symbol, timeframe, int(limit)]
        else:
            query = """
                SELECT epoch, open, high, low, close
                FROM candles
                WHERE symbol=? AND timeframe=?
                ORDER BY epoch
            """
            params = [symbol, timeframe]

        with sqlite3.connect(self.path) as con:
            return pd.read_sql_query(query, con, params=params)

    def count(self, symbol, timeframe):
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=?",
                (symbol, timeframe),
            ).fetchone()

        return int(row[0]) if row else 0
