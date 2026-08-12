from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta
from typing import Any

from .inverter_service_core import (
    MADRID_TIME_ZONE,
    STATS_DB_PATH,
    combined_32bit_counter_value,
    stats_lock,
)


CHART_HISTORY_REGISTERS = (449, 451, 453, 455)
CHART_HISTORY_RAW_RETENTION_SECONDS = 48 * 60 * 60
CHART_HISTORY_AGGREGATE_RETENTION_SECONDS = 90 * 24 * 60 * 60
CHART_HISTORY_AGGREGATE_SECONDS = 5 * 60
chart_history_error = ""
chart_history_last_cleanup_monotonic = 0.0


def initialise_chart_history() -> None:
    with closing(sqlite3.connect(STATS_DB_PATH)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS chart_history_raw (
                timestamp INTEGER NOT NULL,
                register INTEGER NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (timestamp, register)
            );
            CREATE TABLE IF NOT EXISTS chart_history_5m (
                bucket INTEGER NOT NULL,
                register INTEGER NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (bucket, register)
            );
            CREATE TABLE IF NOT EXISTS chart_history_daily (
                day TEXT NOT NULL,
                register INTEGER NOT NULL,
                value REAL NOT NULL,
                PRIMARY KEY (day, register)
            );
            """
        )
        connection.commit()


def record_chart_history(fresh_values: dict[int, int]) -> None:
    global chart_history_error, chart_history_last_cleanup_monotonic
    readings = []
    for register in CHART_HISTORY_REGISTERS:
        value = combined_32bit_counter_value(register, fresh_values)
        if value is not None:
            readings.append((register, float(value)))
    if not readings:
        return
    now = int(time.time())
    bucket = now - now % CHART_HISTORY_AGGREGATE_SECONDS
    day = datetime.now(MADRID_TIME_ZONE).date().isoformat()
    try:
        with stats_lock, closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO chart_history_raw (timestamp, register, value) VALUES (?, ?, ?)",
                [(now, register, value) for register, value in readings],
            )
            for table, key, key_value in (("chart_history_5m", "bucket", bucket), ("chart_history_daily", "day", day)):
                connection.executemany(
                    f"INSERT INTO {table} ({key}, register, value) VALUES (?, ?, ?) "
                    f"ON CONFLICT({key}, register) DO UPDATE SET value = excluded.value",
                    [(key_value, register, value) for register, value in readings],
                )
            if time.monotonic() - chart_history_last_cleanup_monotonic >= 300:
                connection.execute("DELETE FROM chart_history_raw WHERE timestamp < ?", (now - CHART_HISTORY_RAW_RETENTION_SECONDS,))
                connection.execute("DELETE FROM chart_history_5m WHERE bucket < ?", (now - CHART_HISTORY_AGGREGATE_RETENTION_SECONDS,))
                chart_history_last_cleanup_monotonic = time.monotonic()
            connection.commit()
        chart_history_error = ""
    except (OSError, sqlite3.Error) as error:
        chart_history_error = str(error)


def get_chart_history(period: str) -> dict[str, Any]:
    global chart_history_error
    period = period if period in {"realtime", "day", "month", "year", "lifetime"} else "realtime"
    if period in {"realtime", "day"}:
        window_seconds = 120 if period == "realtime" else 24 * 60 * 60
        table, column, minimum, timestamp = "chart_history_raw", "timestamp", int(time.time()) - window_seconds, "timestamp * 1000"
    elif period == "month":
        table, column, minimum, timestamp = "chart_history_5m", "bucket", int(time.time()) - 30 * 24 * 60 * 60, "bucket * 1000"
    else:
        minimum = (datetime.now(MADRID_TIME_ZONE).date() - timedelta(days=365)).isoformat() if period == "year" else "0000-01-01"
        table, column, timestamp = "chart_history_daily", "day", "strftime('%s', day || 'T00:00:00') * 1000"
    try:
        with stats_lock, closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            rows = connection.execute(
                f"SELECT {timestamp}, register, value FROM {table} WHERE {column} >= ? ORDER BY {column}, register",
                (minimum,),
            ).fetchall()
        points: dict[int, dict[str, float | int]] = {}
        for timestamp_value, register, value in rows:
            points.setdefault(int(timestamp_value), {"time": int(timestamp_value)})[str(register)] = float(value)
        return {"period": period, "points": list(points.values()), "error": chart_history_error}
    except (OSError, sqlite3.Error) as error:
        chart_history_error = str(error)
        return {"period": period, "points": [], "error": chart_history_error}
