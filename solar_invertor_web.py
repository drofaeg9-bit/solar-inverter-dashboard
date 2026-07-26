#!/usr/bin/env python3
"""
Direct terminal dashboard for the converter.

Controls:
  q          Quit
  r          Cycle polling rate: 0.5 / 1 / 2 / 5 / 10 seconds
  m          Toggle read mode: fast / compatible
  ↑ / ↓      Scroll register list
  PgUp/PgDn  Scroll faster
  Home/End   Jump to top/bottom

Requirements:
  - Python 3
  - mbpoll
  - /dev/ttyUSB0
  - user in dialout group
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from datetime import datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TextIO
from zoneinfo import ZoneInfo

DEVICE = "/dev/ttyUSB0"
SLAVE_ID = 1
BAUD_RATE = 9600
COMMAND_TIMEOUT_SECONDS = 3.0
MADRID_TIME_ZONE = ZoneInfo("Europe/Madrid")
FAVICON_PATH = Path(__file__).with_name("favicon.png")
_stats_path_setting = os.environ.get("INVERTER_STATS_DB")
_new_stats_path = Path(__file__).with_name("solar_invertor_web_stats.sqlite3")
_legacy_stats_path = Path(__file__).with_name("inverter_stats.sqlite3")
STATS_DB_PATH = (
    Path(_stats_path_setting)
    if _stats_path_setting
    else _legacy_stats_path
    if _legacy_stats_path.exists() and not _new_stats_path.exists()
    else _new_stats_path
)
stats_lock = threading.Lock()
stats_error = ""
site_visit_total = 0
COUNTED_VISITOR_COOKIE = "inverter_counted"
REGISTER_LOG_DIRECTORY = Path(__file__).with_name("register_logs")

register_log_lock = threading.Lock()
register_log_file: TextIO | None = None
register_log_writer: Any = None
register_log_path: Path | None = None
register_log_started_at = ""
register_log_changes = 0
register_log_error = ""
register_log_previous_values: dict[int, int] = {}

POLL_RATES = [0.5, 1.0, 2.0, 5.0, 10.0]

KNOWN_REGISTERS = [
    1, 2, 3, 4, 5, 6, 7, 8, 9,
    17, 18, 27, 28, 58,
    65, 66, 67, 68, 69,
    89, 90, 91, 92, 93, 94,
    129, 130, 133, 134,
    137, 138, 139, 140, 141, 142, 143, 144,
    157, 158,
    321, 324, 325, 337, 339,
    341, 342, 343, 344, 345, 346, 349, 350,
    376, 377, 378, 379, 383, 385, 386,
    401, 402, 403, 404, 405, 406, 407, 408,
    409, 410, 411, 412, 413, 415, 416, 417,
    449, 451, 453, 455,
]

FAST_BLOCKS = [
    (1, 18),
    (27, 2),
    (58, 1),
    (65, 5),
    (89, 6),
    (129, 30),
    (321, 30),
    (376, 11),
    (401, 17),
    (449, 7),
]

# Register metadata is based on observed values. Conservative names such as
# "channel" and "parameter" indicate meanings not confirmed by a vendor map.
# name, scale, unit, signed, group
REGISTER_CONFIG: dict[int, tuple[str, float, str, bool, str]] = {
    **{
        register: (
            f"Ідентифікатор пристрою, слово {register}",
            1.0,
            "",
            False,
            "Ідентифікація",
        )
        for register in range(1, 10)
    },
    17: ("Код протоколу або версії", 1.0, "", False, "Система"),
    18: ("Код конфігурації пристрою", 1.0, "", False, "Система"),
    27: ("Системне слово 27", 1.0, "", False, "Система"),
    28: ("Системний прапорець 28", 1.0, "", False, "Система"),
    58: ("Бітова маска можливостей або стану", 1.0, "", False, "Система"),
    65: ("Системне слово 65", 1.0, "", False, "Система"),
    66: ("Код конфігурації 66", 1.0, "", False, "Система"),
    67: ("Код конфігурації 67", 1.0, "", False, "Система"),
    68: ("Системне значення 68", 1.0, "", False, "Система"),
    69: ("Упаковане знакове значення 69", 1.0, "", True, "Система"),

    89: ("Напруга AC", 0.1, "V", False, "AC"),
    90: ("Параметр AC 90", 1.0, "", False, "AC"),
    91: ("Частота AC", 0.01, "Hz", False, "AC"),
    92: ("Температурний канал інвертора", 0.1, "°C", False, "Температура"),
    93: ("Канал напруги 93", 0.1, "V", False, "Система"),
    94: ("Відсотковий параметр 94", 1.0, "%", False, "Система"),

    129: ("Напруга батареї, канал 129", 0.1, "V", False, "Батарея"),
    130: ("Струм батареї без знаку", 0.1, "A", False, "Батарея"),
    133: ("Рівень заряду батареї", 1.0, "%", False, "Батарея"),
    134: ("Температура батареї, канал 134", 0.1, "°C", False, "Температура"),

    137: ("Напруга батареї BMS", 0.1, "V", False, "BMS"),
    138: ("Струм батареї BMS", 0.1, "A", True, "BMS"),
    139: ("Рівень заряду батареї BMS", 1.0, "%", False, "BMS"),
    140: ("Температура BMS, канал 140", 0.1, "°C", False, "Температура"),
    141: ("Верхня напруга заряджання BMS", 0.1, "V", False, "BMS"),
    142: ("Недоступний параметр BMS 142", 1.0, "", True, "BMS"),
    143: ("Недоступний параметр BMS 143", 1.0, "", True, "BMS"),
    144: ("Параметр BMS 144", 1.0, "", False, "BMS"),

    157: ("Код робочого стану", 1.0, "", False, "Система"),
    158: ("Системний параметр стану 158", 1.0, "", False, "Система"),

    321: ("Прапорець каналу BMS", 1.0, "", False, "BMS"),
    324: ("Код конфігурації BMS 324", 1.0, "", False, "BMS"),
    325: ("Код конфігурації BMS 325", 1.0, "", False, "BMS"),
    337: ("Код стану BMS 337", 1.0, "", False, "BMS"),
    339: ("Рівень заряду батареї BMS", 1.0, "%", False, "BMS"),
    341: ("Канал напруги 341, ймовірно PV", 0.01, "V", False, "PV"),
    342: ("Напруга батареї BMS, канал 342", 0.1, "V", False, "BMS"),
    343: ("Струм BMS, канал 343", 0.1, "A", True, "BMS"),
    344: ("Струм батареї BMS, канал 344", 0.1, "A", True, "BMS"),
    345: ("Верхня межа напруги BMS", 0.1, "V", False, "BMS"),
    346: ("Нижня межа напруги BMS 1", 0.1, "V", False, "BMS"),
    349: ("Нижня межа напруги BMS 2", 0.1, "V", False, "BMS"),
    350: ("Знаковий струмовий параметр BMS", 0.1, "A", True, "BMS"),

    376: ("Напруга заряджання, налаштування 376", 0.1, "V", False, "Налаштування"),
    377: ("Напруга заряджання, налаштування 377", 0.1, "V", False, "Налаштування"),
    378: ("Ліміт струму 378", 0.1, "A", False, "Налаштування"),
    379: ("Ліміт струму 379", 0.1, "A", False, "Налаштування"),
    383: ("Верхня напруга батареї, налаштування 383", 0.1, "V", False, "Налаштування"),
    385: ("Параметр потужності 385", 1.0, "W", False, "Потужність"),
    386: ("Параметр потужності 386", 1.0, "W", False, "Потужність"),

    401: ("Код BMS або стану 401", 1.0, "", False, "BMS"),
    402: ("Прапорець BMS або стану 402", 1.0, "", False, "BMS"),
    403: ("Упакований параметр BMS 403", 1.0, "", False, "BMS"),
    404: ("Напруга батареї BMS, канал 404", 0.1, "V", False, "BMS"),
    405: ("Струм батареї BMS, канал 405", 0.1, "A", True, "BMS"),
    406: ("Температура BMS, канал 406", 0.1, "°C", False, "Температура"),
    407: ("Рівень заряду батареї BMS", 1.0, "%", False, "BMS"),
    408: ("Відсотковий параметр BMS, можливо SOH", 1.0, "%", False, "BMS"),
    409: ("Недоступний параметр BMS 409", 1.0, "", True, "BMS"),
    410: ("Недоступний параметр BMS 410", 1.0, "", True, "BMS"),
    411: ("Верхня напруга заряджання BMS", 0.1, "V", False, "BMS"),
    412: ("Ліміт струму BMS", 0.1, "A", False, "BMS"),
    413: ("Параметр потужності BMS 413", 1.0, "W", False, "Потужність"),
    415: ("Параметр налаштування 415", 1.0, "", False, "Налаштування"),
    416: ("Параметр налаштування 416", 1.0, "", False, "Налаштування"),
    417: ("Параметр налаштування 417", 1.0, "", False, "Налаштування"),

    449: ("Параметр системи 449", 1.0, "", False, "Система"),
    451: ("Упаковане значення 451", 1.0, "", False, "Система"),
    453: ("Упаковане значення 453", 1.0, "", False, "Система"),
    455: ("Упаковане знакове значення 455", 1.0, "", True, "Система"),
}

METER_DEFINITIONS = [
    (89, [], "Напруга AC", 0.0, 300.0, "V"),
    (91, [], "Частота AC", 45.0, 55.0, "Hz"),
    (92, [], "Температура інвертора", -20.0, 120.0, "°C"),
    (341, [], "Напруга каналу 341", 0.0, 600.0, "V"),
    (137, [404, 342, 129], "Напруга батареї", 40.0, 65.0, "V"),
    (138, [405, 344], "Струм батареї", -150.0, 150.0, "A"),
    (130, [], "Струм батареї без знаку", 0.0, 150.0, "A"),
    (139, [407, 339, 133], "Рівень заряду батареї", 0.0, 100.0, "%"),
    (140, [406], "Температура BMS", -20.0, 100.0, "°C"),
    (134, [], "Температура батареї", -20.0, 100.0, "°C"),
    (408, [], "Відсотковий параметр BMS", 0.0, 100.0, "%"),
    (141, [411, 376, 377], "Напруга заряджання / ліміт", 40.0, 65.0, "V"),
    (343, [], "Струм BMS, канал 343", -150.0, 150.0, "A"),
    (412, [378, 379], "Ліміт струму BMS", 0.0, 150.0, "A"),
    (350, [], "Знаковий струмовий параметр", -200.0, 200.0, "A"),
    (413, [], "Параметр потужності 413", 0.0, 15000.0, "W"),
    (385, [], "Параметр потужності 385", 0.0, 15000.0, "W"),
    (386, [], "Параметр потужності 386", 0.0, 15000.0, "W"),
]


# Fault and alarm meanings from the supplied inverter manual.
FAULT_CODES = {
    1: "Помилка підвищення напруги шини",
    2: "Перенапруга шини",
    3: "Знижена напруга шини",
    4: "Надструм батареї",
    5: "Перегрів системи",
    6: "Перенапруга батареї",
    7: "Помилка плавного запуску шини",
    8: "Коротке замикання шини",
    9: "Помилка плавного запуску інвертора",
    11: "Знижена напруга інвертора",
    12: "Коротке замикання інвертора",
    13: "Від’ємна потужність інвертора",
    14: "Перевантаження",
    17: "Оновлення програми",
    18: "Зворотна полярність PV",
    26: "Помилка BMS",
    29: "Ненормальне навантаження інвертора",
}

ALARM_CODES = {
    50: "Батарею відключено",
    51: "Знижена напруга батареї",
    52: "Низька напруга батареї",
    53: "Коротке замикання під час заряджання батареї",
    56: "Втрачено зв’язок із BMS",
    58: "Помилка вентилятора",
    59: "Помилка EEPROM",
    60: "Перевантаження",
    62: "Недостатньо енергії PV",
    68: "Відключення через низький SOC",
    69: "Попередження про низький SOC",
    72: "Батарея не може запуститися",
    77: "Нестабільна мережа",
    78: "Втрачено зв’язок із лічильником",
}

OPERATING_STATUS = {
    0: "Очікування або невідомий стан",
    1: "Ймовірно робота від мережі або байпас",
    2: "Ймовірно робота інвертора від батареї або PV",
    3: "Ймовірно заряджання або активна робота",
    4: "Ймовірно помилка або аварійний стан",
}

VALUE_PATTERN = re.compile(r"\[(\d+)\]:\s*(-?\d+)")

state_lock = threading.Lock()
poll_wake_event = threading.Event()
state: dict[str, Any] = {
    "online": False,
    "updated_at": "ніколи",
    "cycle_seconds": 0.0,
    "cycle_id": 0,
    "poll_rate_index": 2,
    "read_mode": "fast",
    "requests": 0,
    "successful": 0,
    "ошибок": 0,
    "error": "",
    "identifier": "",
    "values": {},
    "paused": False,
    "stop": False,
}


def signed16(raw: int) -> int:
    return raw - 65536 if raw >= 32768 else raw


def normalize(register: int, raw: int) -> tuple[str, str, str, float | None, str]:
    if raw == 0xFFFF:
        name, _, _, _, group = REGISTER_CONFIG.get(
            register, (f"Регістр {register}", 1.0, "", False, "Сире")
        )
        return name, "Н/Д", "", None, group

    if register == 157:
        label = OPERATING_STATUS.get(raw, f"Код робочого стану {raw}")
        return "Робочий стан", label, "", float(raw), "Система"

    name, scale, unit, use_signed, group = REGISTER_CONFIG.get(
        register, (f"Регістр {register}", 1.0, "", False, "Сире")
    )

    base = signed16(raw) if use_signed else raw
    value = base * scale

    if scale == 1.0:
        display = str(int(value))
    elif scale == 0.1:
        display = f"{value:.1f}"
    elif scale == 0.01:
        display = f"{value:.2f}"
    else:
        display = f"{value:.3f}".rstrip("0").rstrip(".")

    return name, display, unit, value, group


def decode_identifier(values: dict[int, int]) -> str:
    data = bytearray()

    for register in range(1, 10):
        if register not in values:
            continue
        value = values[register] & 0xFFFF
        data.append((value >> 8) & 0xFF)
        data.append(value & 0xFF)

    return data.rstrip(b"\x00").decode("ascii", errors="replace")


def run_mbpoll(start: int, count: int) -> tuple[dict[int, int], str | None]:
    command = [
        "mbpoll",
        "-m", "rtu",
        "-b", str(BAUD_RATE),
        "-P", "none",
        "-t", "4",
        "-a", str(SLAVE_ID),
        "-r", str(start),
        "-c", str(count),
        "-1",
        "-q",
        DEVICE,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {}, "перевищено час очікування"
    except FileNotFoundError:
        return {}, "mbpoll не знайдено"
    except Exception as error:
        return {}, str(error)

    output = f"{result.stdout}\n{result.stderr}"
    values = {
        int(match.group(1)): int(match.group(2))
        for match in VALUE_PATTERN.finditer(output)
    }

    if values:
        return values, None

    return {}, output.strip() or "помилка читання"


def read_fast() -> tuple[dict[int, int], int, int, str | None]:
    values: dict[int, int] = {}
    failed = 0
    requests = 0
    last_error = None

    for start, count in FAST_BLOCKS:
        block_values, error = run_mbpoll(start, count)
        requests += 1

        if block_values:
            values.update(block_values)
            continue

        last_error = error

        for register in range(start, start + count):
            one, one_error = run_mbpoll(register, 1)
            requests += 1

            if one:
                values.update(one)
            else:
                failed += 1
                last_error = one_error

    return values, failed, requests, last_error


def read_compatible() -> tuple[dict[int, int], int, int, str | None]:
    values: dict[int, int] = {}
    failed = 0
    requests = 0
    last_error = None

    for register in KNOWN_REGISTERS:
        one, error = run_mbpoll(register, 1)
        requests += 1

        if one:
            values.update(one)
        else:
            failed += 1
            last_error = error

    return values, failed, requests, last_error


def register_log_status() -> dict[str, Any]:
    """Return the current register change-log state for the web dashboard."""
    with register_log_lock:
        path = register_log_path
        if path is None and REGISTER_LOG_DIRECTORY.exists():
            path = max(
                REGISTER_LOG_DIRECTORY.glob("register_changes_*.csv"),
                key=lambda candidate: candidate.stat().st_mtime,
                default=None,
            )
        size = path.stat().st_size if path is not None and path.exists() else 0
        return {
            "active": register_log_file is not None,
            "filename": path.name if path is not None else "",
            "started_at": register_log_started_at,
            "changes": register_log_changes,
            "size_bytes": size,
            "available": path is not None and path.exists(),
            "error": register_log_error,
        }


def start_register_log() -> dict[str, Any]:
    """Start a new CSV file containing initial and changed register values."""
    global register_log_file, register_log_writer, register_log_path
    global register_log_started_at, register_log_changes, register_log_error
    global register_log_previous_values

    with register_log_lock:
        if register_log_file is not None:
            return register_log_status_unlocked()
        try:
            REGISTER_LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
            now = datetime.now(MADRID_TIME_ZONE)
            path = REGISTER_LOG_DIRECTORY / (
                f"register_changes_{now.strftime('%Y%m%d_%H%M%S_%f')}.csv"
            )
            log_file = path.open("x", encoding="utf-8", newline="", buffering=1)
            writer = csv.writer(log_file)
            writer.writerow([
                "timestamp_madrid",
                "cycle",
                "event",
                "register",
                "group",
                "name",
                "previous_raw",
                "raw",
                "display",
                "unit",
                "note",
            ])
            register_log_file = log_file
            register_log_writer = writer
            register_log_path = path
            register_log_started_at = now.isoformat(timespec="seconds")
            register_log_changes = 0
            register_log_error = ""
            register_log_previous_values = {}
        except OSError as error:
            register_log_error = str(error)
        return register_log_status_unlocked()


def stop_register_log() -> dict[str, Any]:
    """Flush and close the active register change log."""
    global register_log_file, register_log_writer, register_log_error
    with register_log_lock:
        try:
            if register_log_file is not None:
                register_log_file.flush()
                register_log_file.close()
        except OSError as error:
            register_log_error = str(error)
        finally:
            register_log_file = None
            register_log_writer = None
        return register_log_status_unlocked()


def register_log_status_unlocked() -> dict[str, Any]:
    """Return log state while the caller holds ``register_log_lock``."""
    path = register_log_path
    size = path.stat().st_size if path is not None and path.exists() else 0
    return {
        "active": register_log_file is not None,
        "filename": path.name if path is not None else "",
        "started_at": register_log_started_at,
        "changes": register_log_changes,
        "size_bytes": size,
        "available": path is not None and path.exists(),
        "error": register_log_error,
    }


def record_register_changes(values: dict[int, int], cycle_id: int) -> None:
    """Append the initial snapshot or values changed since the prior poll."""
    global register_log_changes, register_log_error, register_log_previous_values
    with register_log_lock:
        if register_log_file is None or register_log_writer is None:
            return
        initial_snapshot = not register_log_previous_values
        timestamp = datetime.now(MADRID_TIME_ZONE).isoformat(timespec="milliseconds")
        try:
            for register, raw in sorted(values.items()):
                previous_raw = register_log_previous_values.get(register)
                if not initial_snapshot and previous_raw == raw:
                    continue
                name, display, unit, _, group = normalize(register, raw)
                register_log_writer.writerow([
                    timestamp,
                    cycle_id,
                    "INITIAL" if initial_snapshot else "CHANGE",
                    register,
                    group,
                    name,
                    "" if previous_raw is None else previous_raw,
                    raw,
                    display,
                    unit,
                    "",
                ])
                register_log_changes += 1
            register_log_file.flush()
            register_log_previous_values = dict(values)
            register_log_error = ""
        except OSError as error:
            register_log_error = str(error)


def record_register_log_note(note: str, cycle_id: int) -> dict[str, Any]:
    """Add a user-supplied experiment marker to the active CSV log."""
    global register_log_changes, register_log_error
    clean_note = " ".join(note.strip().split())
    if not clean_note:
        raise ValueError("нотатка не може бути порожньою")
    if len(clean_note) > 500:
        raise ValueError("нотатка не може перевищувати 500 символів")
    with register_log_lock:
        if register_log_file is None or register_log_writer is None:
            raise ValueError("спочатку запустіть запис журналу")
        try:
            register_log_writer.writerow([
                datetime.now(MADRID_TIME_ZONE).isoformat(timespec="milliseconds"),
                cycle_id,
                "NOTE",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                clean_note,
            ])
            register_log_file.flush()
            register_log_changes += 1
            register_log_error = ""
        except OSError as error:
            register_log_error = str(error)
        return register_log_status_unlocked()


def poll_worker() -> None:
    cached: dict[int, int] = {}

    while True:
        with state_lock:
            if state["stop"]:
                return
            paused = state["paused"]
            mode = state["read_mode"]
            poll_rate = POLL_RATES[state["poll_rate_index"]]

        if paused:
            poll_wake_event.wait()
            poll_wake_event.clear()
            continue

        started = time.monotonic()

        if mode == "compatible":
            fresh, failed, requests, error = read_compatible()
        else:
            fresh, failed, requests, error = read_fast()

        if fresh:
            cached.update(fresh)

        duration = round(time.monotonic() - started, 2)

        with state_lock:
            state["online"] = bool(fresh)
            state["updated_at"] = datetime.now(MADRID_TIME_ZONE).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            state["cycle_seconds"] = duration
            state["cycle_id"] += 1
            state["requests"] = requests
            state["successful"] = len(fresh)
            state["ошибок"] = failed
            state["error"] = "" if fresh else (error or "помилка читання")
            state["identifier"] = decode_identifier(cached)
            state["values"] = dict(cached)
            log_cycle_id = int(state["cycle_id"])
            log_values = dict(cached)

            if state["stop"]:
                return

            poll_rate = POLL_RATES[state["poll_rate_index"]]

        record_register_changes(log_values, log_cycle_id)
        poll_wake_event.wait(max(0.0, poll_rate - duration))
        poll_wake_event.clear()


def safe_addstr(win: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = win.getmaxyx()

    if y < 0 or y >= height or x < 0 or x >= width:
        return

    max_length = width - x - 1

    if max_length <= 0:
        return

    try:
        win.addstr(y, x, text[:max_length], attr)
    except curses.error:
        pass


def bar(value: float | None, minimum: float, maximum: float, width: int = 24) -> str:
    if value is None:
        return "[" + ("?" * width) + "]"

    if maximum <= minimum:
        ratio = 0.0
    else:
        ratio = (value - minimum) / (maximum - minimum)

    ratio = max(0.0, min(1.0, ratio))
    filled = round(ratio * width)
    return "[" + ("█" * filled) + ("·" * (width - filled)) + "]"


def meter_value(values: dict[int, int], register: int, fallbacks: list[int]) -> tuple[float | None, str]:
    for candidate in [register, *fallbacks]:
        if candidate not in values:
            continue

        _, display, _, value, _ = normalize(candidate, values[candidate])

        if value is not None:
            return value, f"R{candidate} {display}"

    return None, "Н/Д"


def draw(stdscr: curses.window, scroll: int) -> int:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    with state_lock:
        snapshot = dict(state)
        values = dict(state["values"])

    online = snapshot["online"]
    status_attr = curses.color_pair(2) | curses.A_BOLD if online else curses.color_pair(1) | curses.A_BOLD

    safe_addstr(stdscr, 0, 0, "ТЕРМІНАЛЬНА ПАНЕЛЬ ІНВЕРТОРА", curses.A_BOLD)
    safe_addstr(stdscr, 1, 0, "Стан: ")
    safe_addstr(stdscr, 1, 6, "У МЕРЕЖІ" if online else "НЕМАЄ ЗВ’ЯЗКУ", status_attr)
    safe_addstr(
        stdscr,
        1,
        18,
        f"Пристрій: {snapshot['identifier'] or 'невідомо'}  Оновлено: {snapshot['updated_at']}",
    )
    safe_addstr(
        stdscr,
        2,
        0,
        f"Цикл: {snapshot['cycle_id']}  Читання: {snapshot['cycle_seconds']:.2f} с  "
        f"Інтервал: {POLL_RATES[snapshot['poll_rate_index']]:g} с  "
        f"Режим: {snapshot['read_mode']}  Запити: {snapshot['requests']}  "
        f"Зчитано: {snapshot['successful']} успішно / {snapshot['ошибок']} помилок",
    )
    status_code = values.get(157)
    status_text = OPERATING_STATUS.get(status_code, "") if status_code is not None else ""
    safe_addstr(
        stdscr,
        3,
        0,
        "Клавіші: q вихід | r інтервал | m режим | стрілки/PgUp/PgDn прокручування"
        + (f" | Стан: {status_text}" if status_text else ""),
        curses.A_DIM,
    )

    row = 5
    safe_addstr(stdscr, row, 0, "ПОТОЧНІ ПОКАЗНИКИ", curses.A_BOLD)
    row += 1

    meter_columns = 2 if width >= 90 else 1
    meter_width = max(38, width // meter_columns - 2)

    for index, (register, fallbacks, label, minimum, maximum, unit) in enumerate(METER_DEFINITIONS):
        value, source = meter_value(values, register, fallbacks)
        col = index % meter_columns
        line_group = index // meter_columns
        y = row + line_group * 3
        x = col * meter_width

        display = "Н/Д" if value is None else f"{value:.2f}".rstrip("0").rstrip(".")
        safe_addstr(stdscr, y, x, f"{label}: {display} {unit}", curses.A_BOLD)
        safe_addstr(stdscr, y + 1, x, bar(value, minimum, maximum, min(24, meter_width - 8)))
        safe_addstr(stdscr, y + 2, x, f"{minimum:g}..{maximum:g} | {source}", curses.A_DIM)

    row += ((len(METER_DEFINITIONS) + meter_columns - 1) // meter_columns) * 3 + 1
    safe_addstr(stdscr, row, 0, "НЕНУЛЬОВІ РЕГІСТРИ", curses.A_BOLD)
    row += 1

    entries = []
    for register, raw in sorted(values.items()):
        if raw == 0:
            continue
        name, display, unit, _, group = normalize(register, raw)
        entries.append((register, name, display, unit, raw, signed16(raw), group))

    available_rows = max(1, height - row - 1)
    max_scroll = max(0, len(entries) - available_rows)
    scroll = max(0, min(scroll, max_scroll))

    header = f"{'РЕГ':>4}  {'ГРУПА':<9} {'НАЗВА':<31} {'ЗНАЧЕННЯ':>12} {'СИРЕ':>7} {'ЗНАК.':>7}"
    safe_addstr(stdscr, row, 0, header, curses.A_UNDERLINE)
    row += 1

    for entry in entries[scroll:scroll + available_rows]:
        register, name, display, unit, raw, signed, group = entry
        value_text = f"{display} {unit}".strip()
        line = (
            f"{register:>4}  {group[:9]:<9} "
            f"{name[:31]:<31} {value_text:>12} {raw:>7} {signed:>7}"
        )
        safe_addstr(stdscr, row, 0, line)
        row += 1

    if snapshot["error"]:
        safe_addstr(stdscr, height - 1, 0, f"Помилка: {snapshot['error']}", curses.color_pair(1))

    stdscr.refresh()
    return scroll


def main(stdscr: curses.window) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    worker = threading.Thread(target=poll_worker, daemon=True)
    worker.start()

    scroll = 0

    try:
        while True:
            scroll = draw(stdscr, scroll)
            key = stdscr.getch()

            if key in (ord("q"), ord("Q")):
                break

            if key in (ord("r"), ord("R")):
                with state_lock:
                    state["poll_rate_index"] = (
                        state["poll_rate_index"] + 1
                    ) % len(POLL_RATES)

            elif key in (ord("m"), ord("M")):
                with state_lock:
                    state["read_mode"] = (
                        "compatible"
                        if state["read_mode"] == "fast"
                        else "fast"
                    )

            elif key == curses.KEY_UP:
                scroll = max(0, scroll - 1)
            elif key == curses.KEY_DOWN:
                scroll += 1
            elif key == curses.KEY_PPAGE:
                scroll = max(0, scroll - 10)
            elif key == curses.KEY_NPAGE:
                scroll += 10
            elif key == curses.KEY_HOME:
                scroll = 0
            elif key == curses.KEY_END:
                scroll = 10_000

            time.sleep(0.05)

    finally:
        with state_lock:
            state["stop"] = True


WEB_DASHBOARD = r"""<!doctype html>
<html lang="uk" class="booting">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <link rel="icon" type="image/png" sizes="any" href="/favicon.png">
  <title>Solar Invertor Web</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(15, 28, 46, .76);
      --line: rgba(148, 163, 184, .14);
      --text: #f1f5f9;
      --muted: #8ea0b8;
      --cyan: #22d3ee;
      --blue: #38bdf8;
      --green: #34d399;
      --amber: #fbbf24;
      --red: #fb7185;
      --control: rgba(10, 22, 37, .76);
      --card-start: rgba(21, 38, 59, .86);
      --card-end: rgba(9, 20, 34, .82);
      --table-head: #101f32;
      --gauge-track: rgba(148,163,184,.14);
      --gauge-tick: rgba(226,232,240,.42);
      --gauge-major: rgba(241,245,249,.82);
      --needle: #f8fafc;
      --chart-grid-line: rgba(148,163,184,.14);
    }
    :root[data-theme="light"] {
      color-scheme: light;
      --bg: #edf4f8;
      --panel: rgba(255, 255, 255, .82);
      --line: rgba(30, 64, 86, .16);
      --text: #102334;
      --muted: #5e7284;
      --control: rgba(255, 255, 255, .88);
      --card-start: rgba(255, 255, 255, .96);
      --card-end: rgba(240, 247, 250, .94);
      --table-head: #e7f0f5;
      --gauge-track: rgba(51, 78, 96, .14);
      --gauge-tick: rgba(51, 78, 96, .42);
      --gauge-major: rgba(15, 35, 50, .76);
      --needle: #102334;
      --chart-grid-line: rgba(51, 78, 96, .16);
    }
    * { box-sizing: border-box }
    html { min-width: 280px; overflow-x: hidden }
    html.booting body { visibility: hidden }
    [hidden] { display: none !important }
    body {
      margin: 0;
      min-height: 100vh;
      min-height: 100dvh;
      overflow-x: hidden;
      -webkit-text-size-adjust: 100%;
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      background:
        radial-gradient(circle at 15% -10%, rgba(14, 165, 233, .2), transparent 34rem),
        radial-gradient(circle at 95% 10%, rgba(52, 211, 153, .12), transparent 28rem),
        var(--bg);
    }
    body::before {
      content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .16;
      background-image: linear-gradient(var(--line) 1px, transparent 1px),
                        linear-gradient(90deg, var(--line) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 75%);
    }
    :root[data-theme="light"] body {
      background:
        radial-gradient(circle at 15% -10%, rgba(14, 165, 233, .15), transparent 34rem),
        radial-gradient(circle at 95% 10%, rgba(52, 211, 153, .1), transparent 28rem),
        var(--bg);
    }
    .shell {
      width: min(1440px, calc(100% - 32px));
      margin: auto;
      padding: max(18px, env(safe-area-inset-top)) 0 max(44px, env(safe-area-inset-bottom));
    }
    header, .panel {
      border: 1px solid var(--line);
      background: var(--panel);
      backdrop-filter: blur(18px);
      box-shadow: 0 18px 55px rgba(0, 0, 0, .28);
    }
    header {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      padding: 18px 22px; border-radius: 20px; margin-bottom: 18px;
    }
    .brand { display: flex; align-items: center; gap: 14px; min-width: 0 }
    .brand > div:last-child { min-width: 0 }
    .logo {
      width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px;
      color: #06131c; font-size: 24px; background: linear-gradient(135deg, var(--amber), #fb923c);
      box-shadow: 0 0 28px rgba(251, 191, 36, .25);
    }
    h1 { margin: 0; font-size: clamp(18px, 2.5vw, 25px); letter-spacing: -.03em }
    .subtitle, .muted { color: var(--muted) }
    .subtitle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
    .status { display: flex; align-items: center; gap: 9px; font-weight: 700 }
    .header-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 10px }
    .theme-switch { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; cursor: pointer; user-select: none }
    .theme-switch input { position: absolute; opacity: 0; pointer-events: none }
    .theme-slider {
      position: relative; width: 42px; height: 23px; border-radius: 999px;
      border: 1px solid var(--line); background: var(--control); transition: background .25s ease;
    }
    .theme-slider::after {
      content: "☾"; position: absolute; display: grid; place-items: center;
      width: 19px; height: 19px; left: 1px; top: 1px; border-radius: 50%;
      color: #fff; font-size: 12px; background: #475569; transition: transform .25s ease, background .25s ease;
    }
    .theme-switch input:checked + .theme-slider { background: rgba(251,191,36,.22) }
    .theme-switch input:checked + .theme-slider::after {
      content: "☀"; transform: translateX(19px); color: #412b00; background: var(--amber);
    }
    .theme-switch input:focus-visible + .theme-slider { outline: 3px solid rgba(56,189,248,.25); outline-offset: 2px }
    .language-switch {
      display: flex; align-items: center; gap: 3px; padding: 3px;
      min-height: 40px; border: 1px solid var(--line); border-radius: 12px;
      background: var(--control);
    }
    .language-option {
      min-width: 38px; min-height: 32px; padding: 0 8px; border: 0; border-radius: 9px;
      color: var(--muted); background: transparent; font-size: 11px; font-weight: 800;
    }
    .language-option.active {
      color: #06202a; background: var(--cyan); box-shadow: 0 3px 12px rgba(34,211,238,.22);
    }
    .view-tabs { display: flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 12px; background: var(--control) }
    .view-tab { min-height: 32px; padding: 0 10px; border: 0; border-radius: 9px; color: var(--muted); background: transparent; font-size: 12px; font-weight: 750 }
    .view-tab.active { color: #06202a; background: var(--cyan); box-shadow: 0 3px 12px rgba(34,211,238,.2) }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--red); box-shadow: 0 0 14px var(--red) }
    .online .dot { background: var(--green); box-shadow: 0 0 14px var(--green) }
    .paused .dot { background: var(--amber); box-shadow: 0 0 14px var(--amber) }
    #app-toggle {
      border-color: rgba(251,113,133,.4);
      background: rgba(127,29,29,.18);
      font-weight: 750;
    }
    #app-toggle.start {
      border-color: rgba(52,211,153,.4);
      background: rgba(16,185,129,.16);
    }
    .toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 18px }
    .chip, select, button, input {
      min-height: 40px; border: 1px solid var(--line); border-radius: 12px;
      background: var(--control); color: var(--text); padding: 0 13px;
      font: inherit;
    }
    .chip { display: flex; align-items: center }
    select, button { cursor: pointer }
    @media (hover: hover) {
      button:hover, select:hover { border-color: rgba(56, 189, 248, .55) }
    }
    button:focus-visible, select:focus-visible, input:focus-visible {
      outline: 3px solid rgba(56,189,248,.25);
      outline-offset: 2px;
    }
    button:disabled { cursor: wait; opacity: .65 }
    #demo-button {
      border-color: rgba(52, 211, 153, .35);
      background: linear-gradient(135deg, rgba(16,185,129,.18), rgba(14,165,233,.14));
      font-weight: 750;
    }
    #chart-demo-button {
      border-color: rgba(167,139,250,.4);
      background: linear-gradient(135deg, rgba(139,92,246,.2), rgba(14,165,233,.12));
      font-weight: 750;
    }
    .updated { margin-left: auto }
    .gauges {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px;
      margin-bottom: 18px;
    }
    .gauge-card {
      position: relative; min-width: 0; overflow: hidden; padding: 16px 16px 14px;
      border: 1px solid var(--line); border-radius: 18px;
      background: linear-gradient(145deg, var(--card-start), var(--card-end));
      box-shadow: inset 0 1px rgba(255,255,255,.035), 0 14px 34px rgba(0,0,0,.2);
    }
    .gauge-card[draggable="true"] { cursor: grab }
    .gauge-card[draggable="true"]:active { cursor: grabbing }
    .gauge-card.dragging { opacity: .38; transform: scale(.98) }
    .gauge-card.drag-target { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(34,211,238,.14) }
    .gauge-card::after {
      content: ""; position: absolute; width: 120px; height: 120px; right: -55px; top: -60px;
      border-radius: 50%; background: var(--accent); opacity: .08; filter: blur(12px);
    }
    .gauge-title { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 62px }
    .gauge-actions { position: absolute; z-index: 2; right: 8px; top: 7px; display: flex; align-items: center; gap: 1px }
    .drag-handle, .gauge-actions .remove-value {
      position: static; width: 27px; min-height: 27px; padding: 0; border: 0;
      background: transparent; color: var(--muted); font-size: 18px; line-height: 1;
    }
    .drag-handle { cursor: grab; font-size: 17px; touch-action: none; user-select: none; -webkit-user-select: none }
    .drag-handle:active { cursor: grabbing }
    .gauge-card.pointer-dragging { opacity: .55; transform: scale(.98); z-index: 3 }
    .gauges.empty-dashboard { grid-template-columns: minmax(220px, 330px); justify-content: center }
    .add-gauge-card {
      display: grid; place-items: center; align-content: center; gap: 8px; min-height: 245px;
      padding: 24px; border: 1px dashed rgba(56,189,248,.42); border-radius: 18px;
      background: linear-gradient(145deg, rgba(56,189,248,.08), rgba(34,211,238,.035));
      color: var(--muted); text-align: center; cursor: pointer;
    }
    .add-gauge-card:hover { border-color: var(--cyan); color: var(--text); background: rgba(56,189,248,.12) }
    .add-gauge-plus { color: var(--cyan); font-size: 54px; font-weight: 300; line-height: .9 }
    .add-gauge-label { font-size: 13px; font-weight: 700 }
    dialog.gauge-picker {
      width: min(620px, calc(100vw - 24px)); max-height: min(760px, calc(100vh - 24px));
      padding: 0; overflow: hidden; color: var(--text); border: 1px solid var(--line);
      border-radius: 20px; background: var(--panel); box-shadow: 0 28px 90px rgba(0,0,0,.55);
    }
    dialog.gauge-picker::backdrop { background: rgba(2,6,23,.72); backdrop-filter: blur(5px) }
    .gauge-picker-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; padding: 18px 18px 12px }
    .gauge-picker-head h2 { margin-bottom: 5px }
    .gauge-picker-close { width: 36px; min-height: 36px; padding: 0; font-size: 22px }
    .gauge-picker-search { width: calc(100% - 36px); margin: 0 18px 12px }
    .gauge-picker-list { max-height: min(590px, calc(100vh - 190px)); overflow-y: auto; padding: 0 18px 18px }
    .gauge-picker-option { display: flex; align-items: center; gap: 11px; padding: 11px 5px; border-bottom: 1px solid var(--line); cursor: pointer }
    .gauge-picker-option:hover { background: rgba(56,189,248,.05) }
    .gauge-picker-option input { flex: 0 0 auto; width: 18px; min-height: 18px; margin: 0; accent-color: var(--cyan) }
    .gauge-picker-name { min-width: 0; font-weight: 700 }
    .gauge-picker-name small { display: block; margin-top: 3px; color: var(--muted); font-weight: 400 }
    svg { display: block; width: 100%; max-height: 150px; margin-top: 3px; overflow: visible }
    .track { fill: none; stroke: var(--gauge-track); stroke-width: 13; stroke-linecap: round }
    .progress {
      fill: none; stroke: var(--accent); stroke-width: 13; stroke-linecap: round;
      stroke-dasharray: 283; stroke-dashoffset: 283;
      transition: stroke-dashoffset .7s ease;
    }
    .needle {
      stroke: var(--needle); stroke-width: 3.5; stroke-linecap: round;
      transform-origin: 120px 120px; transform: rotate(-90deg);
      transition: transform .75s cubic-bezier(.2,.8,.2,1);
    }
    .hub { fill: var(--accent); stroke: #e2e8f0; stroke-width: 2 }
    .tick { stroke: var(--gauge-tick); stroke-width: 1.2 }
    .tick.major { stroke: var(--gauge-major); stroke-width: 2 }
    .scale-label {
      fill: var(--muted); font-size: 8px; font-weight: 700;
      text-anchor: middle; dominant-baseline: middle;
    }
    .reading { display: flex; justify-content: center; align-items: baseline; gap: 7px; margin-top: -13px }
    .value { font-size: 27px; font-weight: 800; letter-spacing: -.04em; font-variant-numeric: tabular-nums }
    .unit { color: var(--muted); font-weight: 700 }
    .trend { width: 15px; font-size: 15px; font-weight: 900 }
    .trend.up { color: var(--green) } .trend.down { color: var(--red) } .trend.flat { color: var(--muted) }
    .source { margin-top: 5px; color: var(--muted); text-align: center; font-size: 11px }
    .panel { padding: 18px; border-radius: 18px }
    .panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px }
    .register-logger { margin-bottom: 18px }
    .logger-layout { display: flex; align-items: center; justify-content: space-between; gap: 18px }
    .logger-copy { min-width: 0 }
    .logger-status { margin-top: 7px; color: var(--muted); overflow-wrap: anywhere }
    .logger-status.active { color: var(--green) }
    .logger-status.error-text { color: var(--red) }
    .logger-actions { display: flex; flex: 0 0 auto; flex-wrap: wrap; gap: 8px }
    .logger-note { width: min(300px, 100%); flex: 1 1 220px }
    .logger-actions button, .logger-download {
      display: inline-flex; align-items: center; justify-content: center; min-height: 40px;
      padding: 0 13px; border: 1px solid var(--line); border-radius: 12px;
      color: var(--text); background: var(--control); text-decoration: none; font: inherit;
    }
    #register-log-start { border-color: rgba(52,211,153,.4); background: rgba(16,185,129,.16) }
    #register-log-stop { border-color: rgba(251,113,133,.4); background: rgba(127,29,29,.18) }
    h2 { margin: 0; font-size: 16px }
    input { width: min(270px, 46vw); outline: none }
    input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(56,189,248,.12) }
    .table-wrap { overflow: auto; max-height: 430px; border-radius: 12px }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums }
    th { position: sticky; top: 0; z-index: 1; background: var(--table-head); color: var(--muted); text-align: left; font-size: 11px; letter-spacing: .08em; text-transform: uppercase }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line) }
    tbody tr:hover { background: rgba(56,189,248,.05) }
    tbody tr.unavailable { opacity: .48 }
    td:nth-child(1), td:nth-child(4), td:nth-child(5) { white-space: nowrap }
    .error { display: none; margin-bottom: 15px; color: #fecdd3; border-color: rgba(251,113,133,.35); background: rgba(127,29,29,.24) }
    .error.show { display: block }
    .lcd-panel { max-width: 1080px; margin: 0 auto }
    .lcd-screen {
      overflow: hidden; padding: clamp(16px, 3vw, 32px); border: 8px solid #263238;
      border-radius: 22px; color: #10241d; background: linear-gradient(145deg, #c9e3c4, #a9caa7);
      box-shadow: inset 0 0 35px rgba(24,54,40,.2), 0 22px 65px rgba(0,0,0,.35);
      font-family: "Courier New", ui-monospace, monospace; font-variant-numeric: tabular-nums;
    }
    .lcd-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding-bottom: 14px; border-bottom: 2px solid rgba(16,36,29,.25) }
    .lcd-head h2 { font: 900 clamp(18px,3vw,28px)/1.1 inherit; letter-spacing: .08em }
    .lcd-subtitle { margin-top: 4px; opacity: .68; font-size: 12px }
    .lcd-mode { padding: 5px 10px; border: 2px solid currentColor; border-radius: 6px; font-weight: 900; text-transform: uppercase }
    .lcd-flow { display: grid; grid-template-columns: minmax(0,1fr) auto minmax(0,1fr) auto minmax(0,1fr); align-items: center; gap: 9px; margin: 24px 0 }
    .lcd-node { min-width: 0; padding: 12px 8px; border: 2px solid rgba(16,36,29,.34); border-radius: 9px; text-align: center; opacity: .52 }
    .lcd-node.active { opacity: 1; border-color: currentColor; box-shadow: inset 0 0 0 2px rgba(16,36,29,.1) }
    .lcd-node-icon { display: block; font: 900 25px/1 system-ui; margin-bottom: 5px }
    .lcd-node-label { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 900; text-transform: uppercase }
    .lcd-node-value { display: block; margin-top: 3px; font-size: clamp(14px,2vw,20px); font-weight: 900 }
    .lcd-arrow { text-align: center; font-size: 25px; font-weight: 900; opacity: .35 }
    .lcd-arrow.active { opacity: 1; animation: lcd-pulse 1.2s ease-in-out infinite }
    .lcd-main { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; margin-bottom: 14px }
    .lcd-primary { padding: 15px; border: 2px solid rgba(16,36,29,.3); border-radius: 9px; text-align: center }
    .lcd-primary.active { border-color: currentColor; box-shadow: inset 0 0 0 2px rgba(16,36,29,.1) }
    .lcd-primary-label, .lcd-readout-label { display: block; font-size: 10px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; opacity: .7 }
    .lcd-primary-value { display: block; margin-top: 4px; font-size: clamp(26px,5vw,46px); font-weight: 900; letter-spacing: -.06em }
    .lcd-readouts { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 8px }
    .lcd-readout { min-width: 0; padding: 11px; border-top: 2px solid rgba(16,36,29,.28) }
    .lcd-readout-value { display: block; margin-top: 3px; overflow-wrap: anywhere; font-size: clamp(14px,2vw,20px); font-weight: 900 }
    .lcd-status-line { margin-top: 16px; padding-top: 13px; border-top: 2px solid rgba(16,36,29,.25); font-weight: 900 }
    .lcd-page-panel { margin-top: 17px; padding: 14px; border: 2px solid rgba(16,36,29,.35); border-radius: 9px; background: rgba(220,239,211,.22) }
    .lcd-page-head { display: flex; align-items: center; justify-content: space-between; gap: 12px }
    .lcd-page-code { padding: 2px 7px; border: 2px solid currentColor; border-radius: 5px; font-size: 18px; font-weight: 900 }
    .lcd-page-title { text-align: right; font-weight: 900; text-transform: uppercase }
    .lcd-page-values { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px; margin-top: 12px }
    .lcd-page-reading { padding-top: 9px; border-top: 2px solid rgba(16,36,29,.24) }
    .lcd-page-description { margin-top: 10px; min-height: 2.8em; font: 600 12px/1.4 system-ui,sans-serif; opacity: .75 }
    .lcd-controls-wrap { margin-top: 16px; padding-top: 16px; border-top: 2px solid rgba(16,36,29,.25) }
    .lcd-controls-title { font: 900 11px/1.2 system-ui,sans-serif; letter-spacing: .08em; text-transform: uppercase; opacity: .7 }
    .lcd-controls { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 9px; margin-top: 9px }
    .lcd-key { min-height: 48px; border: 3px solid #17231f; border-radius: 9px; color: #d4e8d0; background: #263731; box-shadow: inset 0 -4px rgba(0,0,0,.24), 0 3px 0 #101915; font: 900 13px/1 system-ui,sans-serif }
    .lcd-key:active { transform: translateY(2px); box-shadow: inset 0 -2px rgba(0,0,0,.2), 0 1px 0 #101915 }
    .lcd-controls-note { margin-top: 10px; font: 600 11px/1.4 system-ui,sans-serif; opacity: .68 }
    @keyframes lcd-pulse { 50% { transform: translateX(3px); opacity: .55 } }
    .charts-layout {
      display: grid; grid-template-columns: 290px minmax(0, 1fr); gap: 16px;
      align-items: start;
    }
    .chart-selector { position: sticky; top: 14px; max-height: calc(100vh - 28px) }
    .chart-selector input[type="search"] { width: 100%; margin: 14px 0 10px }
    .value-list { overflow-y: auto; max-height: calc(100vh - 185px); padding-right: 4px }
    .value-option {
      padding: 9px 5px; border-bottom: 1px solid var(--line);
    }
    .value-option:hover { background: rgba(56,189,248,.05) }
    .value-name { min-width: 0; font-weight: 650 }
    .value-name small { display: block; color: var(--muted); margin-top: 2px; font-weight: 400 }
    .value-targets { display: flex; gap: 12px; margin-top: 7px }
    .value-targets label { display: flex; align-items: center; gap: 5px; color: var(--muted); font-size: 11px; cursor: pointer }
    .value-targets input { width: 14px; min-height: 14px; margin: 0; accent-color: var(--cyan) }
    .custom-values { margin-bottom: 18px }
    .custom-value-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 12px }
    .custom-value-card {
      position: relative; min-width: 0; padding: 15px; border: 1px solid var(--line);
      border-radius: 16px; background: linear-gradient(145deg, var(--card-start), var(--card-end));
    }
    .custom-value-label { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 24px }
    .custom-value-reading { margin-top: 7px; font-size: 25px; font-weight: 800; font-variant-numeric: tabular-nums }
    .custom-value-detail { color: var(--muted); font-size: 11px; margin-top: 4px }
    .remove-value {
      position: absolute; right: 8px; top: 7px; width: 27px; min-height: 27px; padding: 0;
      border: 0; background: transparent; color: var(--muted); font-size: 18px;
    }
    .charts-main { min-width: 0 }
    .charts-head { margin-bottom: 14px }
    .chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px }
    .chart-card {
      min-width: 0; padding: 16px; border: 1px solid var(--line); border-radius: 18px;
      background: linear-gradient(145deg, var(--card-start), var(--card-end));
    }
    .chart-card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px }
    .chart-card h3 { margin: 0; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
    .chart-latest { color: var(--accent); font-size: 20px; font-weight: 800; white-space: nowrap }
    .chart-card canvas { display: block; width: 100%; max-width: 100%; height: 220px; margin-top: 8px }
    .chart-empty {
      display: grid; place-items: center; min-height: 340px; color: var(--muted);
      border: 1px dashed rgba(148,163,184,.22); border-radius: 18px; text-align: center; padding: 24px;
    }
    @media (max-width: 1120px) {
      .gauges, .custom-value-grid { grid-template-columns: repeat(3, minmax(0, 1fr)) }
      .charts-layout { grid-template-columns: 250px minmax(0, 1fr) }
      .chart-grid { grid-template-columns: 1fr }
    }
    @media (max-width: 900px) {
      .shell { width: min(100% - 24px, 1440px); padding-top: max(12px, env(safe-area-inset-top)) }
      header { align-items: flex-start; flex-direction: column; padding: 16px 18px }
      .brand, .header-actions { width: 100% }
      .header-actions { justify-content: flex-start }
      .status { margin-left: auto }
      .gauges, .custom-value-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) }
      .logger-layout { align-items: stretch; flex-direction: column }
      .logger-actions > * { flex: 1 1 140px }
      .charts-layout { grid-template-columns: 1fr }
      .chart-selector { position: static; max-height: none }
      .value-list { max-height: min(42vh, 360px) }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 16px, 1440px); padding-top: max(8px, env(safe-area-inset-top)) }
      header { gap: 14px; padding: 14px; border-radius: 16px; margin-bottom: 12px }
      .logo { width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; font-size: 21px }
      .header-actions {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        align-items: center;
        gap: 8px;
      }
      .header-actions button { width: 100%; min-width: 0; padding-inline: 8px }
      .view-tabs { grid-column: 1 / -1; width: 100% }
      .view-tab { flex: 1 1 0 }
      .theme-switch { min-height: 44px }
      .status { justify-self: end; margin-left: 0; min-height: 44px }
      .toolbar {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin-bottom: 12px;
      }
      .toolbar > * { width: 100%; min-width: 0; margin: 0 }
      .toolbar .chip { justify-content: space-between; padding-inline: 10px }
      .toolbar select { width: auto; min-width: 0; min-height: 36px; padding-inline: 7px }
      #demo-button, #manage-values-button, #updated { grid-column: 1 / -1 }
      .updated { margin-left: 0 }
      .gauges { gap: 8px; margin-bottom: 12px }
      .gauge-card { padding: 11px 8px 10px; border-radius: 15px }
      .gauge-title { font-size: 12px }
      .value { font-size: clamp(21px, 7vw, 26px) }
      .source { overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
      .panel { padding: 14px; border-radius: 16px }
      .panel-head { align-items: stretch; flex-direction: column }
      .panel-head input { width: 100% }
      .custom-values { margin-bottom: 12px }
      .custom-value-grid { gap: 8px }
      .custom-value-card { padding: 12px; border-radius: 14px }
      .custom-value-reading { font-size: 21px }
      .charts-head #chart-demo-button { width: 100% }
      .chart-grid { gap: 10px }
      .chart-card { padding: 12px 10px; border-radius: 15px }
      .chart-card-head { align-items: flex-start }
      .chart-latest { font-size: 17px }
      .chart-card canvas { height: 190px }
      .chart-empty { min-height: 220px }
      .lcd-screen { border-width: 5px; border-radius: 16px }
      .lcd-flow { gap: 5px }
      .lcd-node { padding: 9px 4px }
      .lcd-node-icon { font-size: 20px }
      .lcd-arrow { font-size: 18px }
      .lcd-main { grid-template-columns: 1fr }
      .lcd-readouts { grid-template-columns: repeat(2,minmax(0,1fr)) }
      .lcd-controls { grid-template-columns: repeat(2,minmax(0,1fr)) }
      .table-wrap { max-height: none; overflow: visible }
      table, tbody { display: block; width: 100% }
      thead { display: none }
      tbody { display: grid; gap: 8px }
      tbody tr {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 4px 12px;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--control);
      }
      tbody td { display: block; min-width: 0; padding: 0; border: 0 }
      tbody td:nth-child(1) { grid-column: 1; grid-row: 1; color: var(--muted); font-size: 11px }
      tbody td:nth-child(2), tbody td:nth-child(5) { display: none }
      tbody td:nth-child(3) {
        grid-column: 1 / -1; grid-row: 2;
        overflow-wrap: anywhere;
      }
      tbody td:nth-child(4) {
        grid-column: 2; grid-row: 1;
        justify-self: end; text-align: right; font-weight: 750;
      }
      input, select, button, .chip { min-height: 44px }
    }
    @media (max-width: 390px) {
      .header-actions { grid-template-columns: 1fr }
      .theme-switch, .status { justify-self: stretch }
      .status { justify-content: flex-start }
      .toolbar { grid-template-columns: 1fr }
      .toolbar > *, #demo-button, #manage-values-button, #cycle, #updated { grid-column: 1 }
      .gauges, .custom-value-grid { grid-template-columns: 1fr }
      .gauge-card svg { max-height: 135px }
      .chart-card-head { flex-direction: column; gap: 3px }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        transition-duration: .01ms !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
      }
    }
  </style>
</head>
<body>
  <script>
    // Fail-safe: never leave the interface hidden if later startup code fails.
    window.setTimeout(() => document.documentElement.classList.remove('booting'), 2000);
  </script>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="logo">☀</div>
        <div><h1>Solar Invertor Web</h1><div class="subtitle" id="identifier" data-i18n="waitingInverter">Очікування даних інвертора…</div></div>
      </div>
      <div class="header-actions">
        <label class="theme-switch">
          <input id="theme-toggle" type="checkbox" role="switch" aria-label="Увімкнути світлу тему" data-i18n-aria="themeAria">
          <span class="theme-slider" aria-hidden="true"></span>
          <span id="theme-name">Темна</span>
        </label>
        <div class="language-switch" role="group" aria-label="Мова інтерфейсу" data-i18n-aria="languageAria">
          <button class="language-option active" type="button" data-language="uk" aria-pressed="true">УКР</button>
          <button class="language-option" type="button" data-language="ru" aria-pressed="false">РУС</button>
          <button class="language-option" type="button" data-language="en" aria-pressed="false">ENG</button>
        </div>
        <button id="app-toggle" type="button">Зупинити моніторинг</button>
        <div class="view-tabs" role="tablist" aria-label="Розділи" data-i18n-aria="viewTabsAria">
          <button class="view-tab active" id="dashboard-tab" type="button" role="tab" data-view="dashboard" aria-selected="true" data-i18n="dashboardTab">Панель</button>
          <button class="view-tab" id="charts-tab" type="button" role="tab" data-view="charts" aria-selected="false" data-i18n="chartsTab">Графіки</button>
          <button class="view-tab" id="lcd-tab" type="button" role="tab" data-view="lcd" aria-selected="false" data-i18n="lcdTab">LCD</button>
        </div>
        <div class="status" id="status"><span class="dot"></span><span class="status-label">НЕМАЄ ЗВ’ЯЗКУ</span></div>
      </div>
    </header>

    <section id="dashboard-view">
    <div class="toolbar">
      <label class="chip"><span data-i18n="requestEvery">Запит кожні</span>&nbsp;
        <select id="poll-rate" aria-label="Інтервал опитування" data-i18n-aria="pollAria">
          <option value="0" data-i18n="interval05">0.5 с</option><option value="1" data-i18n="interval1">1 с</option>
          <option value="2" data-i18n="interval2">2 с</option><option value="3" data-i18n="interval5">5 с</option><option value="4" data-i18n="interval10">10 с</option>
        </select>
      </label>
      <label class="chip"><span data-i18n="readMode">Режим читання</span>&nbsp;
        <select id="read-mode" aria-label="Режим читання" data-i18n-aria="readModeAria">
          <option value="fast" data-i18n="fast">Швидкий</option><option value="compatible" data-i18n="compatible">Сумісний</option>
        </select>
      </label>
      <button id="demo-button" class="all-data-demo-button" type="button">Запустити реалістичне демо на 120 с</button>
      <button id="manage-values-button" type="button" data-i18n="addValues">＋ Додати індикатори</button>
      <span class="chip" id="cycle">Цикл —</span>
      <span class="chip" id="site-visits">Відвідувачі — · —</span>
      <span class="chip updated" id="updated">Ще не оновлено</span>
    </div>

    <div class="panel error" id="error"></div>
    <section class="gauges" id="gauges" aria-label="Індикатори інвертора" data-i18n-aria="gaugesAria"></section>

    <section class="panel register-logger">
      <div class="logger-layout">
        <div class="logger-copy">
          <h2 data-i18n="registerLogger">Журнал змін регістрів</h2>
          <div class="muted" data-i18n="registerLoggerHelp">Записує початковий знімок і лише змінені значення у CSV з часом Мадрида.</div>
          <div class="logger-status" id="register-log-status" aria-live="polite">Запис не запущено</div>
        </div>
        <div class="logger-actions">
          <input class="logger-note" id="register-log-note" type="text" maxlength="500" placeholder="Напр. панелі вимкнено" data-i18n-placeholder="registerLogNotePlaceholder" disabled>
          <button id="register-log-mark" type="button" data-i18n="markRegisterLog" disabled>＋ Додати позначку</button>
          <button id="register-log-start" type="button" data-i18n="startRegisterLog">● Почати запис</button>
          <button id="register-log-stop" type="button" data-i18n="stopRegisterLog" disabled>■ Зупинити</button>
          <a class="logger-download" id="register-log-download" href="/api/register-log/download" data-i18n="downloadRegisterLog" hidden>↓ Завантажити CSV</a>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div><h2 data-i18n="liveRegisters">Поточні регістри</h2><span class="muted" id="register-count"></span></div>
        <input id="search" type="search" placeholder="Пошук регістрів…" aria-label="Пошук регістрів" data-i18n-placeholder="searchRegisters" data-i18n-aria="searchRegisters">
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th data-i18n="register">Регістр</th><th data-i18n="group">Група</th><th data-i18n="name">Назва</th><th data-i18n="value">Значення</th><th data-i18n="raw">Сире</th></tr></thead>
          <tbody id="registers"></tbody>
        </table>
      </div>
    </section>
    </section>

    <section id="lcd-view" hidden>
      <div class="panel lcd-panel">
        <div class="lcd-screen">
          <div class="lcd-head">
            <div><h2 data-i18n="lcdTitle">LCD ІНВЕРТОРА</h2><div class="lcd-subtitle" data-i18n="lcdSubtitle">Поточні показники з Modbus</div></div>
            <span class="lcd-mode" id="lcd-mode">—</span>
          </div>
          <div class="lcd-flow">
            <div class="lcd-node" id="lcd-grid-node"><span class="lcd-node-icon">∿</span><span class="lcd-node-label" data-i18n="grid">Мережа</span><span class="lcd-node-value" id="lcd-grid">—</span></div>
            <div class="lcd-arrow" id="lcd-grid-arrow">→</div>
            <div class="lcd-node" id="lcd-inverter-node"><span class="lcd-node-icon">▣</span><span class="lcd-node-label" data-i18n="inverter">Інвертор</span><span class="lcd-node-value" id="lcd-power">—</span></div>
            <div class="lcd-arrow" id="lcd-load-arrow">→</div>
            <div class="lcd-node" id="lcd-load-node"><span class="lcd-node-icon">⌂</span><span class="lcd-node-label" data-i18n="load">Навантаження</span><span class="lcd-node-value" id="lcd-load">—</span></div>
          </div>
          <div class="lcd-main">
            <div class="lcd-primary" id="lcd-pv-card"><span class="lcd-primary-label" data-i18n="pvInput">Вхід PV</span><span class="lcd-primary-value" id="lcd-pv">—</span></div>
            <div class="lcd-primary" id="lcd-battery-card"><span class="lcd-primary-label" data-i18n="batteryVoltage">Напруга батареї</span><span class="lcd-primary-value" id="lcd-battery-voltage">—</span></div>
            <div class="lcd-primary" id="lcd-soc-card"><span class="lcd-primary-label" data-i18n="batterySoc">Заряд батареї</span><span class="lcd-primary-value" id="lcd-soc">—</span></div>
          </div>
          <div class="lcd-readouts">
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="frequency">Частота</span><span class="lcd-readout-value" id="lcd-frequency">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryCurrent">Струм батареї</span><span class="lcd-readout-value" id="lcd-battery-current">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryTemperature">Температура батареї</span><span class="lcd-readout-value" id="lcd-temperature">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="maxChargeVoltage">Макс. напруга заряду</span><span class="lcd-readout-value" id="lcd-charge-voltage">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="currentLimit">Ліміт струму</span><span class="lcd-readout-value" id="lcd-current-limit">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryState">Стан батареї</span><span class="lcd-readout-value" id="lcd-battery-state">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="inverterTemperature">Температура інвертора</span><span class="lcd-readout-value" id="lcd-inverter-temperature">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="systemStatus">Стан системи</span><span class="lcd-readout-value" id="lcd-system-status">—</span></div>
          </div>
          <div class="lcd-status-line" id="lcd-status-line">—</div>
          <div class="lcd-page-panel" aria-live="polite">
            <div class="lcd-page-head"><span class="lcd-page-code" id="lcd-page-code">LCD</span><span class="lcd-page-title" id="lcd-page-title">—</span></div>
            <div class="lcd-page-values">
              <div class="lcd-page-reading" id="lcd-page-reading-1"><span class="lcd-readout-label" id="lcd-page-label-1">—</span><span class="lcd-readout-value" id="lcd-page-value-1">—</span></div>
              <div class="lcd-page-reading" id="lcd-page-reading-2"><span class="lcd-readout-label" id="lcd-page-label-2">—</span><span class="lcd-readout-value" id="lcd-page-value-2">—</span></div>
            </div>
            <div class="lcd-page-description" id="lcd-page-description">—</div>
          </div>
          <div class="lcd-controls-wrap">
            <div class="lcd-controls-title" data-i18n="lcdControls">Керування LCD</div>
            <div class="lcd-controls" role="group" aria-label="Керування LCD" data-i18n-aria="lcdControls">
              <button class="lcd-key" type="button" data-lcd-key="escape" data-i18n-aria="lcdEscapeAria">ESC</button>
              <button class="lcd-key" type="button" data-lcd-key="up" data-i18n-aria="lcdUpAria">▲ UP</button>
              <button class="lcd-key" type="button" data-lcd-key="down" data-i18n-aria="lcdDownAria">▼ DOWN</button>
              <button class="lcd-key" type="button" data-lcd-key="enter" data-i18n-aria="lcdEnterAria">ENTER</button>
            </div>
            <div class="lcd-controls-note" data-i18n="lcdControlsLocalOnly">Віртуальні клавіші керують лише сторінками в застосунку й не записують налаштування в інвертор.</div>
          </div>
        </div>
      </div>
    </section>

    <section id="charts-view" hidden>
      <div class="charts-layout">
        <aside class="panel chart-selector">
          <h2 data-i18n="availableValues">Доступні значення</h2>
          <div class="muted" data-i18n="selectionHelp">Кожен вибраний показник додається на панель і до графіків у реальному часі.</div>
          <input id="chart-search" type="search" placeholder="Пошук значень…" aria-label="Пошук значень графіка" data-i18n-placeholder="searchValues" data-i18n-aria="searchChartValues">
          <div class="value-list" id="chart-value-list"></div>
        </aside>
        <div class="charts-main">
          <div class="panel-head charts-head">
            <div>
              <h2 data-i18n="liveCharts">Графіки в реальному часі</h2>
              <span class="muted" id="chart-selection-count">Значення не вибрано</span>
            </div>
            <button id="chart-demo-button" class="all-data-demo-button" type="button">Запустити реалістичне демо на 120 с</button>
          </div>
          <div class="chart-grid" id="chart-grid">
            <div class="chart-empty">Виберіть значення зі списку, щоб запустити графіки в реальному часі.</div>
          </div>
        </div>
      </div>
    </section>

    <dialog class="gauge-picker" id="gauge-picker">
      <div class="gauge-picker-head">
        <div>
          <h2 data-i18n="chooseGauges">Choose gauges</h2>
          <div class="muted" data-i18n="gaugePickerHelp">Вибрані індикатори з’являться на панелі та у графіках.</div>
        </div>
        <button class="gauge-picker-close" type="button" data-close-gauge-picker aria-label="Закрити" data-i18n-aria="close">×</button>
      </div>
      <input class="gauge-picker-search" id="gauge-picker-search" type="search" placeholder="Пошук значень…" data-i18n-placeholder="searchValues" aria-label="Пошук значень" data-i18n-aria="searchValues">
      <div class="gauge-picker-list" id="gauge-picker-list"></div>
    </dialog>
  </main>
  <script>
    const colours = ['#38bdf8','#22d3ee','#34d399','#fbbf24','#a78bfa','#fb7185','#60a5fa'];
    const UI_TRANSLATIONS = {
      uk: {
        waitingInverter: 'Очікування даних інвертора…',
        themeAria: 'Увімкнути світлу тему',
        languageAria: 'Мова інтерфейсу',
        themeDark: 'Темна', themeLight: 'Світла',
        stopMonitoring: 'Зупинити моніторинг', startMonitoring: 'Запустити моніторинг',
        viewCharts: 'Переглянути графіки', dashboard: '← Панель',
        viewTabsAria: 'Розділи застосунку', dashboardTab: 'Панель', chartsTab: 'Графіки', lcdTab: 'LCD',
        lcdTitle: 'LCD ІНВЕРТОРА', lcdSubtitle: 'Поточні показники з Modbus',
        grid: 'Мережа', inverter: 'Інвертор', load: 'Навантаження', pvInput: 'Вхід PV',
        batteryVoltage: 'Напруга батареї', batterySoc: 'Заряд батареї', frequency: 'Частота',
        batteryCurrent: 'Струм батареї', batteryTemperature: 'Температура батареї',
        maxChargeVoltage: 'Макс. напруга заряду', currentLimit: 'Ліміт струму', batteryState: 'Стан батареї',
        inverterTemperature: 'Температура інвертора', systemStatus: 'Стан системи',
        charging: 'ЗАРЯДЖАННЯ', discharging: 'РОЗРЯДЖАННЯ', batteryIdle: 'ОЧІКУВАННЯ',
        lcdControls: 'Керування LCD', lcdEscapeAria: 'Повернутися на головний екран LCD',
        lcdUpAria: 'Попередня інформаційна сторінка LCD', lcdDownAria: 'Наступна інформаційна сторінка LCD',
        lcdEnterAria: 'Відкрити вибрану сторінку LCD',
        lcdControlsLocalOnly: 'Віртуальні клавіші керують лише сторінками в застосунку й не записують налаштування в інвертор.',
        mainDisplay: 'Головний екран', dailyPvEnergy: 'Сонячна енергія за день', totalPvEnergy: 'Загальна сонячна енергія',
        ratedCapacity: 'Номінальна ємність', remainingCapacity: 'Залишкова ємність',
        minDischargeVoltage: 'Мін. напруга розряду', maxChargeCurrent: 'Макс. струм заряду',
        maxDischargeCurrent: 'Макс. струм розряду', alarmFault: 'Аварії та попередження', faultCode: 'Код аварії', alarmCode: 'Код попередження', firmwareVersion: 'Версія прошивки',
        lcdMainPageHelp: 'ESC повертає на цей екран. UP і DOWN перемикають інформаційні сторінки P1–P9 з інструкції.',
        lcdP1Help: 'P1 показує денне вироблення сонячної енергії. Відповідний Modbus-регістр у документації не вказано.',
        lcdP2Help: 'P2 показує загальне вироблення сонячної енергії. Відповідний Modbus-регістр у документації не вказано.',
        lcdP3Help: 'P3 показує напругу та струм літієвої батареї.', lcdP4Help: 'P4 показує температуру та SOC літієвої батареї.',
        lcdP5Help: 'P5 показує номінальну та залишкову ємність батареї.', lcdP6Help: 'P6 показує максимальну напругу заряду та мінімальну напругу розряду.',
        lcdP7Help: 'P7 показує максимальний струм заряду та розряду.', lcdP8Help: 'P8 показує коди аварій і попереджень батареї.',
        lcdP9Help: 'P9 показує версію прошивки інвертора.', settingsReadOnly: 'Режим налаштувань недоступний: інструкція не містить безпечних Modbus-адрес для запису.',
        offline: 'НЕМАЄ ЗВ’ЯЗКУ', online: 'У МЕРЕЖІ', paused: 'ПРИЗУПИНЕНО', demoMode: 'ДЕМО',
        requestEvery: 'Запит кожні', pollAria: 'Інтервал опитування',
        interval05: '0.5 с', interval1: '1 с', interval2: '2 с', interval5: '5 с', interval10: '10 с',
        readMode: 'Режим читання', readModeAria: 'Режим читання',
        fast: 'Швидкий', compatible: 'Сумісний',
        runDemo: 'Запустити реалістичне демо на 120 с',
        stopDemo: '■ Зупинити · {elapsed} / {seconds} с · {count} значень',
        addValues: '＋ Додати індикатори',
        registerLogger: 'Журнал змін регістрів',
        registerLoggerHelp: 'Записує початковий знімок і лише змінені значення у CSV з часом Мадрида.',
        registerLogNotePlaceholder: 'Напр. панелі вимкнено', markRegisterLog: '＋ Додати позначку',
        startRegisterLog: '● Почати запис', stopRegisterLog: '■ Зупинити',
        downloadRegisterLog: '↓ Завантажити CSV', registerLogIdle: 'Запис не запущено',
        registerLogActive: 'Запис · {filename} · рядків: {changes} · {size}',
        registerLogStopped: 'Зупинено · {filename} · рядків: {changes} · {size}',
        registerLogError: 'Помилка журналу: {error}', registerLogRequestError: 'Не вдалося змінити стан журналу: {error}',
        cycleInitial: 'Цикл —', visitorsInitial: 'Відвідувачі — · —',
        notUpdated: 'Ще не оновлено', gaugesAria: 'Індикатори інвертора',
        addedValues: 'Додані індикатори панелі', liveRegisters: 'Поточні регістри',
        searchRegisters: 'Пошук регістрів…',
        register: 'Регістр', group: 'Група', name: 'Назва', value: 'Значення', raw: 'Сире',
        registerNumber: 'Регістр {number}', operatingStatusCode: 'Код робочого стану {number}',
        availableValues: 'Доступні значення',
        selectionHelp: 'Кожен вибраний показник додається на панель і до графіків у реальному часі.',
        searchValues: 'Пошук значень…', searchChartValues: 'Пошук значень графіка',
        liveCharts: 'Графіки в реальному часі', noValuesSelected: 'Значення не вибрано',
        selectValues: 'Виберіть значення зі списку, щоб запустити графіки в реальному часі.',
        dashboardChart: 'Панель + графік', removeDashboard: 'Видалити з панелі',
        emptyDashboard: 'Індикатори не вибрано. Натисніть «Додати індикатори» та виберіть значення.',
        dragGauge: 'Перетягніть, щоб змінити порядок',
        chooseGauges: 'Виберіть індикатори', gaugePickerHelp: 'Вибрані індикатори з’являться на панелі й у графіках.',
        addGauge: 'Додати індикатор', close: 'Закрити',
        selectedSummary: 'Вибрано значень: {count} · останні 2 хвилини',
        chartAria: 'Графік у реальному часі для {label}',
        waiting: 'Очікування…', noData: 'Немає даних',
        registerCount: 'Отримано: {available} · очікують даних: {waiting} · показано: {shown}',
        unknownDevice: 'Невідомий пристрій', updated: 'Оновлено {time}',
        cyclePaused: 'Цикл {cycle} · моніторинг призупинено',
        cycleReads: 'Цикл {cycle} · {seconds} с · зчитано: {reads}',
        visitors: 'Відвідувачі {count} · {date}',
        connectionError: 'Помилка підключення: {error}',
        connectionLost: 'Втрачено зв’язок із панеллю: {error}',
        unitValue: 'значення', gaugeDetail: '{unit} · шкала R{register}',
        allDataDemo: 'Реалістичне демо даних', direct: 'прямий перехід',
        visitConsole: '[Відвідування Solar Invertor Web]',
        totalVisitorsLabel: 'усього відвідувачів', dateLabel: 'дата', openedLabel: 'відкрито',
        referrerLabel: 'джерело переходу', browserLanguageLabel: 'мова браузера',
        browserLabel: 'браузер', viewportLabel: 'розмір вікна'
      },
      ru: {
        waitingInverter: 'Ожидание данных инвертора…',
        themeAria: 'Включить светлую тему',
        languageAria: 'Язык интерфейса',
        themeDark: 'Тёмная', themeLight: 'Светлая',
        stopMonitoring: 'Остановить мониторинг', startMonitoring: 'Запустить мониторинг',
        viewCharts: 'Просмотреть графики', dashboard: '← Панель',
        viewTabsAria: 'Разделы приложения', dashboardTab: 'Панель', chartsTab: 'Графики', lcdTab: 'LCD',
        lcdTitle: 'LCD ИНВЕРТОРА', lcdSubtitle: 'Текущие показатели из Modbus',
        grid: 'Сеть', inverter: 'Инвертор', load: 'Нагрузка', pvInput: 'Вход PV',
        batteryVoltage: 'Напряжение батареи', batterySoc: 'Заряд батареи', frequency: 'Частота',
        batteryCurrent: 'Ток батареи', batteryTemperature: 'Температура батареи',
        maxChargeVoltage: 'Макс. напряжение заряда', currentLimit: 'Предел тока', batteryState: 'Состояние батареи',
        inverterTemperature: 'Температура инвертора', systemStatus: 'Состояние системы',
        charging: 'ЗАРЯДКА', discharging: 'РАЗРЯДКА', batteryIdle: 'ОЖИДАНИЕ',
        lcdControls: 'Управление LCD', lcdEscapeAria: 'Вернуться на главный экран LCD',
        lcdUpAria: 'Предыдущая информационная страница LCD', lcdDownAria: 'Следующая информационная страница LCD',
        lcdEnterAria: 'Открыть выбранную страницу LCD',
        lcdControlsLocalOnly: 'Виртуальные клавиши управляют только страницами в приложении и не записывают настройки в инвертор.',
        mainDisplay: 'Главный экран', dailyPvEnergy: 'Солнечная энергия за день', totalPvEnergy: 'Общая солнечная энергия',
        ratedCapacity: 'Номинальная ёмкость', remainingCapacity: 'Оставшаяся ёмкость',
        minDischargeVoltage: 'Мин. напряжение разряда', maxChargeCurrent: 'Макс. ток заряда',
        maxDischargeCurrent: 'Макс. ток разряда', alarmFault: 'Аварии и предупреждения', faultCode: 'Код аварии', alarmCode: 'Код предупреждения', firmwareVersion: 'Версия прошивки',
        lcdMainPageHelp: 'ESC возвращает на этот экран. UP и DOWN переключают информационные страницы P1–P9 из инструкции.',
        lcdP1Help: 'P1 показывает дневную выработку солнечной энергии. Соответствующий Modbus-регистр в документации не указан.',
        lcdP2Help: 'P2 показывает общую выработку солнечной энергии. Соответствующий Modbus-регистр в документации не указан.',
        lcdP3Help: 'P3 показывает напряжение и ток литиевой батареи.', lcdP4Help: 'P4 показывает температуру и SOC литиевой батареи.',
        lcdP5Help: 'P5 показывает номинальную и оставшуюся ёмкость батареи.', lcdP6Help: 'P6 показывает максимальное напряжение заряда и минимальное напряжение разряда.',
        lcdP7Help: 'P7 показывает максимальный ток заряда и разряда.', lcdP8Help: 'P8 показывает коды аварий и предупреждений батареи.',
        lcdP9Help: 'P9 показывает версию прошивки инвертора.', settingsReadOnly: 'Режим настроек недоступен: инструкция не содержит безопасных Modbus-адресов для записи.',
        offline: 'НЕТ СВЯЗИ', online: 'В СЕТИ', paused: 'ПРИОСТАНОВЛЕНО', demoMode: 'ДЕМО',
        requestEvery: 'Запрос каждые', pollAria: 'Интервал опроса',
        interval05: '0.5 с', interval1: '1 с', interval2: '2 с', interval5: '5 с', interval10: '10 с',
        readMode: 'Режим чтения', readModeAria: 'Режим чтения',
        fast: 'Быстрый', compatible: 'Совместимый',
        runDemo: 'Запустить реалистичное демо на 120 с',
        stopDemo: '■ Остановить · {elapsed} / {seconds} с · {count} значений',
        addValues: '＋ Добавить индикаторы',
        registerLogger: 'Журнал изменений регистров',
        registerLoggerHelp: 'Записывает начальный снимок и только изменённые значения в CSV со временем Мадрида.',
        registerLogNotePlaceholder: 'Напр. панели выключены', markRegisterLog: '＋ Добавить отметку',
        startRegisterLog: '● Начать запись', stopRegisterLog: '■ Остановить',
        downloadRegisterLog: '↓ Скачать CSV', registerLogIdle: 'Запись не запущена',
        registerLogActive: 'Запись · {filename} · строк: {changes} · {size}',
        registerLogStopped: 'Остановлено · {filename} · строк: {changes} · {size}',
        registerLogError: 'Ошибка журнала: {error}', registerLogRequestError: 'Не удалось изменить журнал: {error}',
        cycleInitial: 'Цикл —', visitorsInitial: 'Посетители — · —',
        notUpdated: 'Ещё не обновлено', gaugesAria: 'Индикаторы инвертора',
        addedValues: 'Добавленные индикаторы панели', liveRegisters: 'Текущие регистры',
        searchRegisters: 'Поиск регистров…',
        register: 'Регистр', group: 'Группа', name: 'Название', value: 'Значение', raw: 'Сырое',
        registerNumber: 'Регистр {number}', operatingStatusCode: 'Код рабочего состояния {number}',
        availableValues: 'Доступные значения',
        selectionHelp: 'Каждый выбранный показатель добавляется на панель и на графики в реальном времени.',
        searchValues: 'Поиск значений…', searchChartValues: 'Поиск значений графика',
        liveCharts: 'Графики в реальном времени', noValuesSelected: 'Значения не выбраны',
        selectValues: 'Выберите значения из списка, чтобы запустить графики в реальном времени.',
        dashboardChart: 'Панель + график', removeDashboard: 'Удалить с панели',
        emptyDashboard: 'Индикаторы не выбраны. Нажмите «Добавить индикаторы» и выберите значения.',
        dragGauge: 'Перетащите, чтобы изменить порядок',
        chooseGauges: 'Выберите индикаторы', gaugePickerHelp: 'Выбранные индикаторы появятся на панели и на графиках.',
        addGauge: 'Добавить индикатор', close: 'Закрыть',
        selectedSummary: 'Выбрано значений: {count} · последние 2 минуты',
        chartAria: 'График в реальном времени для {label}',
        waiting: 'Ожидание…', noData: 'Нет данных',
        registerCount: 'Получено: {available} · ожидают данных: {waiting} · показано: {shown}',
        unknownDevice: 'Неизвестное устройство', updated: 'Обновлено {time}',
        cyclePaused: 'Цикл {cycle} · мониторинг приостановлен',
        cycleReads: 'Цикл {cycle} · {seconds} с · считано: {reads}',
        visitors: 'Посетители {count} · {date}',
        connectionError: 'Ошибка подключения: {error}',
        connectionLost: 'Потеряна связь с панелью: {error}',
        unitValue: 'значение', gaugeDetail: '{unit} · шкала R{register}',
        allDataDemo: 'Реалистичное демо данных', direct: 'прямой переход',
        visitConsole: '[Посещение Solar Invertor Web]',
        totalVisitorsLabel: 'всего посетителей', dateLabel: 'дата', openedLabel: 'открыто',
        referrerLabel: 'источник перехода', browserLanguageLabel: 'язык браузера',
        browserLabel: 'браузер', viewportLabel: 'размер окна'
      },
      en: {
        waitingInverter: 'Waiting for inverter data…',
        themeAria: 'Use light theme',
        languageAria: 'Interface language',
        themeDark: 'Dark', themeLight: 'Light',
        stopMonitoring: 'Stop monitoring', startMonitoring: 'Start monitoring',
        viewCharts: 'View charts', dashboard: '← Dashboard',
        viewTabsAria: 'Application sections', dashboardTab: 'Dashboard', chartsTab: 'Charts', lcdTab: 'LCD',
        lcdTitle: 'INVERTER LCD', lcdSubtitle: 'Live readings from Modbus',
        grid: 'Grid', inverter: 'Inverter', load: 'Load', pvInput: 'PV input',
        batteryVoltage: 'Battery voltage', batterySoc: 'Battery charge', frequency: 'Frequency',
        batteryCurrent: 'Battery current', batteryTemperature: 'Battery temperature',
        maxChargeVoltage: 'Max. charge voltage', currentLimit: 'Current limit', batteryState: 'Battery state',
        inverterTemperature: 'Inverter temperature', systemStatus: 'System status',
        charging: 'CHARGING', discharging: 'DISCHARGING', batteryIdle: 'IDLE',
        lcdControls: 'LCD controls', lcdEscapeAria: 'Return to the main LCD screen',
        lcdUpAria: 'Previous LCD information page', lcdDownAria: 'Next LCD information page',
        lcdEnterAria: 'Open the selected LCD page',
        lcdControlsLocalOnly: 'The virtual keys control app pages only and do not write settings to the inverter.',
        mainDisplay: 'Main display', dailyPvEnergy: 'Daily solar energy', totalPvEnergy: 'Total solar energy',
        ratedCapacity: 'Rated capacity', remainingCapacity: 'Remaining capacity',
        minDischargeVoltage: 'Min. discharge voltage', maxChargeCurrent: 'Max. charging current',
        maxDischargeCurrent: 'Max. discharging current', alarmFault: 'Faults and alarms', faultCode: 'Fault code', alarmCode: 'Alarm code', firmwareVersion: 'Firmware version',
        lcdMainPageHelp: 'ESC returns to this screen. UP and DOWN browse the manual’s P1–P9 information pages.',
        lcdP1Help: 'P1 shows daily solar production. The manual does not provide its corresponding Modbus register.',
        lcdP2Help: 'P2 shows total solar production. The manual does not provide its corresponding Modbus register.',
        lcdP3Help: 'P3 shows lithium-battery voltage and current.', lcdP4Help: 'P4 shows lithium-battery temperature and SOC.',
        lcdP5Help: 'P5 shows rated and remaining battery capacity.', lcdP6Help: 'P6 shows maximum charging and minimum discharging voltage.',
        lcdP7Help: 'P7 shows maximum charging and discharging current.', lcdP8Help: 'P8 shows battery fault and alarm codes.',
        lcdP9Help: 'P9 shows the inverter firmware version.', settingsReadOnly: 'Settings mode is unavailable because the manual provides no safe Modbus write addresses.',
        offline: 'OFFLINE', online: 'ONLINE', paused: 'PAUSED', demoMode: 'DEMO',
        requestEvery: 'Request every', pollAria: 'Polling interval',
        interval05: '0.5 s', interval1: '1 s', interval2: '2 s', interval5: '5 s', interval10: '10 s',
        readMode: 'Read mode', readModeAria: 'Read mode',
        fast: 'Fast', compatible: 'Compatible',
        runDemo: 'Run realistic 120s demo',
        stopDemo: '■ Stop · {elapsed} / {seconds}s · {count} values',
        addValues: '＋ Add gauges',
        registerLogger: 'Register change log',
        registerLoggerHelp: 'Records an initial snapshot and changed values only in a Madrid-time CSV file.',
        registerLogNotePlaceholder: 'E.g. panels switched off', markRegisterLog: '＋ Add marker',
        startRegisterLog: '● Start recording', stopRegisterLog: '■ Stop',
        downloadRegisterLog: '↓ Download CSV', registerLogIdle: 'Recording is not running',
        registerLogActive: 'Recording · {filename} · rows: {changes} · {size}',
        registerLogStopped: 'Stopped · {filename} · rows: {changes} · {size}',
        registerLogError: 'Log error: {error}', registerLogRequestError: 'Could not change log state: {error}',
        cycleInitial: 'Cycle —', visitorsInitial: 'Visitors — · —',
        notUpdated: 'Not updated yet', gaugesAria: 'Live inverter gauges',
        addedValues: 'Added dashboard gauges', liveRegisters: 'Live registers',
        searchRegisters: 'Search registers…',
        register: 'Register', group: 'Group', name: 'Name', value: 'Value', raw: 'Raw',
        registerNumber: 'Register {number}', operatingStatusCode: 'Operating status code {number}',
        availableValues: 'Available values',
        selectionHelp: 'Each selected reading is added to the dashboard and live charts.',
        searchValues: 'Search values…', searchChartValues: 'Search chart values',
        liveCharts: 'Live charts', noValuesSelected: 'No values selected',
        selectValues: 'Select values from the list to start real-time charts.',
        dashboardChart: 'Dashboard + chart', removeDashboard: 'Remove from dashboard',
        emptyDashboard: 'No gauges selected. Click Add gauges and select the readings to display.',
        dragGauge: 'Drag to reorder',
        chooseGauges: 'Choose gauges', gaugePickerHelp: 'Selected gauges appear on the dashboard and live charts.',
        addGauge: 'Add gauge', close: 'Close',
        selectedSummary: '{count} values selected · last 2 minutes',
        chartAria: 'Live chart for {label}',
        waiting: 'Waiting…', noData: 'No data',
        registerCount: '{available} received · {waiting} awaiting data · {shown} shown',
        unknownDevice: 'Unknown device', updated: 'Updated {time}',
        cyclePaused: 'Cycle {cycle} · monitoring paused',
        cycleReads: 'Cycle {cycle} · {seconds} s · {reads} reads',
        visitors: 'Visitors {count} · {date}',
        connectionError: 'Connection error: {error}',
        connectionLost: 'Dashboard connection lost: {error}',
        unitValue: 'value', gaugeDetail: '{unit} · gauge R{register}',
        allDataDemo: 'Realistic data demo', direct: 'direct',
        visitConsole: '[Solar Invertor Web visit]',
        totalVisitorsLabel: 'total visitors', dateLabel: 'date', openedLabel: 'opened',
        referrerLabel: 'referrer', browserLanguageLabel: 'browser language',
        browserLabel: 'browser', viewportLabel: 'viewport'
      }
    };
    const DATA_TRANSLATIONS = {
      'AC': {ru:'AC', en:'AC'},
      'BMS': {ru:'BMS', en:'BMS'},
      'PV': {ru:'PV', en:'PV'},
      'Ідентифікація': {ru:'Идентификация', en:'Identification'},
      'Ідентифікатор пристрою, слово 1': {ru:'Идентификатор устройства, слово 1', en:'Device identifier, word 1'},
      'Ідентифікатор пристрою, слово 2': {ru:'Идентификатор устройства, слово 2', en:'Device identifier, word 2'},
      'Ідентифікатор пристрою, слово 3': {ru:'Идентификатор устройства, слово 3', en:'Device identifier, word 3'},
      'Ідентифікатор пристрою, слово 4': {ru:'Идентификатор устройства, слово 4', en:'Device identifier, word 4'},
      'Ідентифікатор пристрою, слово 5': {ru:'Идентификатор устройства, слово 5', en:'Device identifier, word 5'},
      'Ідентифікатор пристрою, слово 6': {ru:'Идентификатор устройства, слово 6', en:'Device identifier, word 6'},
      'Ідентифікатор пристрою, слово 7': {ru:'Идентификатор устройства, слово 7', en:'Device identifier, word 7'},
      'Ідентифікатор пристрою, слово 8': {ru:'Идентификатор устройства, слово 8', en:'Device identifier, word 8'},
      'Ідентифікатор пристрою, слово 9': {ru:'Идентификатор устройства, слово 9', en:'Device identifier, word 9'},
      'Код протоколу або версії': {ru:'Код протокола или версии', en:'Protocol or version code'},
      'Системне слово 27': {ru:'Системное слово 27', en:'System word 27'},
      'Системний прапорець 28': {ru:'Системный флаг 28', en:'System flag 28'},
      'Бітова маска можливостей або стану': {ru:'Битовая маска возможностей или состояния', en:'Capability or status bitmask'},
      'Системне слово 65': {ru:'Системное слово 65', en:'System word 65'},
      'Код конфігурації 66': {ru:'Код конфигурации 66', en:'Configuration code 66'},
      'Код конфігурації 67': {ru:'Код конфигурации 67', en:'Configuration code 67'},
      'Системне значення 68': {ru:'Системное значение 68', en:'System value 68'},
      'Упаковане знакове значення 69': {ru:'Упакованное знаковое значение 69', en:'Packed signed value 69'},
      'Параметр AC 90': {ru:'Параметр AC 90', en:'AC parameter 90'},
      'Температура': {ru:'Температура', en:'Temperature'},
      'Температурний канал інвертора': {ru:'Температурный канал инвертора', en:'Inverter temperature channel'},
      'Канал напруги 93': {ru:'Канал напряжения 93', en:'Voltage channel 93'},
      'Відсотковий параметр 94': {ru:'Процентный параметр 94', en:'Percentage parameter 94'},
      'Напруга батареї, канал 129': {ru:'Напряжение батареи, канал 129', en:'Battery voltage, channel 129'},
      'Струм батареї без знаку': {ru:'Ток батареи без знака', en:'Unsigned battery current'},
      'Температура батареї, канал 134': {ru:'Температура батареи, канал 134', en:'Battery temperature, channel 134'},
      'Напруга батареї BMS': {ru:'Напряжение батареи BMS', en:'BMS battery voltage'},
      'Струм батареї BMS': {ru:'Ток батареи BMS', en:'BMS battery current'},
      'Рівень заряду батареї BMS': {ru:'Уровень заряда батареи BMS', en:'BMS battery state of charge'},
      'Температура BMS': {ru:'Температура BMS', en:'BMS temperature'},
      'Температура BMS, канал 140': {ru:'Температура BMS, канал 140', en:'BMS temperature, channel 140'},
      'Верхня напруга заряджання BMS': {ru:'Верхнее напряжение зарядки BMS', en:'BMS upper charging voltage'},
      'Недоступний параметр BMS 142': {ru:'Недоступный параметр BMS 142', en:'Unavailable BMS parameter 142'},
      'Недоступний параметр BMS 143': {ru:'Недоступный параметр BMS 143', en:'Unavailable BMS parameter 143'},
      'Параметр BMS 144': {ru:'Параметр BMS 144', en:'BMS parameter 144'},
      'Системний параметр стану 158': {ru:'Системный параметр состояния 158', en:'System status parameter 158'},
      'Прапорець каналу BMS': {ru:'Флаг канала BMS', en:'BMS channel flag'},
      'Код конфігурації BMS 324': {ru:'Код конфигурации BMS 324', en:'BMS configuration code 324'},
      'Код конфігурації BMS 325': {ru:'Код конфигурации BMS 325', en:'BMS configuration code 325'},
      'Код стану BMS 337': {ru:'Код состояния BMS 337', en:'BMS status code 337'},
      'Канал напруги 341, ймовірно PV': {ru:'Канал напряжения 341, вероятно PV', en:'Voltage channel 341, possibly PV'},
      'Напруга каналу 341': {ru:'Напряжение канала 341', en:'Channel 341 voltage'},
      'Напруга батареї BMS, канал 342': {ru:'Напряжение батареи BMS, канал 342', en:'BMS battery voltage, channel 342'},
      'Струм BMS, канал 343': {ru:'Ток BMS, канал 343', en:'BMS current, channel 343'},
      'Струм батареї BMS, канал 344': {ru:'Ток батареи BMS, канал 344', en:'BMS battery current, channel 344'},
      'Верхня межа напруги BMS': {ru:'Верхний предел напряжения BMS', en:'BMS upper voltage limit'},
      'Нижня межа напруги BMS 1': {ru:'Нижний предел напряжения BMS 1', en:'BMS lower voltage limit 1'},
      'Нижня межа напруги BMS 2': {ru:'Нижний предел напряжения BMS 2', en:'BMS lower voltage limit 2'},
      'Знаковий струмовий параметр BMS': {ru:'Знаковый параметр тока BMS', en:'Signed BMS current parameter'},
      'Напруга заряджання, налаштування 376': {ru:'Напряжение зарядки, настройка 376', en:'Charging voltage, setting 376'},
      'Напруга заряджання, налаштування 377': {ru:'Напряжение зарядки, настройка 377', en:'Charging voltage, setting 377'},
      'Ліміт струму 378': {ru:'Предел тока 378', en:'Current limit 378'},
      'Ліміт струму 379': {ru:'Предел тока 379', en:'Current limit 379'},
      'Верхня напруга батареї, налаштування 383': {ru:'Верхнее напряжение батареи, настройка 383', en:'Upper battery voltage, setting 383'},
      'Потужність': {ru:'Мощность', en:'Power'},
      'Параметр потужності 385': {ru:'Параметр мощности 385', en:'Power parameter 385'},
      'Параметр потужності 386': {ru:'Параметр мощности 386', en:'Power parameter 386'},
      'Код BMS або стану 401': {ru:'Код BMS или состояния 401', en:'BMS or status code 401'},
      'Прапорець BMS або стану 402': {ru:'Флаг BMS или состояния 402', en:'BMS or status flag 402'},
      'Упакований параметр BMS 403': {ru:'Упакованный параметр BMS 403', en:'Packed BMS parameter 403'},
      'Напруга батареї BMS, канал 404': {ru:'Напряжение батареи BMS, канал 404', en:'BMS battery voltage, channel 404'},
      'Струм батареї BMS, канал 405': {ru:'Ток батареи BMS, канал 405', en:'BMS battery current, channel 405'},
      'Температура BMS, канал 406': {ru:'Температура BMS, канал 406', en:'BMS temperature, channel 406'},
      'Відсотковий параметр BMS': {ru:'Процентный параметр BMS', en:'BMS percentage parameter'},
      'Відсотковий параметр BMS, можливо SOH': {ru:'Процентный параметр BMS, возможно SOH', en:'BMS percentage parameter, possibly SOH'},
      'Недоступний параметр BMS 409': {ru:'Недоступный параметр BMS 409', en:'Unavailable BMS parameter 409'},
      'Недоступний параметр BMS 410': {ru:'Недоступный параметр BMS 410', en:'Unavailable BMS parameter 410'},
      'Ліміт струму BMS': {ru:'Предел тока BMS', en:'BMS current limit'},
      'Параметр потужності BMS 413': {ru:'Параметр мощности BMS 413', en:'BMS power parameter 413'},
      'Параметр потужності 413': {ru:'Параметр мощности 413', en:'Power parameter 413'},
      'Параметр налаштування 415': {ru:'Параметр настройки 415', en:'Setting parameter 415'},
      'Параметр налаштування 416': {ru:'Параметр настройки 416', en:'Setting parameter 416'},
      'Параметр налаштування 417': {ru:'Параметр настройки 417', en:'Setting parameter 417'},
      'Параметр системи 449': {ru:'Параметр системы 449', en:'System parameter 449'},
      'Упаковане значення 451': {ru:'Упакованное значение 451', en:'Packed value 451'},
      'Упаковане значення 453': {ru:'Упакованное значение 453', en:'Packed value 453'},
      'Упаковане знакове значення 455': {ru:'Упакованное знаковое значение 455', en:'Packed signed value 455'},
      'Напруга заряджання / ліміт': {ru:'Напряжение зарядки / предел', en:'Charging voltage / limit'},
      'Знаковий струмовий параметр': {ru:'Знаковый параметр тока', en:'Signed current parameter'},
      'Очікування або невідомий стан': {ru:'Ожидание или неизвестное состояние', en:'Standby or unknown state'},
      'Ймовірно робота від мережі або байпас': {ru:'Вероятно работа от сети или байпас', en:'Possibly grid or bypass operation'},
      'Ймовірно робота інвертора від батареї або PV': {ru:'Вероятно работа инвертора от батареи или PV', en:'Possibly inverter operation from battery or PV'},
      'Ймовірно заряджання або активна робота': {ru:'Вероятно зарядка или активная работа', en:'Possibly charging or active operation'},
      'Ймовірно помилка або аварійний стан': {ru:'Вероятно ошибка или аварийное состояние', en:'Possibly a fault or emergency state'},
      'нотатка не може бути порожньою': {ru:'заметка не может быть пустой', en:'note cannot be empty'},
      'нотатка не може перевищувати 500 символів': {ru:'заметка не может превышать 500 символов', en:'note cannot exceed 500 characters'},
      'спочатку запустіть запис журналу': {ru:'сначала запустите запись журнала', en:'start log recording first'},
      'action має бути start, stop або mark': {ru:'action должно быть start, stop или mark', en:'action must be start, stop, or mark'},
      'неправильний інтервал опитування': {ru:'неправильный интервал опроса', en:'invalid polling interval'},
      'неправильний режим читання': {ru:'неправильный режим чтения', en:'invalid read mode'},
      'paused має бути true або false': {ru:'paused должно быть true или false', en:'paused must be true or false'},
      'журнал ще не створено': {ru:'журнал ещё не создан', en:'log has not been created yet'},
      'Код протоколу/версії': {ru:'Код протокола/версии', en:'Protocol/version code'},
      'Код конфігурації пристрою': {ru:'Код конфигурации устройства', en:'Device configuration code'},
      'Слово прошивки/стану': {ru:'Слово прошивки/состояния', en:'Firmware/status word'},
      'Прапорець прошивки/стану': {ru:'Флаг прошивки/состояния', en:'Firmware/status flag'},
      'Бітова маска можливостей/стану': {ru:'Битовая маска возможностей/состояния', en:'Capability/status bitmask'},
      'Код конфігурації': {ru:'Код конфигурации', en:'Configuration code'},
      'Значення прошивки/стану': {ru:'Значение прошивки/состояния', en:'Firmware/status value'},
      'Знакове значення стану': {ru:'Знаковое значение состояния', en:'Signed status value'},
      'Напруга AC': {ru:'Напряжение AC', en:'AC voltage'},
      'Вхідний струм AC / значення навантаження': {ru:'Входной ток AC / значение нагрузки', en:'AC input current / load value'},
      'Частота AC': {ru:'Частота AC', en:'AC frequency'},
      'Температура інвертора': {ru:'Температура инвертора', en:'Inverter temperature'},
      'Напруга батареї (дані LCD)': {ru:'Напряжение батареи (данные LCD)', en:'Battery voltage (LCD data)'},
      'Відсоток заряду батареї/навантаження': {ru:'Процент заряда батареи/нагрузки', en:'Battery/load percentage'},
      'Напруга батареї': {ru:'Напряжение батареи', en:'Battery voltage'},
      'Струм заряджання батареї': {ru:'Ток зарядки батареи', en:'Battery charging current'},
      'Рівень заряду батареї': {ru:'Уровень заряда батареи', en:'Battery state of charge'},
      'Температура літієвої батареї': {ru:'Температура литиевой батареи', en:'Lithium battery temperature'},
      'Напруга літієвої батареї (P3)': {ru:'Напряжение литиевой батареи (P3)', en:'Lithium battery voltage (P3)'},
      'Струм літієвої батареї (P3)': {ru:'Ток литиевой батареи (P3)', en:'Lithium battery current (P3)'},
      'Рівень заряду літієвої батареї (P4)': {ru:'Уровень заряда литиевой батареи (P4)', en:'Lithium battery state of charge (P4)'},
      'Температура літієвої батареї (P4)': {ru:'Температура литиевой батареи (P4)', en:'Lithium battery temperature (P4)'},
      'Максимальна напруга заряджання літієвої батареї (P6)': {ru:'Максимальное напряжение зарядки литиевой батареи (P6)', en:'Maximum lithium battery charging voltage (P6)'},
      'Недоступне значення': {ru:'Недоступное значение', en:'Unavailable value'},
      'Потужність/струм/стан батареї': {ru:'Мощность/ток/состояние батареи', en:'Battery power/current/status'},
      'Код робочого стану': {ru:'Код рабочего состояния', en:'Operating status code'},
      'Стан/внутрішнє значення': {ru:'Состояние/внутреннее значение', en:'Status/internal value'},
      'Прапорець каналу/кількості BMS': {ru:'Флаг канала/количества BMS', en:'BMS channel/count flag'},
      'Код конфігурації BMS': {ru:'Код конфигурации BMS', en:'BMS configuration code'},
      'Код стану BMS': {ru:'Код состояния BMS', en:'BMS status code'},
      'Рівень заряду літієвої батареї': {ru:'Уровень заряда литиевой батареи', en:'Lithium battery state of charge'},
      'Вхідна напруга PV': {ru:'Входное напряжение PV', en:'PV input voltage'},
      'Напруга літієвої батареї': {ru:'Напряжение литиевой батареи', en:'Lithium battery voltage'},
      'Максимальний струм заряджання літієвої батареї': {ru:'Максимальный ток зарядки литиевой батареи', en:'Maximum lithium battery charging current'},
      'Струм літієвої батареї': {ru:'Ток литиевой батареи', en:'Lithium battery current'},
      'Межа напруги літієвої батареї': {ru:'Предел напряжения литиевой батареи', en:'Lithium battery voltage limit'},
      'Межа струму розряджання літієвої батареї': {ru:'Предел тока разрядки литиевой батареи', en:'Lithium battery discharge current limit'},
      'Налаштування напруги батареї': {ru:'Настройка напряжения батареи', en:'Battery voltage setting'},
      'Налаштування струму батареї': {ru:'Настройка тока батареи', en:'Battery current setting'},
      'Номінальна потужність / межа віддачі в мережу': {ru:'Номинальная мощность / предел отдачи в сеть', en:'Rated power / grid export limit'},
      'Налаштування потужності / межа': {ru:'Настройка мощности / предел', en:'Power setting / limit'},
      'Код BMS/стану': {ru:'Код BMS/состояния', en:'BMS/status code'},
      'Прапорець BMS/стану': {ru:'Флаг BMS/состояния', en:'BMS/status flag'},
      'Накопичене значення/потужність': {ru:'Накопленное значение/мощность', en:'Accumulated value/power'},
      'Залишкова/номінальна ємність літієвої батареї': {ru:'Оставшаяся/номинальная ёмкость литиевой батареи', en:'Remaining/rated lithium battery capacity'},
      'Максимальний струм літієвої батареї': {ru:'Максимальный ток литиевой батареи', en:'Maximum lithium battery current'},
      'Потужність батареї/PV': {ru:'Мощность батареи/PV', en:'Battery/PV power'},
      'Межа налаштування': {ru:'Предел настройки', en:'Setting limit'},
      'Напруга/значення': {ru:'Напряжение/значение', en:'Voltage/value'},
      'Упаковане значення/лічильник': {ru:'Упакованное значение/счётчик', en:'Packed value/counter'},
      'Упаковане знакове значення': {ru:'Упакованное знаковое значение', en:'Packed signed value'},
      'Струм батареї': {ru:'Ток батареи', en:'Battery current'},
      'Температура батареї': {ru:'Температура батареи', en:'Battery temperature'},
      'Стан батареї SOH / межа': {ru:'Состояние батареи SOH / предел', en:'Battery SOH / limit'},
      'Макс. напруга заряджання': {ru:'Макс. напряжение зарядки', en:'Max. charging voltage'},
      'Макс. струм заряджання': {ru:'Макс. ток зарядки', en:'Max. charging current'},
      'Межа струму розряджання': {ru:'Предел тока разрядки', en:'Discharge current limit'},
      'Потужність батареї / PV': {ru:'Мощность батареи / PV', en:'Battery / PV power'},
      'Номінальна потужність': {ru:'Номинальная мощность', en:'Rated power'},
      'Межа потужності': {ru:'Предел мощности', en:'Power limit'},
      'Система': {ru:'Система', en:'System'},
      'Батарея': {ru:'Батарея', en:'Battery'},
      'Налаштування': {ru:'Настройки', en:'Settings'},
      'Сире': {ru:'Сырое', en:'Raw'},
      'Робочий стан': {ru:'Рабочее состояние', en:'Operating status'},
      'Очікування / невідомо': {ru:'Ожидание / неизвестно', en:'Standby / unknown'},
      'Робота від мережі / байпас': {ru:'Работа от сети / байпас', en:'Grid / bypass operation'},
      'Робота інвертора від батареї або PV': {ru:'Работа инвертора от батареи или PV', en:'Inverter operation from battery or PV'},
      'Заряджання / активна робота': {ru:'Зарядка / активная работа', en:'Charging / active operation'},
      'Помилка або аварійний стан': {ru:'Ошибка или аварийное состояние', en:'Fault or emergency state'},
      'Немає даних mbpoll': {ru:'Нет данных mbpoll', en:'No mbpoll data'},
      'перевищено час очікування': {ru:'превышено время ожидания', en:'request timed out'},
      'mbpoll не знайдено': {ru:'mbpoll не найден', en:'mbpoll not found'},
      'помилка читання': {ru:'ошибка чтения', en:'read error'},
      'ніколи': {ru:'никогда', en:'never'},
      'Н/Д': {ru:'Н/Д', en:'N/A'},
      'Випадкове демо всіх даних': {ru:'Случайное демо всех данных', en:'All-data random demo'}
    };
    let currentLanguage = 'uk';
    function t(key, replacements = {}) {
      const template = UI_TRANSLATIONS[currentLanguage]?.[key] ?? UI_TRANSLATIONS.uk[key] ?? key;
      return template.replace(/\{(\w+)\}/g, (_, name) =>
        Object.prototype.hasOwnProperty.call(replacements, name) ? replacements[name] : `{${name}}`
      );
    }
    function localizeDataText(text) {
      if (!text || currentLanguage === 'uk') return text;
      const registerMatch = /^Регістр (\d+)$/.exec(text);
      if (registerMatch) return t('registerNumber', {number: registerMatch[1]});
      const statusMatch = /^Код робочого стану (\d+)$/.exec(text);
      if (statusMatch) return t('operatingStatusCode', {number: statusMatch[1]});
      return DATA_TRANSLATIONS[text]?.[currentLanguage] ?? text;
    }
    const previous = new Map();
    let lastData = null;
    let chartDemoRunning = false;
    let chartDemoCancelRequested = false;
    let demoRegisterRows = null;
    let currentView = 'dashboard';
    let lcdPageIndex = 0;
    let lcdEnterNotice = false;
    let refreshInFlight = false;
    let refreshTimer = null;
    let refreshController = null;
    let lastLoggedSiteVisits = null;
    const requestIntervals = [500, 1000, 2000, 5000, 10000];
    let chartDefinitions = new Map();
    function savedSelections(name) {
      try {
        return new Set(JSON.parse(window.localStorage.getItem(name) || '[]'));
      } catch {
        return new Set();
      }
    }
    function saveSelections(name, selections) {
      try {
        window.localStorage.setItem(name, JSON.stringify([...selections]));
      } catch {
        // The dashboard still works when browser storage is unavailable.
      }
    }
    function savedMap(name) {
      try {
        const value = JSON.parse(window.localStorage.getItem(name) || '{}');
        return new Map(Object.entries(value && typeof value === 'object' ? value : {}));
      } catch {
        return new Map();
      }
    }
    function saveMap(name, values) {
      try {
        window.localStorage.setItem(name, JSON.stringify(Object.fromEntries(values)));
      } catch {
        // Gauge appearance remains stable for the current page when storage is unavailable.
      }
    }
    const chartSelections = savedSelections('inverter-chart-values-v2');
    const dashboardSelections = savedSelections('inverter-dashboard-gauges-v2');
    const chartHistory = new Map();
    const dashboardGaugeRanges = savedMap('inverter-dashboard-gauge-ranges-v2');
    const dashboardGaugeColours = savedMap('inverter-dashboard-gauge-colours-v2');
    const chartWindowSeconds = 120;
    const chartWindowMilliseconds = chartWindowSeconds * 1000;

    function numericValue(value) {
      const parsed = Number.parseFloat(value);
      return Number.isFinite(parsed) ? parsed : null;
    }

    function collectChartDefinitions(data) {
      const definitions = new Map();
      data.meters.forEach(meter => {
        definitions.set(`meter-${meter.register}`, {
          key: `meter-${meter.register}`,
          register: meter.register,
          label: localizeDataText(meter.label),
          detail: t('gaugeDetail', {
            unit: meter.unit || t('unitValue'),
            register: meter.register
          }),
          unit: meter.unit,
          value: Number.isFinite(meter.value) ? meter.value : 0,
          minimum: meter.minimum,
          maximum: meter.maximum,
          available: !String(meter.source || '').toLowerCase().includes('mbpoll'),
          source: localizeDataText(meter.source)
        });
      });
      data.registers.forEach(register => {
        const value = numericValue(register.display);
        if (value === null) return;
        definitions.set(`register-${register.register}`, {
          key: `register-${register.register}`,
          register: register.register,
          label: localizeDataText(register.name),
          detail: `R${register.register} · ${localizeDataText(register.group)}`,
          unit: register.unit,
          scale: Number(register.scale) || 1,
          signed: Boolean(register.signed),
          value,
          minimum: null,
          maximum: null,
          available: register.available,
          source: register.available ? `R${register.register}` : t('noData')
        });
      });
      return definitions;
    }

    function renderChartValueList() {
      const host = document.querySelector('#chart-value-list');
      const query = document.querySelector('#chart-search').value.trim().toLowerCase();
      const items = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.unit}`.toLowerCase().includes(query)
      );
      host.innerHTML = items.map(item => `<div class="value-option">
        <div class="value-name">${item.label}<small>${item.detail}</small></div>
        <div class="value-targets">
          <label><input type="checkbox" data-value-key="${item.key}" ${chartSelections.has(item.key) && dashboardSelections.has(item.key) ? 'checked' : ''}> ${t('dashboardChart')}</label>
        </div>
      </div>`).join('');
    }

    function renderGaugePickerList() {
      const host = document.querySelector('#gauge-picker-list');
      const query = document.querySelector('#gauge-picker-search').value.trim().toLowerCase();
      const items = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.unit}`.toLowerCase().includes(query)
      );
      host.innerHTML = items.map(item => `<label class="gauge-picker-option">
        <input type="checkbox" data-picker-value-key="${item.key}" ${dashboardSelections.has(item.key) ? 'checked' : ''}>
        <span class="gauge-picker-name">${item.label}<small>${item.detail}${item.unit ? ` · ${item.unit}` : ''}</small></span>
      </label>`).join('');
    }

    function openGaugePicker() {
      const picker = document.querySelector('#gauge-picker');
      renderGaugePickerList();
      if (typeof picker.showModal === 'function') picker.showModal();
      else picker.setAttribute('open', '');
      window.setTimeout(() => document.querySelector('#gauge-picker-search').focus(), 0);
    }

    function updateChartDefinitions(data) {
      const next = collectChartDefinitions(data);
      const oldSignature = [...chartDefinitions.keys()].join('|');
      const nextSignature = [...next.keys()].join('|');
      chartDefinitions = next;
      if (oldSignature !== nextSignature) {
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
      }
      if (!chartDemoRunning) renderDashboardValues();
    }

    function niceGaugeLimit(value) {
      const positive = Math.max(1, Math.abs(value));
      const magnitude = 10 ** Math.floor(Math.log10(positive));
      const normalized = positive / magnitude;
      const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
      return step * magnitude;
    }

    function dashboardGaugeBounds(item) {
      if (Number.isFinite(item.minimum) && Number.isFinite(item.maximum) && item.maximum > item.minimum) {
        return {minimum: item.minimum, maximum: item.maximum};
      }
      const matchingMeter = chartDefinitions.get(`meter-${item.register}`);
      if (matchingMeter && Number.isFinite(matchingMeter.minimum) && Number.isFinite(matchingMeter.maximum)) {
        return {minimum: matchingMeter.minimum, maximum: matchingMeter.maximum};
      }
      if (item.unit === '%') return {minimum: 0, maximum: 100};

      const value = Number.isFinite(item.value) ? item.value : 0;
      const previousRange = dashboardGaugeRanges.get(item.key);
      if (previousRange && value >= previousRange.minimum && value <= previousRange.maximum) return previousRange;

      const range = value < 0
        ? {minimum: -niceGaugeLimit(Math.abs(value) * 1.2), maximum: niceGaugeLimit(Math.abs(value) * 1.2)}
        : {minimum: 0, maximum: niceGaugeLimit(Math.max(100, value * 1.2))};
      dashboardGaugeRanges.set(item.key, range);
      saveMap('inverter-dashboard-gauge-ranges-v2', dashboardGaugeRanges);
      return range;
    }

    function dashboardGaugeColour(key) {
      const saved = dashboardGaugeColours.get(key);
      if (colours.includes(saved)) return saved;
      const activeColours = [...dashboardSelections]
        .filter(selectedKey => selectedKey !== key)
        .map(selectedKey => dashboardGaugeColours.get(selectedKey));
      const colour = colours.reduce((best, candidate) => {
        const uses = activeColours.filter(value => value === candidate).length;
        const bestUses = activeColours.filter(value => value === best).length;
        return uses < bestUses ? candidate : best;
      }, colours[0]);
      dashboardGaugeColours.set(key, colour);
      saveMap('inverter-dashboard-gauge-colours-v2', dashboardGaugeColours);
      return colour;
    }

    function dashboardGaugeItems() {
      return [...dashboardSelections]
        .filter(key => chartDefinitions.has(key))
        .map(key => {
          const item = chartDefinitions.get(key);
          return {...item, ...dashboardGaugeBounds(item), colour: dashboardGaugeColour(key)};
        });
    }

    function dashboardGaugeSignature(gauges) {
      return `${currentLanguage}|${gauges.map(gauge =>
        `${gauge.key}:${gauge.minimum}:${gauge.maximum}:${gauge.colour}`).join('|')}`;
    }

    function renderDashboardValues() {
      const gauges = dashboardGaugeItems();
      if (!gauges.length) {
        const host = document.querySelector('#gauges');
        host.classList.add('empty-dashboard');
        host.innerHTML = addGaugeMarkup(true);
        host.dataset.keys = `${currentLanguage}|empty`;
        return;
      }
      renderGauges(gauges);
    }

    function renderChartCards() {
      const grid = document.querySelector('#chart-grid');
      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      document.querySelector('#chart-demo-button').disabled = false;
      document.querySelector('#chart-selection-count').textContent =
        selected.length ? t('selectedSummary', {count: selected.length}) : t('noValuesSelected');

      if (!selected.length) {
        grid.innerHTML = `<div class="chart-empty">${t('selectValues')}</div>`;
        return;
      }

      grid.innerHTML = selected.map((key, index) => {
        const item = chartDefinitions.get(key);
        return `<article class="chart-card" style="--accent:${colours[index % colours.length]}">
          <div class="chart-card-head">
            <h3 title="${item.label}">${item.label}</h3>
            <div class="chart-latest" id="latest-${key}">—</div>
          </div>
          <div class="muted">${item.detail}</div>
          <canvas id="chart-${key}" data-chart-key="${key}" aria-label="${t('chartAria', {label: item.label})}"></canvas>
        </article>`;
      }).join('');
      requestAnimationFrame(drawAllCharts);
    }

    function recordChartSamples(data) {
      updateChartDefinitions(data);
      if (chartDemoRunning) {
        if (!document.querySelector('#charts-view').hidden) drawAllCharts();
        return;
      }
      const now = Date.now();
      chartSelections.forEach(key => {
        const item = chartDefinitions.get(key);
        if (!item) return;
        const history = chartHistory.get(key) || [];
        history.push({time: now, value: item.value});
        trimChartHistory(history, now);
        chartHistory.set(key, history);
      });
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    }

    function interpolate(start, end, ratio) {
      return start + (end - start) * Math.max(0, Math.min(1, ratio));
    }

    function realisticDemoScenario(elapsedSeconds) {
      const second = elapsedSeconds % chartWindowSeconds;
      const ripple = Math.sin(second * .37);
      let gridAvailable = true;
      let pvVoltage;
      let pvPower;
      let loadPower;
      let batteryCurrent;
      let batterySoc;
      let statusCode;

      if (second < 30) {
        // Strong solar production: loads are supplied and the battery charges.
        pvVoltage = 326 + ripple * 4;
        pvPower = 6400 + Math.sin(second * .21) * 350;
        loadPower = 2850 + Math.sin(second * .29) * 180;
        batteryCurrent = -(pvPower - loadPower) / 54 * .82;
        batterySoc = 76 + second * .06;
        statusCode = 3;
      } else if (second < 45) {
        // Panels are switched off: voltage, power, and charging current decay together.
        const transition = (second - 30) / 15;
        pvVoltage = interpolate(326, 12, transition);
        pvPower = interpolate(6300, 0, transition);
        loadPower = 2750 + ripple * 120;
        batteryCurrent = interpolate(-52, loadPower / 51.8, transition);
        batterySoc = 77.8 - transition * .15;
        statusCode = batteryCurrent < 0 ? 3 : 2;
      } else if (second < 70) {
        // No panels and no grid: the battery supplies the load.
        gridAvailable = false;
        pvVoltage = Math.max(0, 8 - (second - 45) * .5);
        pvPower = 0;
        loadPower = 2250 + Math.sin(second * .31) * 220;
        batteryCurrent = loadPower / 51.7;
        batterySoc = 77.65 - (second - 45) * .08;
        statusCode = 2;
      } else if (second < 95) {
        // Grid/bypass operation after the grid returns; battery receives a small charge.
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2450 + Math.sin(second * .27) * 160;
        batteryCurrent = -8 + ripple * .8;
        batterySoc = 75.65 + (second - 70) * .025;
        statusCode = 1;
      } else {
        // Panels return and solar production ramps back up.
        const transition = (second - 95) / 25;
        pvVoltage = interpolate(20, 324, transition) + ripple * 2;
        pvPower = interpolate(0, 6100, transition) + ripple * 120;
        loadPower = 2700 + Math.sin(second * .25) * 170;
        batteryCurrent = interpolate(-7, -(pvPower - loadPower) / 54 * .8, transition);
        batterySoc = 76.28 + transition * 1.7;
        statusCode = 3;
      }

      const gridVoltage = gridAvailable ? 230 + Math.sin(second * .19) * 1.4 : 0;
      const gridFrequency = gridAvailable ? 50 + Math.sin(second * .17) * .025 : 0;
      const batteryVoltage = 52.1 + (batterySoc - 75) * .09 - batteryCurrent * .018;
      const batteryTemperature = 29.5 + Math.abs(batteryCurrent) * .055 + Math.sin(second * .08) * .3;
      const inverterTemperature = 33 + loadPower / 1000 * 1.8 + Math.max(0, pvPower) / 1000 * .45;
      const loadPercent = loadPower / 12000 * 100;
      const batteryPower = Math.abs(batteryVoltage * batteryCurrent);

      return {
        statusCode,
        values: new Map([
          [89, gridVoltage], [90, gridVoltage], [91, gridFrequency],
          [92, inverterTemperature], [93, batteryVoltage], [94, loadPercent],
          [129, batteryVoltage], [130, Math.abs(batteryCurrent)],
          [133, batterySoc], [134, batteryTemperature],
          [137, batteryVoltage], [138, batteryCurrent], [139, batterySoc],
          [140, batteryTemperature + .6], [141, 57.1], [144, 11.4],
          [157, statusCode], [158, 190 + statusCode],
          [321, 1], [324, 1], [325, 1], [337, 2], [339, batterySoc],
          [341, Math.max(0, pvVoltage)], [342, batteryVoltage],
          [343, batteryCurrent * 1.06], [344, batteryCurrent * .98],
          [345, 61], [346, 48], [349, 48], [350, -1.5],
          [376, 57.1], [377, 54.4], [378, 80], [379, 80], [383, 58.4],
          [385, 7200], [386, 2160],
          [401, 1], [402, 1], [403, batteryPower],
          [404, batteryVoltage], [405, batteryCurrent],
          [406, batteryTemperature + .6], [407, batterySoc], [408, 100],
          [411, 57.1], [412, 80], [413, batteryPower],
          [415, 20], [416, 50], [417, 90], [449, 584]
        ])
      };
    }

    function demoRawValue(register, value) {
      const scale = Number(register.scale) || 1;
      let raw = Math.round(value / scale);
      if (register.signed && raw < 0) raw += 65536;
      return Math.max(0, Math.min(65534, raw));
    }

    function demoDisplayValue(value, scale) {
      if (scale === .01) return value.toFixed(2);
      if (scale === .1) return value.toFixed(1);
      if (scale === 1) return Math.round(value).toString();
      return Number(value.toFixed(3)).toString();
    }

    function demoStatusText(statusCode) {
      return ({
        1: 'Ймовірно робота від мережі або байпас',
        2: 'Ймовірно робота інвертора від батареї або PV',
        3: 'Ймовірно заряджання або активна робота'
      })[statusCode] || 'Очікування або невідомий стан';
    }

    function trimChartHistory(history, currentTime) {
      const oldestAllowed = currentTime - chartWindowMilliseconds;
      while (history.length && history[0].time < oldestAllowed) history.shift();
    }

    function formatChartTime(timestamp) {
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      return new Date(timestamp).toLocaleTimeString(locale, {
        timeZone: 'Europe/Madrid',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }

    async function fillChartExampleData() {
      if (chartDemoRunning) {
        chartDemoCancelRequested = true;
        return;
      }

      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      const registerKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('register-'));
      const meterKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('meter-'));
      const demoKeys = [...new Set([...registerKeys, ...meterKeys, ...selected])];
      if (!demoKeys.length) return;

      const buttons = document.querySelectorAll('.all-data-demo-button');
      const setButtonState = (text, disabled = false) => buttons.forEach(button => {
        button.textContent = text;
        button.disabled = disabled;
      });
      chartDemoRunning = true;
      chartDemoCancelRequested = false;
      demoKeys.forEach(key => chartHistory.set(key, []));
      if (lastData) render(lastData);
      drawAllCharts();

      try {
        const demoStartedAt = Date.now();
        while (Date.now() - demoStartedAt < chartWindowMilliseconds) {
          const elapsedBeforeWait = Math.floor((Date.now() - demoStartedAt) / 1000);
          setButtonState(t('stopDemo', {
            elapsed: elapsedBeforeWait,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          const selectedIndex = Number(document.querySelector('#poll-rate').value);
          await wait(requestIntervals[selectedIndex] ?? 2000);
          if (chartDemoCancelRequested) break;

          const now = Date.now();
          const elapsedSeconds = Math.min(
            chartWindowSeconds - .001,
            (now - demoStartedAt) / 1000
          );
          const scenario = realisticDemoScenario(elapsedSeconds);
          registerKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const history = chartHistory.get(key) || [];
            const scenarioValue = scenario.values.get(item.register);
            if (Number.isFinite(scenarioValue)) item.value = scenarioValue;
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          meterKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const registerKey = key.replace('meter-', 'register-');
            const registerItem = chartDefinitions.get(registerKey);
            const scenarioValue = scenario.values.get(item.register);
            if (Number.isFinite(scenarioValue)) item.value = scenarioValue;
            else if (registerItem) item.value = registerItem.value;
            if (registerItem) registerItem.value = item.value;
            const history = chartHistory.get(key) || [];
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          demoRegisterRows = lastData ? lastData.registers.map(register => {
            const value = scenario.values.get(register.register);
            if (!Number.isFinite(value)) return register;
            const display = register.register === 157
              ? demoStatusText(scenario.statusCode)
              : demoDisplayValue(value, Number(register.scale) || 1);
            return {
              ...register,
              display,
              raw: demoRawValue(register, value),
              available: true
            };
          }) : [];
          const elapsed = Math.min(
            chartWindowSeconds,
            Math.floor((now - demoStartedAt) / 1000)
          );
          setButtonState(t('stopDemo', {
            elapsed,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          renderDashboardValues();
          renderRegisters(demoRegisterRows);
          if (lastData) renderLcd(lastData, demoRegisterRows);
          drawAllCharts();
        }
      } finally {
        chartDemoRunning = false;
        chartDemoCancelRequested = false;
        demoRegisterRows = null;
        setButtonState(t('runDemo'));
        if (lastData) {
          recordChartSamples(lastData);
          render(lastData);
        }
      }
    }

    function drawChart(canvas, item, history, colour) {
      const width = Math.max(1, canvas.clientWidth);
      const height = canvas.clientHeight || 220;
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * pixelRatio);
      canvas.height = Math.round(height * pixelRatio);
      const context = canvas.getContext('2d');
      context.scale(pixelRatio, pixelRatio);
      context.clearRect(0, 0, width, height);
      const themeStyles = window.getComputedStyle(document.documentElement);
      const mutedColour = themeStyles.getPropertyValue('--muted').trim();
      const gridColour = themeStyles.getPropertyValue('--chart-grid-line').trim();

      const compactChart = width < 420;
      const padding = {
        left: compactChart ? 42 : 48,
        right: compactChart ? 8 : 14,
        top: 16,
        bottom: 28
      };
      const plotWidth = width - padding.left - padding.right;
      const plotHeight = height - padding.top - padding.bottom;
      const values = history.map(point => point.value);
      let minimum = values.length ? Math.min(...values) : 0;
      let maximum = values.length ? Math.max(...values) : 1;
      if (minimum === maximum) {
        const margin = Math.abs(minimum) * .08 || 1;
        minimum -= margin;
        maximum += margin;
      } else {
        const margin = (maximum - minimum) * .1;
        minimum -= margin;
        maximum += margin;
      }

      context.font = '10px system-ui';
      context.fillStyle = mutedColour;
      context.strokeStyle = gridColour;
      context.lineWidth = 1;
      for (let line = 0; line <= 4; line += 1) {
        const ratio = line / 4;
        const y = padding.top + plotHeight * ratio;
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();
        const label = maximum - (maximum - minimum) * ratio;
        context.fillText(Number(label.toFixed(2)).toString(), 3, y + 3);
      }

      const endTime = history.length ? history.at(-1).time : Date.now();
      const startTime = endTime - chartWindowMilliseconds;
      const timeTickCount = width < 340 ? 2 : 3;
      for (let tick = 0; tick <= timeTickCount; tick += 1) {
        const ratio = tick / timeTickCount;
        const x = padding.left + plotWidth * ratio;
        context.beginPath();
        context.moveTo(x, padding.top);
        context.lineTo(x, padding.top + plotHeight);
        context.stroke();
        context.fillStyle = mutedColour;
        context.textAlign = tick === 0 ? 'left' : tick === timeTickCount ? 'right' : 'center';
        context.fillText(
          formatChartTime(startTime + (endTime - startTime) * ratio),
          x,
          height - 7
        );
      }

      if (history.length) {
        context.strokeStyle = colour;
        context.lineWidth = 2.5;
        context.lineJoin = 'round';
        context.lineCap = 'round';
        context.beginPath();
        history.forEach((point, index) => {
          const timeRatio = Math.max(
            0,
            Math.min(1, (point.time - startTime) / chartWindowMilliseconds)
          );
          const x = padding.left + plotWidth * timeRatio;
          const y = padding.top + plotHeight * (maximum - point.value) / (maximum - minimum);
          if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
        });
        context.stroke();
      }

      const latest = document.querySelector(`#latest-${item.key}`);
      if (latest) latest.textContent = history.length
        ? `${Number(history.at(-1).value.toFixed(2))} ${item.unit}`.trim()
        : t('waiting');
    }

    function drawAllCharts() {
      document.querySelectorAll('canvas[data-chart-key]').forEach((canvas, index) => {
        const key = canvas.dataset.chartKey;
        const item = chartDefinitions.get(key);
        if (item) drawChart(canvas, item, chartHistory.get(key) || [], colours[index % colours.length]);
      });
    }

    function scaleNumber(value, range) {
      if (Math.abs(value) >= 1000) {
        const compact = value / 1000;
        return `${Number(compact.toFixed(compact % 1 ? 1 : 0))}k`;
      }
      const decimals = range <= 20 ? 1 : 0;
      return Number(value.toFixed(decimals)).toString();
    }

    function scaleMarkup(meter) {
      const centreX = 120;
      const centreY = 120;
      const range = meter.maximum - meter.minimum;
      let markup = '';

      for (let index = 0; index <= 20; index += 1) {
        const angle = Math.PI + (Math.PI * index / 20);
        const major = index % 5 === 0;
        const outerRadius = 106;
        const innerRadius = major ? 94 : 99;
        const x1 = centreX + Math.cos(angle) * innerRadius;
        const y1 = centreY + Math.sin(angle) * innerRadius;
        const x2 = centreX + Math.cos(angle) * outerRadius;
        const y2 = centreY + Math.sin(angle) * outerRadius;
        markup += `<line class="tick${major ? ' major' : ''}" x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"/>`;

        if (major) {
          const labelRadius = 81;
          const labelX = centreX + Math.cos(angle) * labelRadius;
          const labelY = centreY + Math.sin(angle) * labelRadius;
          const value = meter.minimum + range * index / 20;
          markup += `<text class="scale-label" x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}">${scaleNumber(value, range)}</text>`;
        }
      }
      return markup;
    }

    function addGaugeMarkup(empty = false) {
      return `<button class="add-gauge-card" type="button" data-open-gauge-picker aria-label="${t('addGauge')}">
        <span class="add-gauge-plus">+</span>
        <span class="add-gauge-label">${empty ? t('emptyDashboard') : t('addGauge')}</span>
      </button>`;
    }

    function gaugeMarkup(meter) {
      const label = localizeDataText(meter.label);
      return `<article class="gauge-card" draggable="true" data-dashboard-key="${meter.key}" style="--accent:${meter.colour}">
        <div class="gauge-actions">
          <button class="drag-handle" type="button" draggable="false" title="${t('dragGauge')}" aria-label="${t('dragGauge')}">⠿</button>
          <button class="remove-value" type="button" draggable="false" data-remove-dashboard="${meter.key}" title="${t('removeDashboard')}" aria-label="${t('removeDashboard')}">×</button>
        </div>
        <div class="gauge-title">${label}</div>
        <svg viewBox="0 0 240 145" role="img" aria-label="${label}">
          <path class="track" d="M20 120 A100 100 0 0 1 220 120"/>
          <path class="progress" d="M20 120 A100 100 0 0 1 220 120"/>
          ${scaleMarkup(meter)}
          <line class="needle" x1="120" y1="120" x2="120" y2="33"/>
          <circle class="hub" cx="120" cy="120" r="7"/>
        </svg>
        <div class="reading"><span class="trend flat">•</span><span class="value">—</span><span class="unit">${meter.unit}</span></div>
        <div class="source">${meter.detail}</div>
      </article>`;
    }

    function renderGauges(meters) {
      const host = document.querySelector('#gauges');
      host.classList.remove('empty-dashboard');
      const signature = dashboardGaugeSignature(meters);
      if (host.dataset.keys !== signature) {
        host.dataset.keys = signature;
        host.innerHTML = meters.map(gaugeMarkup).join('') + addGaugeMarkup();
      }
      meters.forEach(meter => {
        const card = host.querySelector(`[data-dashboard-key="${meter.key}"]`);
        if (!card) return;
        const hasValue = Number.isFinite(meter.value);
        const value = hasValue ? meter.value : 0;
        const ratio = hasValue ? Math.max(0, Math.min(1, (value - meter.minimum) / (meter.maximum - meter.minimum))) : 0;
        const needleTransform = `rotate(${-90 + ratio * 180}deg)`;
        const progressOffset = `${283 * (1 - ratio)}`;
        const valueText = hasValue ? Number(value.toFixed(2)).toString() : '—';
        const needle = card.querySelector('.needle');
        const progress = card.querySelector('.progress');
        const valueElement = card.querySelector('.value');
        const sourceElement = card.querySelector('.source');

        if (needle.style.transform !== needleTransform) needle.style.transform = needleTransform;
        if (progress.style.strokeDashoffset !== progressOffset) progress.style.strokeDashoffset = progressOffset;
        if (valueElement.textContent !== valueText) valueElement.textContent = valueText;
        const localizedSource = meter.available === false ? t('noData') : localizeDataText(meter.source || meter.detail);
        if (sourceElement.textContent !== localizedSource) sourceElement.textContent = localizedSource;

        const old = previous.get(meter.key);
        const trend = card.querySelector('.trend');
        if (old === undefined) {
          trend.className = 'trend flat';
          trend.textContent = '•';
        } else if (hasValue && value !== old) {
          const up = value > old;
          trend.className = `trend ${up ? 'up' : 'down'}`;
          trend.textContent = up ? '↑' : '↓';
        }
        if (hasValue) previous.set(meter.key, value);
      });
    }

    function renderRegisters(registers) {
      const query = document.querySelector('#search').value.trim().toLowerCase();
      const shown = registers.filter(item =>
        `${item.register} ${localizeDataText(item.group)} ${localizeDataText(item.name)} ${localizeDataText(item.display)} ${item.unit}`.toLowerCase().includes(query)
      );
      const available = registers.filter(item => item.available).length;
      document.querySelector('#register-count').textContent =
        t('registerCount', {
          available,
          waiting: registers.length - available,
          shown: shown.length
        });
      document.querySelector('#registers').innerHTML = shown.map(item => `<tr class="${item.available ? '' : 'unavailable'}">
        <td>R${item.register}</td><td>${localizeDataText(item.group)}</td><td>${localizeDataText(item.name)}</td>
        <td>${localizeDataText(item.display)} ${item.unit}</td><td>${item.raw ?? '—'}</td></tr>`).join('');
    }

    function formatFileSize(bytes) {
      const value = Number(bytes || 0);
      if (value < 1024) return `${value} B`;
      if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
      return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }

    function renderRegisterLog(log = {}) {
      const status = document.querySelector('#register-log-status');
      const active = Boolean(log.active);
      status.classList.toggle('active', active && !log.error);
      status.classList.toggle('error-text', Boolean(log.error));
      if (log.error) {
        status.textContent = t('registerLogError', {error: localizeDataText(log.error)});
      } else if (active) {
        status.textContent = t('registerLogActive', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else if (log.available) {
        status.textContent = t('registerLogStopped', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else {
        status.textContent = t('registerLogIdle');
      }
      document.querySelector('#register-log-start').disabled = active;
      document.querySelector('#register-log-stop').disabled = !active;
      document.querySelector('#register-log-note').disabled = !active;
      document.querySelector('#register-log-mark').disabled = !active;
      document.querySelector('#register-log-download').hidden = !log.available;
    }

    async function updateRegisterLog(action, note = '') {
      const buttons = document.querySelectorAll('#register-log-start, #register-log-stop, #register-log-mark');
      buttons.forEach(button => button.disabled = true);
      try {
        const response = await fetch('/api/register-log', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({action, note})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        if (lastData) lastData.register_log = result;
        if (action === 'mark') document.querySelector('#register-log-note').value = '';
        renderRegisterLog(result);
      } catch (error) {
        const status = document.querySelector('#register-log-status');
        status.className = 'logger-status error-text';
        status.textContent = t('registerLogRequestError', {error: localizeDataText(error.message)});
        const active = Boolean(lastData?.register_log?.active);
        document.querySelector('#register-log-start').disabled = active;
        document.querySelector('#register-log-stop').disabled = !active;
        document.querySelector('#register-log-mark').disabled = !active;
      }
    }

    function renderLcd(data, registers = data.registers || []) {
      const byNumber = new Map(registers.map(register => [register.register, register]));
      const firstRegister = numbers => numbers
        .map(number => byNumber.get(number))
        .find(register => register?.available);
      const numberValue = numbers => {
        const register = firstRegister(numbers);
        return register ? numericValue(register.display) : null;
      };
      const rawValue = (numbers, scale = 1) => {
        const register = firstRegister(numbers);
        const raw = Number(register?.raw);
        return Number.isFinite(raw) && raw !== 65535 ? raw * scale : null;
      };
      const textValue = numbers => {
        const register = firstRegister(numbers);
        return register ? localizeDataText(register.display) : t('noData');
      };
      const reading = (value, unit, digits = 1) =>
        Number.isFinite(value) ? `${value.toFixed(digits)} ${unit}`.trim() : t('noData');
      const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
      };

      const gridVoltage = numberValue([89]);
      const frequency = numberValue([91]);
      const pvVoltage = numberValue([341]);
      const batteryVoltage = numberValue([137, 404, 342, 129, 93]);
      const batteryCurrent = numberValue([138, 405, 344, 343, 130]);
      const batterySoc = numberValue([139, 407, 339, 133]);
      const batteryTemperature = numberValue([140, 406, 134]);
      const inverterTemperature = numberValue([92]);
      const maximumChargeVoltage = numberValue([141, 411, 376, 377]);
      const currentLimit = numberValue([412, 378, 379]);
      const loadPercent = numberValue([94]);
      const power = numberValue([413, 385, 386]);
      const statusText = textValue([157]);
      const batteryState = !Number.isFinite(batteryCurrent) || Math.abs(batteryCurrent) < .3
        ? t('batteryIdle')
        : batteryCurrent < 0 ? t('charging') : t('discharging');

      setText('#lcd-mode', chartDemoRunning ? t('demoMode') : data.online ? t('online') : t('offline'));
      setText('#lcd-grid', reading(gridVoltage, 'V'));
      setText('#lcd-frequency', reading(frequency, 'Hz', 2));
      setText('#lcd-pv', reading(pvVoltage, 'V', 2));
      setText('#lcd-battery-voltage', reading(batteryVoltage, 'V'));
      setText('#lcd-battery-current', reading(batteryCurrent, 'A'));
      setText('#lcd-soc', reading(batterySoc, '%', 0));
      setText('#lcd-temperature', reading(batteryTemperature, '°C'));
      setText('#lcd-inverter-temperature', reading(inverterTemperature, '°C'));
      setText('#lcd-charge-voltage', reading(maximumChargeVoltage, 'V'));
      setText('#lcd-current-limit', reading(currentLimit, 'A'));
      setText('#lcd-load', reading(loadPercent, '%', 0));
      setText('#lcd-power', reading(power, 'W', 0));
      setText('#lcd-battery-state', batteryState);
      setText('#lcd-system-status', statusText);
      setText('#lcd-status-line', `${data.identifier || t('unknownDevice')} · ${t('updated', {time: data.updated_at})}`);

      const pages = [
        {
          code: 'LCD', title: t('mainDisplay'),
          label1: t('batteryVoltage'), value1: reading(batteryVoltage, 'V'),
          label2: t('pvInput'), value2: reading(pvVoltage, 'V', 2), help: t('lcdMainPageHelp')
        },
        {
          code: 'P1', title: t('dailyPvEnergy'),
          label1: t('dailyPvEnergy'), value1: t('noData'), label2: '', value2: '', help: t('lcdP1Help')
        },
        {
          code: 'P2', title: t('totalPvEnergy'),
          label1: t('totalPvEnergy'), value1: t('noData'), label2: '', value2: '', help: t('lcdP2Help')
        },
        {
          code: 'P3', title: t('batteryState'),
          label1: t('batteryVoltage'), value1: reading(batteryVoltage, 'V'),
          label2: t('batteryCurrent'), value2: reading(batteryCurrent, 'A'), help: t('lcdP3Help')
        },
        {
          code: 'P4', title: t('batteryState'),
          label1: t('batteryTemperature'), value1: reading(batteryTemperature, '°C'),
          label2: t('batterySoc'), value2: reading(batterySoc, '%', 0), help: t('lcdP4Help')
        },
        {
          code: 'P5', title: t('ratedCapacity'),
          label1: t('ratedCapacity'), value1: reading(rawValue([408]), 'Ah', 0),
          label2: t('remainingCapacity'), value2: reading(rawValue([409], .1), 'Ah'), help: t('lcdP5Help')
        },
        {
          code: 'P6', title: t('maxChargeVoltage'),
          label1: t('maxChargeVoltage'), value1: reading(maximumChargeVoltage, 'V'),
          label2: t('minDischargeVoltage'), value2: reading(numberValue([410, 142]), 'V'), help: t('lcdP6Help')
        },
        {
          code: 'P7', title: t('currentLimit'),
          label1: t('maxChargeCurrent'), value1: reading(currentLimit, 'A'),
          label2: t('maxDischargeCurrent'), value2: reading(rawValue([413], .1), 'A'), help: t('lcdP7Help')
        },
        {
          code: 'P8', title: t('alarmFault'),
          label1: t('faultCode'), value1: t('noData'),
          label2: t('alarmCode'), value2: t('noData'), help: t('lcdP8Help')
        },
        {
          code: 'P9', title: t('firmwareVersion'),
          label1: t('firmwareVersion'), value1: textValue([17]),
          label2: t('systemStatus'), value2: textValue([18]), help: t('lcdP9Help')
        }
      ];
      const page = pages[lcdPageIndex] || pages[0];
      setText('#lcd-page-code', page.code);
      setText('#lcd-page-title', page.title);
      setText('#lcd-page-label-1', page.label1);
      setText('#lcd-page-value-1', page.value1);
      setText('#lcd-page-label-2', page.label2);
      setText('#lcd-page-value-2', page.value2);
      setText('#lcd-page-description', lcdEnterNotice ? t('settingsReadOnly') : page.help);
      document.querySelector('#lcd-page-reading-2').hidden = !page.label2;

      const active = (selector, enabled) =>
        document.querySelector(selector)?.classList.toggle('active', Boolean(enabled));
      active('#lcd-grid-node', Number.isFinite(gridVoltage) && gridVoltage > 40);
      active('#lcd-grid-arrow', Number.isFinite(gridVoltage) && gridVoltage > 40);
      active('#lcd-inverter-node', chartDemoRunning || data.online);
      active('#lcd-load-node', Number.isFinite(loadPercent) && loadPercent > 0);
      active('#lcd-load-arrow', Number.isFinite(loadPercent) && loadPercent > 0);
      active('#lcd-pv-card', Number.isFinite(pvVoltage) && pvVoltage > 20);
      active('#lcd-battery-card', Number.isFinite(batteryVoltage) && batteryVoltage > 20);
      active('#lcd-soc-card', Number.isFinite(batterySoc));
    }

    function render(data) {
      lastData = data;
      document.querySelector('#identifier').textContent = data.identifier || t('unknownDevice');
      const status = document.querySelector('#status');
      status.classList.toggle('online', chartDemoRunning || (data.online && !data.paused));
      status.classList.toggle('paused', !chartDemoRunning && data.paused);
      status.querySelector('.status-label').textContent =
        chartDemoRunning
          ? t('demoMode')
          : data.paused ? t('paused') : data.online ? t('online') : t('offline');
      const appToggle = document.querySelector('#app-toggle');
      appToggle.textContent = data.paused ? t('startMonitoring') : t('stopMonitoring');
      appToggle.classList.toggle('start', data.paused);
      document.querySelector('#updated').textContent =
        t('updated', {time: localizeDataText(data.updated_at)});
      document.querySelector('#cycle').textContent =
        data.paused
          ? t('cyclePaused', {cycle: data.cycle_id})
          : t('cycleReads', {
              cycle: data.cycle_id,
              seconds: data.cycle_seconds.toFixed(2),
              reads: data.successful
            });
      const totalVisitors = Number(data.site_visits || 0);
      const numberLocale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      document.querySelector('#site-visits').textContent =
        t('visitors', {
          count: totalVisitors.toLocaleString(numberLocale),
          date: data.site_visits_date
        });
      if (lastLoggedSiteVisits !== totalVisitors) {
        const visitDetails = {};
        visitDetails[t('totalVisitorsLabel')] = totalVisitors;
        visitDetails[t('dateLabel')] = data.site_visits_date;
        visitDetails[t('openedLabel')] = new Date().toISOString();
        visitDetails[t('referrerLabel')] = document.referrer || t('direct');
        visitDetails[t('browserLanguageLabel')] = navigator.language;
        visitDetails[t('browserLabel')] = navigator.userAgent;
        visitDetails[t('viewportLabel')] = `${window.innerWidth}x${window.innerHeight}`;
        console.log(t('visitConsole'), visitDetails);
        lastLoggedSiteVisits = totalVisitors;
      }
      document.querySelector('#poll-rate').value = data.poll_rate_index;
      document.querySelector('#read-mode').value = data.read_mode;
      const error = document.querySelector('#error');
      const connectionError = chartDemoRunning ? '' : data.error;
      error.textContent = connectionError
        ? t('connectionError', {error: localizeDataText(data.error)})
        : '';
      error.classList.toggle('show', Boolean(connectionError));
      renderRegisterLog(data.register_log);
      renderRegisters(data.registers);
      renderLcd(data, chartDemoRunning && demoRegisterRows ? demoRegisterRows : data.registers);
      updateChartDefinitions(data);
    }

    async function refresh() {
      if (refreshInFlight) return;
      refreshInFlight = true;
      refreshController = new AbortController();
      try {
        const response = await fetch('/api/state', {
          cache: 'no-store',
          signal: refreshController.signal
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        lastData = data;
        recordChartSamples(data);
        if (!chartDemoRunning) render(data);
      } catch (error) {
        if (error.name === 'AbortError') return;
        if (chartDemoRunning) return;
        const box = document.querySelector('#error');
        box.textContent = t('connectionLost', {error: error.message});
        box.classList.add('show');
      } finally {
        refreshInFlight = false;
        refreshController = null;
        if (!lastData?.paused) {
          scheduleRefresh();
        } else if (refreshTimer !== null) {
          window.clearTimeout(refreshTimer);
          refreshTimer = null;
        }
      }
    }

    function scheduleRefresh(delay = null) {
      if (refreshTimer !== null) window.clearTimeout(refreshTimer);
      const selectedIndex = Number(document.querySelector('#poll-rate').value);
      const milliseconds = delay ?? requestIntervals[selectedIndex] ?? 2000;
      refreshTimer = window.setTimeout(refresh, milliseconds);
    }

    async function updateSetting(setting, value) {
      await fetch('/api/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({[setting]: value})
      });
      if (setting === 'paused' && value === true) {
        if (refreshTimer !== null) window.clearTimeout(refreshTimer);
        refreshTimer = null;
        refreshController?.abort();
      } else {
        scheduleRefresh(0);
      }
    }

    function wait(milliseconds) {
      return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

    function showView(view) {
      currentView = ['dashboard', 'charts', 'lcd'].includes(view) ? view : 'dashboard';
      document.querySelector('#dashboard-view').hidden = currentView !== 'dashboard';
      document.querySelector('#charts-view').hidden = currentView !== 'charts';
      document.querySelector('#lcd-view').hidden = currentView !== 'lcd';
      document.querySelectorAll('.view-tab').forEach(button => {
        const active = button.dataset.view === currentView;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
      });
      if (currentView === 'charts') requestAnimationFrame(drawAllCharts);
    }

    function handleLcdKey(key) {
      if (key === 'escape') {
        lcdPageIndex = 0;
        lcdEnterNotice = false;
      } else if (key === 'up') {
        lcdPageIndex = lcdPageIndex <= 1 ? 9 : lcdPageIndex - 1;
        lcdEnterNotice = false;
      } else if (key === 'down') {
        lcdPageIndex = lcdPageIndex === 0 || lcdPageIndex >= 9 ? 1 : lcdPageIndex + 1;
        lcdEnterNotice = false;
      } else if (key === 'enter') {
        lcdEnterNotice = true;
      } else {
        return;
      }
      if (lastData) {
        renderLcd(lastData, chartDemoRunning && demoRegisterRows ? demoRegisterRows : lastData.registers);
      }
    }

    function applyLanguage(language, save = true) {
      currentLanguage = ['uk', 'ru', 'en'].includes(language) ? language : 'uk';
      document.documentElement.lang = currentLanguage;
      document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
      });
      document.querySelectorAll('[data-i18n-aria]').forEach(element => {
        element.setAttribute('aria-label', t(element.dataset.i18nAria));
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
      });
      document.querySelectorAll('.language-option').forEach(button => {
        const active = button.dataset.language === currentLanguage;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      document.querySelector('#theme-name').textContent =
        document.documentElement.dataset.theme === 'light' ? t('themeLight') : t('themeDark');
      showView(currentView);
      if (!chartDemoRunning) {
        document.querySelectorAll('.all-data-demo-button').forEach(button => {
          button.textContent = t('runDemo');
        });
      }
      if (save) {
        try {
          window.localStorage.setItem('solar-invertor-language', currentLanguage);
        } catch {
          // Language switching still works when browser storage is unavailable.
        }
      }
      lastLoggedSiteVisits = null;
      if (lastData) {
        document.querySelector('#gauges').innerHTML = '';
        render(lastData);
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
        renderDashboardValues();
      } else {
        document.querySelector('#app-toggle').textContent = t('stopMonitoring');
        document.querySelector('#status .status-label').textContent = t('offline');
        document.querySelector('#cycle').textContent = t('cycleInitial');
        document.querySelector('#site-visits').textContent = t('visitorsInitial');
        document.querySelector('#updated').textContent = t('notUpdated');
        renderChartCards();
      }
      requestAnimationFrame(drawAllCharts);
    }

    function initialLanguage() {
      try {
        const savedLanguage = window.localStorage.getItem('solar-invertor-language');
        if (['uk', 'ru', 'en'].includes(savedLanguage)) return savedLanguage;
      } catch {
        // Use Ukrainian when browser storage is unavailable.
      }
      return 'uk';
    }

    function applyTheme(theme, save = true) {
      const selectedTheme = theme === 'light' ? 'light' : 'dark';
      document.documentElement.dataset.theme = selectedTheme;
      document.querySelector('#theme-toggle').checked = selectedTheme === 'light';
      document.querySelector('#theme-name').textContent =
        selectedTheme === 'light' ? t('themeLight') : t('themeDark');
      if (save) {
        try {
          window.localStorage.setItem('inverter-theme', selectedTheme);
        } catch {
          // Theme still changes when browser storage is unavailable.
        }
      }
      requestAnimationFrame(drawAllCharts);
    }

    function initialTheme() {
      try {
        const savedTheme = window.localStorage.getItem('inverter-theme');
        if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme;
      } catch {
        // Fall through to the system preference.
      }
      return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    applyTheme(initialTheme(), false);
    applyLanguage(initialLanguage(), false);

    document.querySelector('#poll-rate').addEventListener('change', event =>
      updateSetting('poll_rate_index', Number(event.target.value)));
    document.querySelector('#read-mode').addEventListener('change', event =>
      updateSetting('read_mode', event.target.value));
    document.querySelector('#demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#chart-demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#manage-values-button').addEventListener('click', openGaugePicker);
    document.querySelector('#register-log-start').addEventListener('click', () => updateRegisterLog('start'));
    document.querySelector('#register-log-stop').addEventListener('click', () => updateRegisterLog('stop'));
    document.querySelector('#register-log-mark').addEventListener('click', () =>
      updateRegisterLog('mark', document.querySelector('#register-log-note').value));
    document.querySelector('#register-log-note').addEventListener('keydown', event => {
      if (event.key === 'Enter') updateRegisterLog('mark', event.currentTarget.value);
    });
    document.querySelector('#search').addEventListener('input', () =>
      demoRegisterRows
        ? renderRegisters(demoRegisterRows)
        : lastData && renderRegisters(lastData.registers));
    document.querySelector('.view-tabs').addEventListener('click', event => {
      const tab = event.target.closest('.view-tab[data-view]');
      if (tab) showView(tab.dataset.view);
    });
    document.querySelector('.lcd-controls').addEventListener('click', event => {
      const button = event.target.closest('[data-lcd-key]');
      if (button) handleLcdKey(button.dataset.lcdKey);
    });
    window.addEventListener('keydown', event => {
      if (currentView !== 'lcd' || event.target?.closest?.('input, select, textarea')) return;
      const key = ({Escape:'escape', ArrowUp:'up', ArrowDown:'down', Enter:'enter'})[event.key];
      if (!key) return;
      event.preventDefault();
      handleLcdKey(key);
    });
    document.querySelector('#app-toggle').addEventListener('click', async event => {
      if (!lastData) return;
      const toggleButton = event.currentTarget;
      const paused = !lastData.paused;
      lastData.paused = paused;
      render(lastData);
      toggleButton.disabled = true;
      try {
        await updateSetting('paused', paused);
      } finally {
        toggleButton.disabled = false;
      }
    });
    document.querySelector('#theme-toggle').addEventListener('change', event =>
      applyTheme(event.target.checked ? 'light' : 'dark'));
    document.querySelector('.language-switch').addEventListener('click', event => {
      const button = event.target.closest('button[data-language]');
      if (button) applyLanguage(button.dataset.language);
    });
    document.querySelector('#chart-search').addEventListener('input', renderChartValueList);
    document.querySelector('#chart-value-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.valueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderGaugePickerList();
    });
    document.querySelector('#gauge-picker-search').addEventListener('input', renderGaugePickerList);
    document.querySelector('#gauge-picker-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-picker-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.pickerValueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
    });
    document.querySelector('[data-close-gauge-picker]').addEventListener('click', () =>
      document.querySelector('#gauge-picker').close());
    document.querySelector('#gauge-picker').addEventListener('click', event => {
      if (event.target === event.currentTarget) event.currentTarget.close();
    });
    const gaugeHost = document.querySelector('#gauges');
    let draggedGauge = null;
    let pointerDraggedGauge = null;
    let pointerDragHandle = null;

    function saveDashboardOrderFromCards() {
      const orderedKeys = [...gaugeHost.querySelectorAll('[data-dashboard-key]')]
        .map(card => card.dataset.dashboardKey)
        .filter(key => dashboardSelections.has(key));
      dashboardSelections.clear();
      orderedKeys.forEach(key => dashboardSelections.add(key));
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      gaugeHost.dataset.keys = dashboardGaugeSignature(dashboardGaugeItems());
    }

    function placeGaugeAtPointer(card, target, clientX, clientY) {
      gaugeHost.querySelectorAll('.drag-target').forEach(item => item.classList.remove('drag-target'));
      if (!target || target === card || !gaugeHost.contains(target)) return;
      target.classList.add('drag-target');
      const bounds = target.getBoundingClientRect();
      const cardBounds = card.getBoundingClientRect();
      const sameRow = Math.abs(bounds.top - cardBounds.top) < bounds.height / 2;
      const placeAfter = sameRow
        ? clientX > bounds.left + bounds.width / 2
        : clientY > bounds.top + bounds.height / 2;
      target[placeAfter ? 'after' : 'before'](card);
    }

    gaugeHost.addEventListener('dragstart', event => {
      const card = event.target.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      draggedGauge = card;
      card.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.dataset.dashboardKey);
    });
    gaugeHost.addEventListener('dragover', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      const target = event.target.closest('.gauge-card[data-dashboard-key]');
      placeGaugeAtPointer(draggedGauge, target, event.clientX, event.clientY);
    });
    gaugeHost.addEventListener('drop', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      saveDashboardOrderFromCards();
    });
    gaugeHost.addEventListener('dragend', () => {
      gaugeHost.querySelectorAll('.dragging, .drag-target').forEach(card =>
        card.classList.remove('dragging', 'drag-target'));
      draggedGauge = null;
    });

    gaugeHost.addEventListener('pointerdown', event => {
      const handle = event.target.closest('.drag-handle');
      if (!handle || event.button !== 0 || event.isPrimary === false) return;
      const card = handle.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      event.preventDefault();
      pointerDraggedGauge = card;
      pointerDragHandle = handle;
      card.classList.add('pointer-dragging');
      handle.setPointerCapture(event.pointerId);
    });

    gaugeHost.addEventListener('pointermove', event => {
      if (!pointerDraggedGauge || !pointerDragHandle) return;
      event.preventDefault();
      if (event.clientY < 70) window.scrollBy(0, -14);
      if (event.clientY > window.innerHeight - 70) window.scrollBy(0, 14);

      const previousVisibility = pointerDraggedGauge.style.visibility;
      pointerDraggedGauge.style.visibility = 'hidden';
      const elementBelow = document.elementFromPoint(event.clientX, event.clientY);
      pointerDraggedGauge.style.visibility = previousVisibility;
      const target = elementBelow?.closest('.gauge-card[data-dashboard-key]') || null;
      placeGaugeAtPointer(pointerDraggedGauge, target, event.clientX, event.clientY);
    });

    function finishPointerGaugeDrag(event) {
      if (!pointerDraggedGauge) return;
      if (pointerDragHandle?.hasPointerCapture(event.pointerId)) {
        pointerDragHandle.releasePointerCapture(event.pointerId);
      }
      pointerDraggedGauge.classList.remove('pointer-dragging');
      gaugeHost.querySelectorAll('.drag-target').forEach(card => card.classList.remove('drag-target'));
      pointerDraggedGauge = null;
      pointerDragHandle = null;
      saveDashboardOrderFromCards();
    }

    gaugeHost.addEventListener('pointerup', finishPointerGaugeDrag);
    gaugeHost.addEventListener('pointercancel', finishPointerGaugeDrag);

    gaugeHost.addEventListener('click', event => {
      if (event.target.closest('[data-open-gauge-picker]')) {
        openGaugePicker();
        return;
      }
      const button = event.target.closest('button[data-remove-dashboard]');
      if (!button) return;
      const key = button.dataset.removeDashboard;
      dashboardSelections.delete(key);
      chartSelections.delete(key);
      chartHistory.delete(key);
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
      renderGaugePickerList();
    });
    window.addEventListener('resize', () => {
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    });
    const initialData = /*__INITIAL_STATE__*/null;
    if (initialData) {
      lastData = initialData;
      render(initialData);
      recordChartSamples(initialData);
      if (!initialData.paused) {
        window.addEventListener('load', () => scheduleRefresh(), {once: true});
      }
    } else {
      refresh();
    }
    document.documentElement.classList.remove('booting');
  </script>
</body>
</html>
"""


def web_state() -> dict[str, Any]:
    """Return a JSON-safe snapshot for the browser."""
    with state_lock:
        snapshot = dict(state)
        values = dict(state["values"])

    meters = []
    for register, fallbacks, label, minimum, maximum, unit in METER_DEFINITIONS:
        value, source = meter_value(values, register, fallbacks)
        if value is None:
            value = 0.0
            source = "Немає даних mbpoll"
        meters.append({
            "register": register,
            "label": label,
            "minimum": minimum,
            "maximum": maximum,
            "unit": unit,
            "value": value,
            "source": source,
        })

    registers = []
    all_registers = sorted(set(KNOWN_REGISTERS) | set(values))
    for register in all_registers:
        raw = values.get(register)
        name, scale, unit, signed, group = REGISTER_CONFIG.get(
            register, (f"Регістр {register}", 1.0, "", False, "Сире")
        )
        if raw is None:
            display = "0"
        else:
            name, display, unit, _, group = normalize(register, raw)
        registers.append({
            "register": register,
            "group": group,
            "name": name,
            "display": display,
            "unit": unit,
            "scale": scale,
            "signed": signed,
            "raw": raw,
            "available": raw is not None,
        })

    return {
        "online": bool(snapshot["online"]),
        "updated_at": snapshot["updated_at"],
        "cycle_seconds": snapshot["cycle_seconds"],
        "cycle_id": snapshot["cycle_id"],
        "poll_rate_index": snapshot["poll_rate_index"],
        "read_mode": snapshot["read_mode"],
        "requests": snapshot["requests"],
        "successful": snapshot["successful"],
        "failed": snapshot["ошибок"],
        "error": snapshot["error"],
        "identifier": snapshot["identifier"],
        "paused": bool(snapshot["paused"]),
        "site_visits": site_visit_total,
        "site_visits_date": datetime.now(MADRID_TIME_ZONE).strftime("%d.%m.%Y"),
        "register_log": register_log_status(),
        "meters": meters,
        "registers": registers,
    }


def initialise_statistics() -> None:
    """Create and load the privacy-friendly persistent page-view counter."""
    global site_visit_total, stats_error
    try:
        STATS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS site_counters (
                    name TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO site_counters (name, value)
                VALUES ('page_views', 0)
                """
            )
            site_visit_total = int(
                connection.execute(
                    "SELECT value FROM site_counters WHERE name = 'page_views'"
                ).fetchone()[0]
            )
            connection.commit()
        stats_error = ""
    except (OSError, sqlite3.Error) as error:
        stats_error = str(error)


def increment_site_visits() -> None:
    """Count one dashboard HTML page load without storing visitor information."""
    global site_visit_total, stats_error
    try:
        with stats_lock, closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            connection.execute(
                """
                UPDATE site_counters
                SET value = value + 1
                WHERE name = 'page_views'
                """
            )
            site_visit_total = int(
                connection.execute(
                    "SELECT value FROM site_counters WHERE name = 'page_views'"
                ).fetchone()[0]
            )
            connection.commit()
        stats_error = ""
    except sqlite3.Error as error:
        stats_error = str(error)


def visitor_was_counted(cookie_header: str) -> bool:
    """Check the anonymous first-visit cookie without identifying the visitor."""
    try:
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        return cookie.get(COUNTED_VISITOR_COOKIE, "").value == "1"
    except (AttributeError, ValueError):
        return False


def safe_console_print(message: str) -> None:
    """Print localized text without failing on a legacy Windows code page."""
    console_encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_message = message.encode(
        console_encoding, errors="backslashreplace"
    ).decode(console_encoding)
    print(safe_message, flush=True)


def log_visit_to_console(
    handler: BaseHTTPRequestHandler, new_visitor: bool
) -> None:
    """Write request details to the private server terminal only."""
    peer = str(handler.client_address[0])
    forwarded = handler.headers.get("X-Forwarded-For", "")
    source = (
        forwarded.split(",", 1)[0].strip()
        if peer in {"127.0.0.1", "::1"} and forwarded
        else peer
    )
    details = {
        "подія": "відвідування_панелі",
        "дата": datetime.now(MADRID_TIME_ZONE).isoformat(timespec="seconds"),
        "усього_відвідувачів": site_visit_total,
        "новий_відвідувач": new_visitor,
        "джерело": source[:100],
        "ідентифікатор": (
            handler.headers.get("Tailscale-User-Login")
            or handler.headers.get("Tailscale-User-Name")
            or "публічний/анонімний"
        )[:160],
        "джерело_переходу": handler.headers.get("Referer", "прямий перехід")[:500],
        "браузер": handler.headers.get("User-Agent", "невідомо")[:500],
    }
    message = (
        "ВІДВІДУВАЧ "
        + json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    )
    safe_console_print(message)


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve the dashboard and its small JSON API."""

    def send_content(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # Browsers and reverse proxies may cancel an obsolete polling request.
            return

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path in {"/favicon.png", "/favicon.ico"}:
            try:
                self.send_content(FAVICON_PATH.read_bytes(), "image/png")
            except OSError:
                self.send_content(b"", "image/png", HTTPStatus.NOT_FOUND)
            return

        if request_path == "/":
            new_visitor = not visitor_was_counted(
                self.headers.get("Cookie", "")
            )
            if new_visitor:
                increment_site_visits()
            log_visit_to_console(self, new_visitor)
            initial_state = json.dumps(
                web_state(), ensure_ascii=False, separators=(",", ":")
            ).replace("<", "\\u003c")
            page = WEB_DASHBOARD.replace(
                "/*__INITIAL_STATE__*/null", initial_state, 1
            )
            response_headers: dict[str, str] = {}
            if new_visitor:
                cookie = (
                    f"{COUNTED_VISITOR_COOKIE}=1; Path=/; Max-Age=31536000; "
                    "HttpOnly; SameSite=Lax"
                )
                if (
                    self.headers.get("X-Forwarded-Proto", "").lower() == "https"
                    or self.headers.get("Host", "").endswith(".ts.net")
                ):
                    cookie += "; Secure"
                response_headers["Set-Cookie"] = cookie
            self.send_content(
                page.encode("utf-8"),
                "text/html; charset=utf-8",
                extra_headers=response_headers,
            )
            return
        if request_path == "/api/state":
            body = json.dumps(web_state(), ensure_ascii=False).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/register-log/download":
            with register_log_lock:
                path = register_log_path
                if path is None and REGISTER_LOG_DIRECTORY.exists():
                    path = max(
                        REGISTER_LOG_DIRECTORY.glob("register_changes_*.csv"),
                        key=lambda candidate: candidate.stat().st_mtime,
                        default=None,
                    )
                if register_log_file is not None:
                    register_log_file.flush()
            if path is None or not path.exists():
                self.send_content(
                    '{"error":"журнал ще не створено"}'.encode("utf-8"),
                    "application/json; charset=utf-8",
                    HTTPStatus.NOT_FOUND,
                )
                return
            try:
                self.send_content(
                    path.read_bytes(),
                    "text/csv; charset=utf-8",
                    extra_headers={
                        "Content-Disposition": f'attachment; filename="{path.name}"'
                    },
                )
            except OSError as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR
                )
            return
        self.send_content(
            '{"error":"не знайдено"}'.encode("utf-8"),
            "application/json",
            HTTPStatus.NOT_FOUND,
        )

    def do_POST(self) -> None:
        if self.path == "/api/register-log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                action = payload.get("action")
                if action == "start":
                    result = start_register_log()
                elif action == "stop":
                    result = stop_register_log()
                elif action == "mark":
                    with state_lock:
                        cycle_id = int(state["cycle_id"])
                    result = record_register_log_note(
                        str(payload.get("note", "")), cycle_id
                    )
                else:
                    raise ValueError("action має бути start, stop або mark")
                status = (
                    HTTPStatus.INTERNAL_SERVER_ERROR
                    if result.get("error")
                    else HTTPStatus.OK
                )
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", status)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path != "/api/settings":
            self.send_content(
                '{"error":"не знайдено"}'.encode("utf-8"),
                "application/json",
                HTTPStatus.NOT_FOUND,
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            with state_lock:
                if "poll_rate_index" in payload:
                    index = int(payload["poll_rate_index"])
                    if not 0 <= index < len(POLL_RATES):
                        raise ValueError("неправильний інтервал опитування")
                    state["poll_rate_index"] = index
                if "read_mode" in payload:
                    mode = str(payload["read_mode"])
                    if mode not in {"fast", "compatible"}:
                        raise ValueError("неправильний режим читання")
                    state["read_mode"] = mode
                if "paused" in payload:
                    paused = payload["paused"]
                    if not isinstance(paused, bool):
                        raise ValueError("paused має бути true або false")
                    state["paused"] = paused
            poll_wake_event.set()
            self.send_content(b'{"ok":true}', "application/json")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            body = json.dumps({"error": str(error)}).encode("utf-8")
            self.send_content(body, "application/json", HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_web_dashboard() -> None:
    host = os.environ.get("INVERTER_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("INVERTER_WEB_PORT", "8080"))
    initialise_statistics()
    worker = threading.Thread(target=poll_worker, name="inverter-poller", daemon=True)
    worker.start()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    safe_console_print(f"Solar Invertor Web: http://localhost:{port}")
    safe_console_print(
        f"Прослуховування {host}:{port} — натисніть Ctrl+C для зупинки"
    )
    if stats_error:
        safe_console_print(f"Лічильник відвідувачів вимкнено: {stats_error}")
    else:
        safe_console_print(
            f"Лічильник: {site_visit_total} відвідувачів · {STATS_DB_PATH}"
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_register_log()
        with state_lock:
            state["stop"] = True
        poll_wake_event.set()
        server.server_close()


if __name__ == "__main__":
    run_web_dashboard()
