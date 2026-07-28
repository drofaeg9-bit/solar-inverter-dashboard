from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from datetime import datetime, timedelta
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
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAVICON_PATH = PROJECT_ROOT / "favicon.png"
_stats_path_setting = os.environ.get("INVERTER_STATS_DB")
_new_stats_path = PROJECT_ROOT / "solar_invertor_web_stats.sqlite3"
_legacy_stats_path = PROJECT_ROOT / "inverter_stats.sqlite3"
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
solar_energy_error = ""
solar_energy_last_sample_at: datetime | None = None
solar_energy_last_power_w: float | None = None
solar_energy_last_flush_monotonic = 0.0
solar_energy_pending_wh: dict[str, float] = {}
COUNTED_VISITOR_COOKIE = "inverter_counted"
REGISTER_LOG_DIRECTORY = PROJECT_ROOT / "register_logs"


def non_negative_int_environment(name: str, default: int) -> int:
    """Read a non-negative integer setting, falling back on invalid input."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value >= 0 else default


REGISTER_LOG_MIN_FREE_BYTES = non_negative_int_environment(
    "INVERTER_LOG_MIN_FREE_BYTES", 2 * 1024**3
)
REGISTER_LOG_CLEANUP_TARGET_BYTES = max(
    REGISTER_LOG_MIN_FREE_BYTES,
    non_negative_int_environment(
        "INVERTER_LOG_CLEANUP_TARGET_BYTES",
        REGISTER_LOG_MIN_FREE_BYTES + 512 * 1024**2,
    ),
)

register_log_lock = threading.RLock()
register_log_storage_stop_event = threading.Event()
register_log_file: TextIO | None = None
register_log_writer: Any = None
register_log_path: Path | None = None
register_log_started_at = ""
register_log_changes = 0
register_log_error = ""
register_log_previous_values: dict[int, int] = {}
register_log_free_bytes: int | None = None
register_log_pruned_files = 0
register_log_storage_checked_at = 0.0
register_log_previous_poll_settings: tuple[int, str, bool] | None = None
register_log_language = "uk"
register_log_text_translations: dict[str, str] = {}

REGISTER_LOG_CSV_LABELS = {
    "uk": {
        "headers": [
            "час_мадрид", "цикл", "подія", "регістр", "група", "назва",
            "попереднє_raw", "raw", "змінені_біти", "значення", "одиниця",
            "кнопка_lcd", "сторінка_lcd", "сценарій_демо", "нотатка",
        ],
        "events": {"INITIAL": "ПОЧАТКОВИЙ", "CHANGE": "ЗМІНА", "NOTE": "НОТАТКА", "LCD_KEY": "КНОПКА_LCD"},
        "register": "Регістр",
    },
    "ru": {
        "headers": [
            "время_мадрид", "цикл", "событие", "регистр", "группа", "название",
            "предыдущее_raw", "raw", "изменённые_биты", "значение", "единица",
            "кнопка_lcd", "страница_lcd", "сценарий_демо", "заметка",
        ],
        "events": {"INITIAL": "ИСХОДНОЕ", "CHANGE": "ИЗМЕНЕНИЕ", "NOTE": "ЗАМЕТКА", "LCD_KEY": "КНОПКА_LCD"},
        "register": "Регистр",
    },
    "en": {
        "headers": [
            "timestamp_madrid", "cycle", "event", "register", "group", "name",
            "previous_raw", "raw", "changed_bits", "display", "unit",
            "lcd_key", "lcd_page", "demo_scenario", "note",
        ],
        "events": {"INITIAL": "INITIAL", "CHANGE": "CHANGE", "NOTE": "NOTE", "LCD_KEY": "LCD_KEY"},
        "register": "Register",
    },
}

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
    16643, 16644, 16645,
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
    (16643, 3),
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

    # mbpoll uses one-based references for zero-based Modbus addresses
    # 0x4102-0x4104 (LCD programs 03-05).
    16643: ("Пріоритет вихідного джерела", 1.0, "", False, "Налаштування"),
    16644: ("Режим входу AC", 1.0, "", False, "Налаштування"),
    16645: ("Пріоритет джерела заряджання", 1.0, "", False, "Налаштування"),
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


def maintain_register_log_storage(force: bool = False) -> bool:
    """Delete oldest completed logs when disk space falls below the reserve."""
    global register_log_free_bytes, register_log_pruned_files
    global register_log_storage_checked_at, register_log_error

    with register_log_lock:
        monotonic_now = time.monotonic()
        if not force and monotonic_now - register_log_storage_checked_at < 60:
            return (
                register_log_free_bytes is None
                or register_log_free_bytes >= REGISTER_LOG_MIN_FREE_BYTES
            )

        register_log_storage_checked_at = monotonic_now
        try:
            REGISTER_LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
            root = REGISTER_LOG_DIRECTORY.resolve()
            register_log_free_bytes = shutil.disk_usage(root).free
            if register_log_free_bytes >= REGISTER_LOG_MIN_FREE_BYTES:
                return True

            active_path = (
                register_log_path.resolve()
                if register_log_file is not None and register_log_path is not None
                else None
            )
            candidates: list[tuple[float, Path]] = []
            for candidate in REGISTER_LOG_DIRECTORY.glob("register_changes_*.csv"):
                try:
                    resolved = candidate.resolve(strict=True)
                    modified_at = resolved.stat().st_mtime
                except OSError:
                    continue
                if (
                    resolved.parent != root
                    or resolved == active_path
                    or not resolved.name.startswith("register_changes_")
                    or resolved.suffix.lower() != ".csv"
                ):
                    continue
                candidates.append((modified_at, resolved))

            candidates.sort(key=lambda item: item[0])
            for _, candidate in candidates:
                if register_log_free_bytes >= REGISTER_LOG_CLEANUP_TARGET_BYTES:
                    break
                candidate.unlink()
                register_log_pruned_files += 1
                register_log_free_bytes = shutil.disk_usage(root).free

            if register_log_free_bytes < REGISTER_LOG_MIN_FREE_BYTES:
                minimum_gib = REGISTER_LOG_MIN_FREE_BYTES / 1024**3
                register_log_error = (
                    "Register logging stopped: less than "
                    f"{minimum_gib:g} GiB free and no completed register logs "
                    "remain to remove"
                )
                return False
            register_log_error = ""
            return True
        except OSError as error:
            register_log_error = f"Register-log storage cleanup failed: {error}"
            return False


def register_log_storage_worker() -> None:
    """Check log storage every minute, even when recording is inactive."""
    while not register_log_storage_stop_event.wait(60):
        maintain_register_log_storage(force=True)


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
            "free_bytes": register_log_free_bytes,
            "minimum_free_bytes": REGISTER_LOG_MIN_FREE_BYTES,
            "pruned_files": register_log_pruned_files,
            "physical_button_capture": register_log_file is not None,
            "capture_interval_seconds": POLL_RATES[0],
            "language": register_log_language,
        }


def describe_changed_bits(previous_raw: int | None, raw: int) -> str:
    """Describe changed bits in a 16-bit register value for signal discovery."""
    if previous_raw is None:
        return ""
    previous_word = int(previous_raw) & 0xFFFF
    current_word = int(raw) & 0xFFFF
    changed_mask = previous_word ^ current_word
    return "|".join(
        f"b{bit}:{(previous_word >> bit) & 1}->{(current_word >> bit) & 1}"
        for bit in range(16)
        if changed_mask & (1 << bit)
    )


def configure_register_log_language(
    language: str, translations: Any = None
) -> None:
    """Select and validate browser-provided translations for one CSV session."""
    global register_log_language, register_log_text_translations
    if language not in REGISTER_LOG_CSV_LABELS:
        raise ValueError("language must be uk, ru, or en")
    clean_translations: dict[str, str] = {}
    if isinstance(translations, dict):
        for source, translated in list(translations.items())[:500]:
            if not isinstance(source, str) or not isinstance(translated, str):
                continue
            clean_source = " ".join(source.split())[:250]
            clean_translated = " ".join(translated.split())[:250]
            if clean_source and clean_translated:
                clean_translations[clean_source] = clean_translated
    register_log_language = language
    register_log_text_translations = clean_translations


def localize_register_log_text(text: str) -> str:
    """Translate register metadata using the language selected when logging began."""
    translated = register_log_text_translations.get(text)
    if translated is None and text.startswith("Регістр "):
        translated = f"{REGISTER_LOG_CSV_LABELS[register_log_language]['register']} {text[8:]}"
    return safe_register_log_cell(translated if translated is not None else text)


def safe_register_log_cell(value: str) -> str:
    """Prevent user or translated text from becoming a spreadsheet formula."""
    # Prevent spreadsheet applications from treating labels as formulas.
    numeric = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value) is not None
    return f"'{value}" if not numeric and value.startswith(("=", "+", "-", "@")) else value


def register_log_event(event: str) -> str:
    """Return a localized CSV event name."""
    events = REGISTER_LOG_CSV_LABELS[register_log_language]["events"]
    return str(events.get(event, event))


def start_register_log(
    language: str = "uk", translations: Any = None
) -> dict[str, Any]:
    """Start a new CSV file containing initial and changed register values."""
    global register_log_file, register_log_writer, register_log_path
    global register_log_started_at, register_log_changes, register_log_error
    global register_log_previous_values
    global register_log_previous_poll_settings

    with register_log_lock:
        if register_log_file is not None:
            return register_log_status_unlocked()
        log_file: TextIO | None = None
        try:
            configure_register_log_language(language, translations)
            REGISTER_LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
            if not maintain_register_log_storage(force=True):
                return register_log_status_unlocked()
            now = datetime.now(MADRID_TIME_ZONE)
            path = REGISTER_LOG_DIRECTORY / (
                f"register_changes_{register_log_language}_"
                f"{now.strftime('%Y%m%d_%H%M%S_%f')}.csv"
            )
            log_file = path.open("x", encoding="utf-8-sig", newline="", buffering=1)
            writer = csv.writer(log_file)
            writer.writerow(REGISTER_LOG_CSV_LABELS[register_log_language]["headers"])
            register_log_file = log_file
            register_log_writer = writer
            register_log_path = path
            register_log_started_at = now.isoformat(timespec="seconds")
            register_log_changes = 0
            register_log_error = ""
            with state_lock:
                register_log_previous_poll_settings = (
                    int(state["poll_rate_index"]),
                    str(state["read_mode"]),
                    bool(state["paused"]),
                )
                baseline_values = dict(state["values"])
                baseline_cycle_id = int(state["cycle_id"])
                state["poll_rate_index"] = 0
                state["read_mode"] = "fast"
                state["paused"] = False

            baseline_timestamp = now.isoformat(timespec="milliseconds")
            for register, raw in sorted(baseline_values.items()):
                name, display, unit, _, group = normalize(register, raw)
                writer.writerow([
                    baseline_timestamp,
                    baseline_cycle_id,
                    register_log_event("INITIAL"),
                    register,
                    localize_register_log_text(group),
                    localize_register_log_text(name),
                    "",
                    raw,
                    "",
                    localize_register_log_text(display),
                    unit,
                    "",
                    "",
                    "",
                    "",
                ])
                register_log_changes += 1
            log_file.flush()
            register_log_previous_values = baseline_values
            poll_wake_event.set()
        except OSError as error:
            register_log_error = str(error)
            if log_file is not None:
                try:
                    log_file.close()
                except OSError:
                    pass
            register_log_file = None
            register_log_writer = None
            restore_register_log_poll_settings()
        return register_log_status_unlocked()


def restore_register_log_poll_settings() -> None:
    """Restore polling settings that were active before capture started."""
    global register_log_previous_poll_settings
    if register_log_previous_poll_settings is None:
        return
    poll_rate_index, read_mode, paused = register_log_previous_poll_settings
    with state_lock:
        state["poll_rate_index"] = poll_rate_index
        state["read_mode"] = read_mode
        state["paused"] = paused
    register_log_previous_poll_settings = None
    poll_wake_event.set()


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
            restore_register_log_poll_settings()
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
        "free_bytes": register_log_free_bytes,
        "minimum_free_bytes": REGISTER_LOG_MIN_FREE_BYTES,
        "pruned_files": register_log_pruned_files,
        "physical_button_capture": register_log_file is not None,
        "capture_interval_seconds": POLL_RATES[0],
        "language": register_log_language,
    }


def record_register_changes(values: dict[int, int], cycle_id: int) -> None:
    """Append the initial snapshot or values changed since the prior poll."""
    global register_log_file, register_log_writer
    global register_log_changes, register_log_error, register_log_previous_values
    with register_log_lock:
        if register_log_file is None or register_log_writer is None:
            return
        if not maintain_register_log_storage():
            try:
                register_log_file.flush()
                register_log_file.close()
            except OSError:
                pass
            register_log_file = None
            register_log_writer = None
            restore_register_log_poll_settings()
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
                    register_log_event("INITIAL" if initial_snapshot else "CHANGE"),
                    register,
                    localize_register_log_text(group),
                    localize_register_log_text(name),
                    "" if previous_raw is None else previous_raw,
                    raw,
                    describe_changed_bits(previous_raw, raw),
                    localize_register_log_text(display),
                    unit,
                    "",
                    "",
                    "",
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
                register_log_event("NOTE"),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                safe_register_log_cell(clean_note),
            ])
            register_log_file.flush()
            register_log_changes += 1
            register_log_error = ""
        except OSError as error:
            register_log_error = str(error)
        return register_log_status_unlocked()


def record_demo_lcd_key(
    key: str, page: str, demo_case: str, cycle_id: int
) -> dict[str, Any]:
    """Record a virtual LCD key press made while the browser demo is running."""
    global register_log_changes, register_log_error
    clean_key = key.strip().lower()
    if clean_key not in {"escape", "up", "down", "enter"}:
        raise ValueError("invalid LCD key")
    clean_page = page.strip().upper()
    if clean_page != "LCD" and re.fullmatch(r"P[1-9]", clean_page) is None:
        raise ValueError("invalid LCD page")
    clean_demo_case = demo_case.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", clean_demo_case) is None:
        raise ValueError("invalid demo scenario")

    with register_log_lock:
        if register_log_file is None or register_log_writer is None:
            raise ValueError("спочатку запустіть запис журналу")
        try:
            register_log_writer.writerow([
                datetime.now(MADRID_TIME_ZONE).isoformat(timespec="milliseconds"),
                cycle_id,
                register_log_event("LCD_KEY"),
                "", "", "", "", "", "", "", "",
                "ESC" if clean_key == "escape" else clean_key.upper(),
                clean_page,
                clean_demo_case,
                "",
            ])
            register_log_file.flush()
            register_log_changes += 1
            register_log_error = ""
        except OSError as error:
            register_log_error = str(error)
        return register_log_status_unlocked()


def flush_solar_energy_locked() -> bool:
    """Persist pending PV watt-hours while ``stats_lock`` is held."""
    global solar_energy_error
    pending = {
        day: watt_hours
        for day, watt_hours in solar_energy_pending_wh.items()
        if watt_hours > 0
    }
    if not pending:
        return True
    try:
        with closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            connection.executemany(
                """
                INSERT INTO solar_energy_daily (day, watt_hours, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                    watt_hours = watt_hours + excluded.watt_hours,
                    updated_at = excluded.updated_at
                """,
                [
                    (day, watt_hours, datetime.now(MADRID_TIME_ZONE).isoformat(timespec="seconds"))
                    for day, watt_hours in pending.items()
                ],
            )
            connection.commit()
        for day, watt_hours in pending.items():
            remaining = solar_energy_pending_wh.get(day, 0.0) - watt_hours
            if remaining > 1e-9:
                solar_energy_pending_wh[day] = remaining
            else:
                solar_energy_pending_wh.pop(day, None)
        solar_energy_error = ""
        return True
    except (OSError, sqlite3.Error) as error:
        solar_energy_error = str(error)
        return False


def flush_solar_energy() -> None:
    """Persist accumulated solar energy before a clean shutdown."""
    with stats_lock:
        flush_solar_energy_locked()


def record_solar_energy(fresh_values: dict[int, int]) -> None:
    """Integrate confirmed R385 PV power samples into Madrid-day buckets."""
    global solar_energy_last_sample_at, solar_energy_last_power_w
    global solar_energy_last_flush_monotonic
    raw = fresh_values.get(385)
    if raw is None:
        return
    _, _, _, normalized_power, _ = normalize(385, raw)
    if normalized_power is None:
        return

    now = datetime.now(MADRID_TIME_ZONE)
    power_w = max(0.0, min(20000.0, float(normalized_power)))
    with stats_lock:
        previous_at = solar_energy_last_sample_at
        previous_power_w = solar_energy_last_power_w
        solar_energy_last_sample_at = now
        solar_energy_last_power_w = power_w
        if previous_at is None or previous_power_w is None:
            return

        elapsed_seconds = (now - previous_at).total_seconds()
        # Ignore long gaps so a stopped process or failed Modbus link cannot
        # turn one stale reading into fictitious production.
        if not 0 < elapsed_seconds <= 60:
            return
        average_power_w = (previous_power_w + power_w) / 2
        watt_hours = average_power_w * elapsed_seconds / 3600
        day_key = now.date().isoformat()
        solar_energy_pending_wh[day_key] = (
            solar_energy_pending_wh.get(day_key, 0.0) + watt_hours
        )

        monotonic_now = time.monotonic()
        if monotonic_now - solar_energy_last_flush_monotonic >= 10:
            if flush_solar_energy_locked():
                solar_energy_last_flush_monotonic = monotonic_now


def solar_energy_summary() -> dict[str, Any]:
    """Return current and all-time SQLite-backed production in kWh."""
    global solar_energy_error
    now = datetime.now(MADRID_TIME_ZONE)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    daily: dict[str, float] = {}

    try:
        with stats_lock:
            with closing(sqlite3.connect(STATS_DB_PATH)) as connection:
                rows = connection.execute(
                    """
                    SELECT day, watt_hours
                    FROM solar_energy_daily
                    """,
                ).fetchall()
            daily = {str(day): float(watt_hours) for day, watt_hours in rows}
            for day, watt_hours in solar_energy_pending_wh.items():
                daily[day] = daily.get(day, 0.0) + watt_hours
        solar_energy_error = ""
    except (OSError, sqlite3.Error) as error:
        solar_energy_error = str(error)

    def total_since(start: Any) -> float:
        return sum(
            watt_hours
            for day, watt_hours in daily.items()
            if start.isoformat() <= day <= today.isoformat()
        ) / 1000

    return {
        "today_kwh": round(total_since(today), 3),
        "week_kwh": round(total_since(week_start), 3),
        "month_kwh": round(total_since(month_start), 3),
        "year_kwh": round(total_since(year_start), 3),
        "total_kwh": round(sum(daily.values()) / 1000, 3),
        "source_register": 385,
        "storage": "sqlite",
        "estimated": True,
        "error": solar_energy_error,
    }


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
        if fresh:
            record_solar_energy(fresh)
        poll_wake_event.wait(max(0.0, poll_rate - duration))
        poll_wake_event.clear()


def meter_value(
    values: dict[int, int], register: int, fallbacks: list[int]
) -> tuple[float | None, str]:
    """Return the first available normalized value for a dashboard meter."""
    for candidate in [register, *fallbacks]:
        if candidate not in values:
            continue

        _, display, _, value, _ = normalize(candidate, values[candidate])
        if value is not None:
            return value, f"R{candidate} {display}"

    return None, "Н/Д"


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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS solar_energy_daily (
                    day TEXT PRIMARY KEY,
                    watt_hours REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
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
