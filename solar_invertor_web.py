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

import json
import os
import re
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from datetime import datetime
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DEVICE = "/dev/ttyUSB0"
SLAVE_ID = 1
BAUD_RATE = 9600
COMMAND_TIMEOUT_SECONDS = 3.0
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

# name, scale, unit, signed, group
REGISTER_CONFIG: dict[int, tuple[str, float, str, bool, str]] = {
    17: ("Код протокола/версии", 1.0, "", False, "System"),
    18: ("Код конфигурации устройства", 1.0, "", False, "System"),
    27: ("Слово прошивки/состояния", 1.0, "", False, "System"),
    28: ("Флаг прошивки/состояния", 1.0, "", False, "System"),
    58: ("Битовая маска возможностей/состояния", 1.0, "", False, "System"),
    65: ("Слово прошивки/состояния", 1.0, "", False, "System"),
    66: ("Код конфигурации", 1.0, "", False, "System"),
    67: ("Код конфигурации", 1.0, "", False, "System"),
    68: ("Значение прошивки/состояния", 1.0, "", False, "System"),
    69: ("Знаковое значение состояния", 1.0, "", True, "System"),

    89: ("Напряжение AC", 0.1, "V", False, "AC"),
    90: ("Входной ток AC / значение нагрузки", 1.0, "", False, "AC"),
    91: ("Частота AC", 0.01, "Hz", False, "AC"),
    92: ("Температура инвертора", 0.1, "°C", False, "AC"),
    93: ("Напряжение батареи (данные LCD)", 0.1, "V", False, "Battery"),
    94: ("Процент заряда батареи/нагрузки", 1.0, "%", False, "System"),

    129: ("Напряжение батареи", 0.1, "V", False, "Battery"),
    130: ("Ток зарядки батареи", 0.1, "A", False, "Battery"),
    133: ("Уровень заряда батареи", 1.0, "%", False, "Battery"),
    134: ("Температура литиевой батареи", 0.1, "°C", False, "Battery"),

    137: ("Напряжение литиевой батареи (P3)", 0.1, "V", False, "BMS"),
    138: ("Ток литиевой батареи (P3)", 0.1, "A", True, "BMS"),
    139: ("Уровень заряда литиевой батареи (P4)", 1.0, "%", False, "BMS"),
    140: ("Температура литиевой батареи (P4)", 0.1, "°C", False, "BMS"),
    141: ("Максимальное напряжение зарядки литиевой батареи (P6)", 0.1, "V", False, "BMS"),
    142: ("Недоступное значение", 1.0, "", True, "BMS"),
    143: ("Недоступное значение", 1.0, "", True, "BMS"),
    144: ("Мощность/ток/состояние батареи", 1.0, "", False, "BMS"),

    157: ("Operating status code", 1.0, "", False, "System"),
    158: ("Состояние/внутреннее значение", 1.0, "", False, "System"),

    321: ("Флаг канала/количества BMS", 1.0, "", False, "BMS"),
    324: ("Код конфигурации BMS", 1.0, "", False, "BMS"),
    325: ("Код конфигурации BMS", 1.0, "", False, "BMS"),
    337: ("Код состояния BMS", 1.0, "", False, "BMS"),
    339: ("Уровень заряда литиевой батареи", 1.0, "%", False, "BMS"),
    341: ("Входное напряжение PV", 0.01, "V", False, "PV"),
    342: ("Напряжение литиевой батареи", 0.1, "V", False, "BMS"),
    343: ("Максимальный ток зарядки литиевой батареи", 0.1, "A", True, "BMS"),
    344: ("Ток литиевой батареи", 0.1, "A", True, "BMS"),
    345: ("Предел напряжения литиевой батареи", 0.1, "V", False, "BMS"),
    346: ("Предел напряжения литиевой батареи", 0.1, "V", False, "BMS"),
    349: ("Предел напряжения литиевой батареи", 0.1, "V", False, "BMS"),
    350: ("Предел тока разрядки литиевой батареи", 0.1, "A", True, "BMS"),

    376: ("Настройка напряжения батареи", 0.1, "V", False, "Settings"),
    377: ("Настройка напряжения батареи", 0.1, "V", False, "Settings"),
    378: ("Настройка тока батареи", 0.1, "A", False, "Settings"),
    379: ("Настройка тока батареи", 0.1, "A", False, "Settings"),
    383: ("Настройка напряжения батареи", 0.1, "V", False, "Settings"),
    385: ("Номинальная мощность / предел отдачи в сеть", 1.0, "W", False, "Settings"),
    386: ("Настройка мощности / предел", 1.0, "W", False, "Settings"),

    401: ("Код BMS/состояния", 1.0, "", False, "BMS"),
    402: ("Флаг BMS/состояния", 1.0, "", False, "BMS"),
    403: ("Накопленное значение/мощность", 1.0, "", False, "BMS"),
    404: ("Напряжение литиевой батареи", 0.1, "V", False, "BMS"),
    405: ("Ток литиевой батареи", 0.1, "A", True, "BMS"),
    406: ("Температура литиевой батареи", 0.1, "°C", False, "BMS"),
    407: ("Уровень заряда литиевой батареи", 1.0, "%", False, "BMS"),
    408: ("Оставшаяся/номинальная ёмкость литиевой батареи", 1.0, "%", False, "BMS"),
    409: ("Недоступное значение", 1.0, "", True, "BMS"),
    410: ("Недоступное значение", 1.0, "", True, "BMS"),
    411: ("Максимальное напряжение зарядки литиевой батареи (P6)", 0.1, "V", False, "BMS"),
    412: ("Максимальный ток литиевой батареи", 0.1, "A", False, "BMS"),
    413: ("Мощность батареи/PV", 1.0, "W", False, "BMS"),
    415: ("Предел настройки", 1.0, "", False, "Settings"),
    416: ("Предел настройки", 1.0, "", False, "Settings"),
    417: ("Предел настройки", 1.0, "", False, "Settings"),

    449: ("Напряжение/значение", 0.1, "", False, "System"),
    451: ("Упакованное значение/счётчик", 1.0, "", False, "System"),
    453: ("Упакованное значение/счётчик", 1.0, "", False, "System"),
    455: ("Упакованное знаковое значение", 1.0, "", True, "System"),
}

METER_DEFINITIONS = [
    (89, [], "Напряжение AC", 0.0, 300.0, "V"),
    (91, [], "Частота AC", 45.0, 55.0, "Hz"),
    (92, [], "Температура инвертора", -20.0, 120.0, "°C"),
    (341, [], "Входное напряжение PV", 0.0, 600.0, "V"),
    (137, [404, 342, 129], "Напряжение батареи", 40.0, 65.0, "V"),
    (138, [405, 344], "Ток батареи", -100.0, 100.0, "A"),
    (130, [], "Ток зарядки батареи", 0.0, 150.0, "A"),
    (139, [407, 339, 133], "Уровень заряда батареи", 0.0, 100.0, "%"),
    (140, [406, 134], "Температура батареи", -20.0, 100.0, "°C"),
    (408, [], "Состояние батареи SOH / предел", 0.0, 100.0, "%"),
    (141, [411], "Макс. напряжение зарядки", 40.0, 65.0, "V"),
    (343, [412], "Макс. ток зарядки", 0.0, 150.0, "A"),
    (350, [], "Предел тока разрядки", -200.0, 200.0, "A"),
    (413, [], "Мощность батареи / PV", 0.0, 15000.0, "W"),
    (385, [], "Номинальная мощность", 0.0, 15000.0, "W"),
    (386, [], "Предел мощности", 0.0, 15000.0, "W"),
]


# Fault and alarm meanings from the supplied inverter manual.
FAULT_CODES = {
    1: "Ошибка повышения напряжения шины",
    2: "Перенапряжение шины",
    3: "Пониженное напряжение шины",
    4: "Сверхток батареи",
    5: "Перегрев системы",
    6: "Перенапряжение батареи",
    7: "Ошибка плавного запуска шины",
    8: "Короткое замыкание шины",
    9: "Ошибка плавного запуска инвертора",
    11: "Пониженное напряжение инвертора",
    12: "Короткое замыкание инвертора",
    13: "Отрицательная мощность инвертора",
    14: "Перегрузка",
    17: "Обновление программы",
    18: "Обратная полярность PV",
    26: "Ошибка BMS",
    29: "Ненормальная нагрузка инвертора",
}

ALARM_CODES = {
    50: "Батарея отключена",
    51: "Пониженное напряжение батареи",
    52: "Низкое напряжение батареи",
    53: "Короткое замыкание при зарядке батареи",
    56: "Потеря связи с BMS",
    58: "Ошибка вентилятора",
    59: "Ошибка EEPROM",
    60: "Перегрузка",
    62: "Недостаточная энергия PV",
    68: "Отключение из-за низкого SOC",
    69: "Предупреждение о низком SOC",
    72: "Батарея не может запуститься",
    77: "Нестабильная сеть",
    78: "Потеря связи со счётчиком",
}

OPERATING_STATUS = {
    0: "Ожидание / неизвестно",
    1: "Работа от сети / байпас",
    2: "Работа инвертора от батареи или PV",
    3: "Зарядка / активная работа",
    4: "Ошибка или аварийное состояние",
}

VALUE_PATTERN = re.compile(r"\[(\d+)\]:\s*(-?\d+)")

state_lock = threading.Lock()
poll_wake_event = threading.Event()
state: dict[str, Any] = {
    "online": False,
    "updated_at": "никогда",
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
            register, (f"Register {register}", 1.0, "", False, "Raw")
        )
        return name, "N/A", "", None, group

    if register == 157:
        label = OPERATING_STATUS.get(raw, f"Operating status code {raw}")
        return "Рабочее состояние", label, "", float(raw), "System"

    name, scale, unit, use_signed, group = REGISTER_CONFIG.get(
        register, (f"Register {register}", 1.0, "", False, "Raw")
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
        return {}, "тайм-аут"
    except FileNotFoundError:
        return {}, "mbpoll не найден"
    except Exception as error:
        return {}, str(error)

    output = f"{result.stdout}\n{result.stderr}"
    values = {
        int(match.group(1)): int(match.group(2))
        for match in VALUE_PATTERN.finditer(output)
    }

    if values:
        return values, None

    return {}, output.strip() or "ошибка чтения"


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
            state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state["cycle_seconds"] = duration
            state["cycle_id"] += 1
            state["requests"] = requests
            state["successful"] = len(fresh)
            state["ошибок"] = failed
            state["error"] = "" if fresh else (error or "ошибка чтения")
            state["identifier"] = decode_identifier(cached)
            state["values"] = dict(cached)

            if state["stop"]:
                return

            poll_rate = POLL_RATES[state["poll_rate_index"]]

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

    return None, "N/A"


def draw(stdscr: curses.window, scroll: int) -> int:
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    with state_lock:
        snapshot = dict(state)
        values = dict(state["values"])

    online = snapshot["online"]
    status_attr = curses.color_pair(2) | curses.A_BOLD if online else curses.color_pair(1) | curses.A_BOLD

    safe_addstr(stdscr, 0, 0, "ТЕРМИНАЛЬНАЯ ПАНЕЛЬ ИНВЕРТОРА", curses.A_BOLD)
    safe_addstr(stdscr, 1, 0, "Состояние: ")
    safe_addstr(stdscr, 1, 8, "В СЕТИ" if online else "НЕТ СВЯЗИ", status_attr)
    safe_addstr(
        stdscr,
        1,
        18,
        f"Device: {snapshot['identifier'] or 'неизвестно'}  Updated: {snapshot['updated_at']}",
    )
    safe_addstr(
        stdscr,
        2,
        0,
        f"Cycle: {snapshot['cycle_id']}  Read: {snapshot['cycle_seconds']:.2f}s  "
        f"Target: {POLL_RATES[snapshot['poll_rate_index']]:g}s  "
        f"Mode: {snapshot['read_mode']}  Requests: {snapshot['requests']}  "
        f"Reads: {snapshot['successful']} ok / {snapshot['ошибок']} failed",
    )
    status_code = values.get(157)
    status_text = OPERATING_STATUS.get(status_code, "") if status_code is not None else ""
    safe_addstr(
        stdscr,
        3,
        0,
        "Клавиши: q выход | r интервал | m режим | стрелки/PgUp/PgDn прокрутка"
        + (f" | State: {status_text}" if status_text else ""),
        curses.A_DIM,
    )

    row = 5
    safe_addstr(stdscr, row, 0, "ТЕКУЩИЕ ПОКАЗАТЕЛИ", curses.A_BOLD)
    row += 1

    meter_columns = 2 if width >= 90 else 1
    meter_width = max(38, width // meter_columns - 2)

    for index, (register, fallbacks, label, minimum, maximum, unit) in enumerate(METER_DEFINITIONS):
        value, source = meter_value(values, register, fallbacks)
        col = index % meter_columns
        line_group = index // meter_columns
        y = row + line_group * 3
        x = col * meter_width

        display = "N/A" if value is None else f"{value:.2f}".rstrip("0").rstrip(".")
        safe_addstr(stdscr, y, x, f"{label}: {display} {unit}", curses.A_BOLD)
        safe_addstr(stdscr, y + 1, x, bar(value, minimum, maximum, min(24, meter_width - 8)))
        safe_addstr(stdscr, y + 2, x, f"{minimum:g}..{maximum:g} | {source}", curses.A_DIM)

    row += ((len(METER_DEFINITIONS) + meter_columns - 1) // meter_columns) * 3 + 1
    safe_addstr(stdscr, row, 0, "НЕНУЛЕВЫЕ РЕГИСТРЫ", curses.A_BOLD)
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

    header = f"{'REG':>4}  {'ГРУППА':<9} {'НАЗВАНИЕ':<31} {'ЗНАЧЕНИЕ':>12} {'СЫРОЕ':>7} {'ЗНАК.':>7}"
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
        safe_addstr(stdscr, height - 1, 0, f"Error: {snapshot['error']}", curses.color_pair(1))

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
<html lang="en">
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
    #view-toggle {
      border-color: rgba(56,189,248,.38);
      background: linear-gradient(135deg, rgba(14,165,233,.2), rgba(34,211,238,.1));
      font-weight: 750;
    }
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
    .gauge-card::after {
      content: ""; position: absolute; width: 120px; height: 120px; right: -55px; top: -60px;
      border-radius: 50%; background: var(--accent); opacity: .08; filter: blur(12px);
    }
    .gauge-title { font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
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
  <main class="shell">
    <header>
      <div class="brand">
        <div class="logo">☀</div>
        <div><h1>Solar Invertor Web</h1><div class="subtitle" id="identifier">Waiting for invertor…</div></div>
      </div>
      <div class="header-actions">
        <label class="theme-switch">
          <input id="theme-toggle" type="checkbox" role="switch" aria-label="Use light theme">
          <span class="theme-slider" aria-hidden="true"></span>
          <span id="theme-name">Dark</span>
        </label>
        <button id="app-toggle" type="button">Stop monitoring</button>
        <button id="view-toggle" type="button">View charts</button>
        <div class="status" id="status"><span class="dot"></span><span class="status-label">OFFLINE</span></div>
      </div>
    </header>

    <section id="dashboard-view">
    <div class="toolbar">
      <label class="chip">Request every&nbsp;
        <select id="poll-rate" aria-label="Polling interval">
          <option value="0">0.5 s</option><option value="1">1 s</option>
          <option value="2">2 s</option><option value="3">5 s</option><option value="4">10 s</option>
        </select>
      </label>
      <label class="chip">Read mode&nbsp;
        <select id="read-mode" aria-label="Read mode">
          <option value="fast">Fast</option><option value="compatible">Compatible</option>
        </select>
      </label>
      <button id="demo-button" class="all-data-demo-button" type="button">Run 120s demo · 79 values</button>
      <button id="manage-values-button" type="button">＋ Add values</button>
      <span class="chip" id="cycle">Cycle —</span>
      <span class="chip" id="site-visits">Visitors — · —</span>
      <span class="chip updated" id="updated">Not updated yet</span>
    </div>

    <div class="panel error" id="error"></div>
    <section class="gauges" id="gauges" aria-label="Live inverter readings"></section>
    <section class="panel custom-values" id="custom-values-section" hidden>
      <h2>Added dashboard values</h2>
      <div class="custom-value-grid" id="custom-value-grid"></div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div><h2>Live registers</h2><span class="muted" id="register-count"></span></div>
        <input id="search" type="search" placeholder="Search registers…" aria-label="Search registers">
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Register</th><th>Group</th><th>Name</th><th>Value</th><th>Raw</th></tr></thead>
          <tbody id="registers"></tbody>
        </table>
      </div>
    </section>
    </section>

    <section id="charts-view" hidden>
      <div class="charts-layout">
        <aside class="panel chart-selector">
          <h2>Available values</h2>
          <div class="muted">Each selected reading is added to the dashboard and live charts.</div>
          <input id="chart-search" type="search" placeholder="Search values…" aria-label="Search chart values">
          <div class="value-list" id="chart-value-list"></div>
        </aside>
        <div class="charts-main">
          <div class="panel-head charts-head">
            <div>
              <h2>Live charts</h2>
              <span class="muted" id="chart-selection-count">No values selected</span>
            </div>
            <button id="chart-demo-button" class="all-data-demo-button" type="button">Run 120s demo · 79 values</button>
          </div>
          <div class="chart-grid" id="chart-grid">
            <div class="chart-empty">Select values from the list to start real-time charts.</div>
          </div>
        </div>
      </div>
    </section>
  </main>
  <script>
    const colours = ['#38bdf8','#22d3ee','#34d399','#fbbf24','#a78bfa','#fb7185','#60a5fa'];
    const previous = new Map();
    let lastData = null;
    let chartDemoRunning = false;
    let chartDemoCancelRequested = false;
    let demoRegisterRows = null;
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
    const chartSelections = savedSelections('inverter-chart-values');
    const dashboardSelections = savedSelections('inverter-dashboard-values');
    const combinedSelections = new Set([...chartSelections, ...dashboardSelections]);
    chartSelections.clear();
    dashboardSelections.clear();
    combinedSelections.forEach(key => {
      chartSelections.add(key);
      dashboardSelections.add(key);
    });
    const chartHistory = new Map();
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
          label: meter.label,
          detail: `${meter.unit || 'value'} · gauge R${meter.register}`,
          unit: meter.unit,
          value: Number.isFinite(meter.value) ? meter.value : 0,
          minimum: meter.minimum,
          maximum: meter.maximum
        });
      });
      data.registers.forEach(register => {
        const value = numericValue(register.display);
        if (value === null) return;
        definitions.set(`register-${register.register}`, {
          key: `register-${register.register}`,
          label: register.name,
          detail: `R${register.register} · ${register.group}`,
          unit: register.unit,
          value,
          minimum: null,
          maximum: null
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
          <label><input type="checkbox" data-value-key="${item.key}" ${chartSelections.has(item.key) && dashboardSelections.has(item.key) ? 'checked' : ''}> Dashboard + chart</label>
        </div>
      </div>`).join('');
    }

    function updateChartDefinitions(data) {
      const next = collectChartDefinitions(data);
      const oldSignature = [...chartDefinitions.keys()].join('|');
      const nextSignature = [...next.keys()].join('|');
      chartDefinitions = next;
      if (oldSignature !== nextSignature) {
        renderChartValueList();
        renderChartCards();
      }
      if (!chartDemoRunning) renderDashboardValues();
    }

    function renderDashboardValues() {
      const section = document.querySelector('#custom-values-section');
      const grid = document.querySelector('#custom-value-grid');
      const selected = [...dashboardSelections].filter(key => chartDefinitions.has(key));
      section.hidden = selected.length === 0;
      if (!selected.length) {
        grid.innerHTML = '';
        grid.dataset.keys = '';
        return;
      }

      const signature = selected.join('|');
      if (grid.dataset.keys !== signature) {
        grid.dataset.keys = signature;
        grid.innerHTML = selected.map(key => {
          const item = chartDefinitions.get(key);
          return `<article class="custom-value-card" data-dashboard-key="${key}">
            <button class="remove-value" type="button" data-remove-dashboard="${key}" title="Remove from dashboard">×</button>
            <div class="custom-value-label" title="${item.label}">${item.label}</div>
            <div class="custom-value-reading"><span class="custom-value-number">0</span> <span class="unit">${item.unit}</span></div>
            <div class="custom-value-detail">${item.detail}</div>
          </article>`;
        }).join('');
      }

      selected.forEach(key => {
        const item = chartDefinitions.get(key);
        const card = grid.querySelector(`[data-dashboard-key="${key}"]`);
        if (!card || !item) return;
        const text = Number(item.value.toFixed(2)).toString();
        const number = card.querySelector('.custom-value-number');
        if (number.textContent !== text) number.textContent = text;
      });
    }

    function renderChartCards() {
      const grid = document.querySelector('#chart-grid');
      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      document.querySelector('#chart-demo-button').disabled = false;
      document.querySelector('#chart-selection-count').textContent =
        selected.length ? `${selected.length} value${selected.length === 1 ? '' : 's'} selected · last 2 minutes` : 'No values selected';

      if (!selected.length) {
        grid.innerHTML = '<div class="chart-empty">Select values from the list to start real-time charts.</div>';
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
          <canvas id="chart-${key}" data-chart-key="${key}" aria-label="Live chart for ${item.label}"></canvas>
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

    function randomChartValue(item) {
      const hasRange = Number.isFinite(item.minimum) && Number.isFinite(item.maximum);
      if (hasRange) {
        return item.minimum + Math.random() * (item.maximum - item.minimum);
      }
      const spread = Math.max(Math.abs(item.value) * .4, 10);
      return item.value + (Math.random() * 2 - 1) * spread;
    }

    function trimChartHistory(history, currentTime) {
      const oldestAllowed = currentTime - chartWindowMilliseconds;
      while (history.length && history[0].time < oldestAllowed) history.shift();
    }

    function formatChartTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString([], {
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
      drawAllCharts();

      try {
        const demoStartedAt = Date.now();
        while (Date.now() - demoStartedAt < chartWindowMilliseconds) {
          const elapsedBeforeWait = Math.floor((Date.now() - demoStartedAt) / 1000);
          setButtonState(`■ Stop · ${elapsedBeforeWait} / ${chartWindowSeconds}s · ${registerKeys.length} values`);
          const selectedIndex = Number(document.querySelector('#poll-rate').value);
          await wait(requestIntervals[selectedIndex] ?? 2000);
          if (chartDemoCancelRequested) break;

          const now = Date.now();
          registerKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const history = chartHistory.get(key) || [];
            item.value = randomChartValue(item);
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          meterKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const registerKey = key.replace('meter-', 'register-');
            const registerItem = chartDefinitions.get(registerKey);
            item.value = randomChartValue(item);
            if (registerItem) {
              registerItem.value = item.value;
              const registerHistory = chartHistory.get(registerKey) || [];
              if (registerHistory.length) registerHistory.at(-1).value = item.value;
            }
            const history = chartHistory.get(key) || [];
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          demoRegisterRows = lastData ? lastData.registers.map(register => {
            const item = chartDefinitions.get(`register-${register.register}`);
            if (!item) return register;
            return {
              ...register,
              display: Number(item.value.toFixed(2)).toString(),
              raw: Math.round(item.value),
              available: true
            };
          }) : [];
          const demoMeters = lastData ? lastData.meters.map(meter => {
            const item = chartDefinitions.get(`meter-${meter.register}`);
            return item ? {...meter, value: item.value, source: 'All-data random demo'} : meter;
          }) : [];
          const elapsed = Math.min(
            chartWindowSeconds,
            Math.floor((now - demoStartedAt) / 1000)
          );
          setButtonState(`■ Stop · ${elapsed} / ${chartWindowSeconds}s · ${registerKeys.length} values`);
          renderGauges(demoMeters);
          renderDashboardValues();
          renderRegisters(demoRegisterRows);
          drawAllCharts();
        }
      } finally {
        chartDemoRunning = false;
        chartDemoCancelRequested = false;
        demoRegisterRows = null;
        setButtonState('Run 120s demo · 79 values');
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
        : 'Waiting…';
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

    function gaugeMarkup(meter, index) {
      return `<article class="gauge-card" id="g-${meter.register}" style="--accent:${colours[index % colours.length]}">
        <div class="gauge-title">${meter.label}</div>
        <svg viewBox="0 0 240 145" role="img" aria-label="${meter.label}">
          <path class="track" d="M20 120 A100 100 0 0 1 220 120"/>
          <path class="progress" d="M20 120 A100 100 0 0 1 220 120"/>
          ${scaleMarkup(meter)}
          <line class="needle" x1="120" y1="120" x2="120" y2="33"/>
          <circle class="hub" cx="120" cy="120" r="7"/>
        </svg>
        <div class="reading"><span class="trend flat">•</span><span class="value">—</span><span class="unit">${meter.unit}</span></div>
        <div class="source">No data</div>
      </article>`;
    }

    function renderGauges(meters) {
      const host = document.querySelector('#gauges');
      if (!host.children.length) host.innerHTML = meters.map(gaugeMarkup).join('');
      meters.forEach(meter => {
        const card = document.querySelector(`#g-${meter.register}`);
        const hasValue = Number.isFinite(meter.value);
        const value = hasValue ? meter.value : null;
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
        if (sourceElement.textContent !== meter.source) sourceElement.textContent = meter.source;

        const old = previous.get(meter.register);
        const trend = card.querySelector('.trend');
        if (old === undefined) {
          trend.className = 'trend flat';
          trend.textContent = '•';
        } else if (hasValue && value !== old) {
          const up = value > old;
          trend.className = `trend ${up ? 'up' : 'down'}`;
          trend.textContent = up ? '↑' : '↓';
        }
        if (hasValue) previous.set(meter.register, value);
      });
    }

    function renderRegisters(registers) {
      const query = document.querySelector('#search').value.trim().toLowerCase();
      const shown = registers.filter(item =>
        `${item.register} ${item.group} ${item.name} ${item.display} ${item.unit}`.toLowerCase().includes(query)
      );
      const available = registers.filter(item => item.available).length;
      document.querySelector('#register-count').textContent =
        `${available} received · ${registers.length - available} awaiting data · ${shown.length} shown`;
      document.querySelector('#registers').innerHTML = shown.map(item => `<tr class="${item.available ? '' : 'unavailable'}">
        <td>R${item.register}</td><td>${item.group}</td><td>${item.name}</td>
        <td>${item.display} ${item.unit}</td><td>${item.raw ?? '—'}</td></tr>`).join('');
    }

    function render(data) {
      lastData = data;
      document.querySelector('#identifier').textContent = data.identifier || 'Unknown device';
      const status = document.querySelector('#status');
      status.classList.toggle('online', data.online && !data.paused);
      status.classList.toggle('paused', data.paused);
      status.querySelector('.status-label').textContent =
        data.paused ? 'PAUSED' : data.online ? 'ONLINE' : 'OFFLINE';
      const appToggle = document.querySelector('#app-toggle');
      appToggle.textContent = data.paused ? 'Start monitoring' : 'Stop monitoring';
      appToggle.classList.toggle('start', data.paused);
      document.querySelector('#updated').textContent = `Updated ${data.updated_at}`;
      document.querySelector('#cycle').textContent =
        data.paused
          ? `Cycle ${data.cycle_id} · monitoring paused`
          : `Cycle ${data.cycle_id} · ${data.cycle_seconds.toFixed(2)} s · ${data.successful} reads`;
      const totalVisitors = Number(data.site_visits || 0);
      document.querySelector('#site-visits').textContent =
        `Visitors ${totalVisitors.toLocaleString()} · ${data.site_visits_date}`;
      if (lastLoggedSiteVisits !== totalVisitors) {
        console.log('[Solar Invertor Web visit]', {
          totalVisitors,
          date: data.site_visits_date,
          openedAt: new Date().toISOString(),
          referrer: document.referrer || 'direct',
          language: navigator.language,
          userAgent: navigator.userAgent,
          viewport: `${window.innerWidth}x${window.innerHeight}`
        });
        lastLoggedSiteVisits = totalVisitors;
      }
      document.querySelector('#poll-rate').value = data.poll_rate_index;
      document.querySelector('#read-mode').value = data.read_mode;
      const error = document.querySelector('#error');
      error.textContent = data.error ? `Connection error: ${data.error}` : '';
      error.classList.toggle('show', Boolean(data.error));
      renderGauges(data.meters);
      renderRegisters(data.registers);
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
        const box = document.querySelector('#error');
        box.textContent = `Dashboard connection lost: ${error.message}`;
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

    function toggleView() {
      const dashboard = document.querySelector('#dashboard-view');
      const charts = document.querySelector('#charts-view');
      const showCharts = charts.hidden;
      dashboard.hidden = showCharts;
      charts.hidden = !showCharts;
      document.querySelector('#view-toggle').textContent = showCharts ? '← Dashboard' : 'View charts';
      if (showCharts) requestAnimationFrame(drawAllCharts);
    }

    function applyTheme(theme, save = true) {
      const selectedTheme = theme === 'light' ? 'light' : 'dark';
      document.documentElement.dataset.theme = selectedTheme;
      document.querySelector('#theme-toggle').checked = selectedTheme === 'light';
      document.querySelector('#theme-name').textContent =
        selectedTheme === 'light' ? 'Light' : 'Dark';
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

    document.querySelector('#poll-rate').addEventListener('change', event =>
      updateSetting('poll_rate_index', Number(event.target.value)));
    document.querySelector('#read-mode').addEventListener('change', event =>
      updateSetting('read_mode', event.target.value));
    document.querySelector('#demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#chart-demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#manage-values-button').addEventListener('click', () => {
      if (document.querySelector('#charts-view').hidden) toggleView();
      document.querySelector('#chart-search').focus();
    });
    document.querySelector('#search').addEventListener('input', () =>
      demoRegisterRows
        ? renderRegisters(demoRegisterRows)
        : lastData && renderRegisters(lastData.registers));
    document.querySelector('#view-toggle').addEventListener('click', toggleView);
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
      saveSelections('inverter-dashboard-values', dashboardSelections);
      saveSelections('inverter-chart-values', chartSelections);
      renderDashboardValues();
      renderChartCards();
    });
    document.querySelector('#custom-value-grid').addEventListener('click', event => {
      const button = event.target.closest('button[data-remove-dashboard]');
      if (!button) return;
      const key = button.dataset.removeDashboard;
      dashboardSelections.delete(key);
      chartSelections.delete(key);
      chartHistory.delete(key);
      saveSelections('inverter-dashboard-values', dashboardSelections);
      saveSelections('inverter-chart-values', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
    });
    window.addEventListener('resize', () => {
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    });
    const initialData = /*__INITIAL_STATE__*/null;
    if (initialData) render(initialData);
    refresh();
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
            source = "No mbpoll data"
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
        if raw is None:
            name, _, unit, _, group = REGISTER_CONFIG.get(
                register, (f"Register {register}", 1.0, "", False, "Raw")
            )
            display = "0"
        else:
            name, display, unit, _, group = normalize(register, raw)
        registers.append({
            "register": register,
            "group": group,
            "name": name,
            "display": display,
            "unit": unit,
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
        "site_visits_date": datetime.now().astimezone().strftime("%d %b %Y"),
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
        "event": "dashboard_visit",
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total_visitors": site_visit_total,
        "new_visitor": new_visitor,
        "source": source[:100],
        "identity": (
            handler.headers.get("Tailscale-User-Login")
            or handler.headers.get("Tailscale-User-Name")
            or "public/anonymous"
        )[:160],
        "referrer": handler.headers.get("Referer", "direct")[:500],
        "user_agent": handler.headers.get("User-Agent", "unknown")[:500],
    }
    print(
        "VISITOR " + json.dumps(details, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )


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
        self.send_content(b'{"error":"not found"}', "application/json", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/settings":
            self.send_content(b'{"error":"not found"}', "application/json", HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            with state_lock:
                if "poll_rate_index" in payload:
                    index = int(payload["poll_rate_index"])
                    if not 0 <= index < len(POLL_RATES):
                        raise ValueError("invalid polling interval")
                    state["poll_rate_index"] = index
                if "read_mode" in payload:
                    mode = str(payload["read_mode"])
                    if mode not in {"fast", "compatible"}:
                        raise ValueError("invalid read mode")
                    state["read_mode"] = mode
                if "paused" in payload:
                    paused = payload["paused"]
                    if not isinstance(paused, bool):
                        raise ValueError("paused must be true or false")
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
    print(f"Solar Invertor Web: http://localhost:{port}")
    print(f"Listening on {host}:{port} — press Ctrl+C to stop")
    if stats_error:
        print(f"Visit counter disabled: {stats_error}")
    else:
        print(f"Visit counter: {site_visit_total} visits · {STATS_DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with state_lock:
            state["stop"] = True
        poll_wake_event.set()
        server.server_close()


if __name__ == "__main__":
    run_web_dashboard()
