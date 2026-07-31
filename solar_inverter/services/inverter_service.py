from __future__ import annotations

import csv
import io
import json
import math
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
_register_map_path_setting = os.environ.get("INVERTER_REGISTER_MAP")
REGISTER_MAP_PATH = (
    Path(_register_map_path_setting)
    if _register_map_path_setting
    else STATS_DB_PATH.with_name("register_map_overrides.csv")
)
REGISTER_MAP_MAX_BYTES = 1024 * 1024
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
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
    17, 18, 27, 28, 58,
    65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80,
    81, 82, 83, 84,
    85, 86, 87, 88,
    89, 90, 91, 92, 93, 94,
    95,
    129, 130, 131, 132, 133, 134, 135, 136,
    137, 138, 139, 140, 141, 142, 143, 144, 145, 146,
    147, 148, 149, 150, 151, 152, 153, 154, 155, 156,
    157, 158, 159, 160, 161, 162, 163, 164, 165, 166,
    167, 168, 169, 170, 171, 172, 173, 174, 175, 176,
    177, 178, 179, 180, 181, 182, 183, 184, 185, 186,
    187, 188, 189, 190,
    321, 322, 323, 324, 325, 337, 339,
    341, 342, 343, 344, 345, 346, 349, 350,
    375, 376, 377, 378, 379, 383, 384, 385, 386,
    401, 402, 403, 404, 405, 406, 407, 408,
    409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419,
    433, 434, 435, 436, 437,
    448, 449, 450, 451, 452, 453, 454, 455,
    529, 530, 537, 538, 539, 541, 542, 545,
    801, 802, 817, 818, 819, 820, 821, 822, 823,
    16641, 16642, 16643, 16644, 16645, 16646, 16647, 16648,
    16649, 16650, 16651, 16652, 16653, 16654, 16655, 16656,
]

FAST_BLOCKS = [
    (1, 10),
    (17, 2),
    (27, 2),
    (58, 1),
    (65, 31),
    (129, 62),
    (321, 30),
    (375, 14),
    (401, 19),
    (433, 5),
    (448, 8),
    (529, 2),
    (537, 9),
    (801, 2),
    (817, 6),
    (16641, 16),
]

# Public R-numbers are one-based references. The inverter's Modbus PDU addresses
# are zero-based, so R89 is protocol address 0x0058. Metadata below follows the
# TTN/JSD Solar external Modbus map V1.31 used by compatible inverter models.
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
        for register in range(1, 11)
    },
    17: ("Версія протоколу, старше слово", 1.0, "", False, "Система"),
    18: ("Версія протоколу, молодше слово", 1.0, "", False, "Система"),
    27: ("Версія ПЗ плати керування, старше слово", 1.0, "", False, "Система"),
    28: ("Версія ПЗ плати керування, молодше слово", 1.0, "", False, "Система"),
    58: ("Ідентифікатор протоколу B", 1.0, "", False, "Система"),
    65: ("Версія ПЗ", 1.0, "", False, "Система"),
    66: ("Стан з’єднання BMS", 1.0, "", False, "BMS"),
    67: ("Стан інвертора", 1.0, "", False, "Система"),
    68: ("Стан енергетичних клем", 1.0, "", False, "Система"),
    69: ("Стан потоку енергії", 1.0, "", False, "Система"),
    70: ("Стан паралельної роботи", 1.0, "", False, "Система"),
    71: ("Код несправності 1", 1.0, "", False, "Помилки"),
    72: ("Код несправності 2", 1.0, "", False, "Помилки"),
    73: ("Код попередження 1", 1.0, "", False, "Помилки"),
    74: ("Код попередження 2", 1.0, "", False, "Помилки"),
    75: ("Колір переднього RGB, старше слово", 1.0, "", False, "RGB"),
    76: ("Колір переднього RGB, молодше слово", 1.0, "", False, "RGB"),
    77: ("Режим переднього RGB", 1.0, "", False, "RGB"),
    78: ("Колір фонового RGB, старше слово", 1.0, "", False, "RGB"),
    79: ("Колір фонового RGB, молодше слово", 1.0, "", False, "RGB"),
    80: ("Режим фонового RGB", 1.0, "", False, "RGB"),

    81: ("Напруга мережі, фаза A", 0.1, "V", True, "AC"),
    82: ("Струм мережі, фаза A", 0.01, "A", True, "AC"),
    83: ("Частота мережі, фаза A", 0.01, "Hz", True, "AC"),
    84: ("Потужність мережі, фаза A", 1.0, "W", True, "Потужність"),
    85: ("Напруга генератора, фаза A", 0.1, "V", False, "Генератор"),
    86: ("Струм генератора, фаза A", 0.01, "A", False, "Генератор"),
    87: ("Частота генератора, фаза A", 0.01, "Hz", False, "Генератор"),
    88: ("Потужність генератора, фаза A", 1.0, "W", False, "Генератор"),
    89: ("Вихідна напруга навантаження, фаза A", 0.1, "V", True, "AC"),
    90: ("Вихідний струм AC", 0.01, "A", False, "AC"),
    91: ("Вихідна частота AC", 0.01, "Hz", True, "AC"),
    92: ("Активна потужність навантаження", 1.0, "W", True, "Потужність"),
    93: ("Повна потужність навантаження", 1.0, "VA", True, "Потужність"),
    94: ("Завантаження інвертора", 0.1, "%", False, "AC"),
    95: ("Навантаження мережі, фаза A", 1.0, "W", True, "Потужність"),

    129: ("Напруга акумулятора", 0.1, "V", False, "Батарея"),
    130: ("Струм акумулятора", 0.1, "A", True, "Батарея"),
    131: ("Напруга від’ємної клеми батареї", 0.1, "V", True, "Батарея"),
    132: ("Струм від’ємної клеми батареї", 0.1, "A", True, "Батарея"),
    133: ("SOC акумулятора", 0.1, "%", True, "Батарея"),
    134: ("Потужність акумулятора", 1.0, "W", True, "Потужність"),
    135: ("Резерв", 1.0, "", False, "Батарея"),
    136: ("Резерв", 1.0, "", False, "Батарея"),

    137: ("Напруга акумулятора від BMS", 0.1, "V", False, "BMS"),
    138: ("Струм акумулятора від BMS", 0.1, "A", True, "BMS"),
    139: ("SOC від BMS", 1.0, "%", False, "BMS"),
    140: ("Температура акумулятора BMS", 0.1, "°C", True, "Температура"),
    141: ("Точка постійної напруги BMS", 0.1, "V", False, "BMS"),
    142: ("Номінальна ємність BMS", 0.1, "Ah", False, "BMS"),
    143: ("Поточна ємність BMS", 0.1, "Ah", False, "BMS"),
    144: ("Стан зв’язку BMS", 1.0, "", False, "BMS"),
    145: ("Стан мережі літієвої батареї", 1.0, "", False, "BMS"),
    146: ("Код несправності BMS", 1.0, "", False, "BMS"),
    147: ("Код попередження BMS", 1.0, "", False, "BMS"),
    148: ("Резерв", 1.0, "", False, "BMS"),
    149: ("Резерв", 1.0, "", False, "BMS"),
    150: ("Резерв", 1.0, "", False, "BMS"),
    151: ("Напруга PV1", 0.1, "V", True, "PV"),
    152: ("Струм PV1", 0.01, "A", True, "PV"),
    153: ("Потужність PV1", 1.0, "W", True, "PV"),
    154: ("Напруга PV2", 0.1, "V", True, "PV"),
    155: ("Струм PV2", 0.01, "A", True, "PV"),
    156: ("Потужність PV2", 1.0, "W", True, "PV"),
    157: ("Енергія PV за сьогодні", 0.1, "kWh", False, "PV"),
    158: ("Загальна енергія PV", 0.1, "kWh", False, "PV"),
    159: ("Струм заряджання від PV1", 0.1, "A", False, "PV"),
    160: ("Струм заряджання від PV2", 0.1, "A", False, "PV"),
    161: ("Загальна потужність PV", 1.0, "W", False, "PV"),
    162: ("Енергія PV за місяць", 0.1, "kWh", False, "PV"),
    163: ("Енергія PV за рік", 0.1, "kWh", False, "PV"),
    164: ("Енергія заряджання за день", 0.1, "kWh", False, "Енергія"),
    165: ("Енергія заряджання за місяць", 0.1, "kWh", False, "Енергія"),
    166: ("Енергія заряджання за рік", 0.1, "kWh", False, "Енергія"),
    167: ("Загальна енергія заряджання", 0.1, "kWh", False, "Енергія"),
    168: ("Енергія розряджання за день", 0.1, "kWh", False, "Енергія"),
    169: ("Енергія розряджання за місяць", 0.1, "kWh", False, "Енергія"),
    170: ("Енергія розряджання за рік", 0.1, "kWh", False, "Енергія"),
    171: ("Загальна енергія розряджання", 0.1, "kWh", False, "Енергія"),
    172: ("Енергія інвертування за день", 0.1, "kWh", False, "Енергія"),
    173: ("Енергія інвертування за місяць", 0.1, "kWh", False, "Енергія"),
    174: ("Енергія інвертування за рік", 0.1, "kWh", False, "Енергія"),
    175: ("Загальна енергія інвертування", 0.1, "kWh", False, "Енергія"),
    176: ("Енергія навантаження за день", 0.1, "kWh", False, "Енергія"),
    177: ("Енергія навантаження за місяць", 0.1, "kWh", False, "Енергія"),
    178: ("Енергія навантаження за рік", 0.1, "kWh", False, "Енергія"),
    179: ("Загальна енергія навантаження", 0.1, "kWh", False, "Енергія"),
    180: ("Енергія віддачі в мережу за день", 0.1, "kWh", False, "Енергія"),
    181: ("Енергія віддачі в мережу за місяць", 0.1, "kWh", False, "Енергія"),
    182: ("Енергія віддачі в мережу за рік", 0.1, "kWh", False, "Енергія"),
    183: ("Загальна енергія віддачі в мережу", 0.1, "kWh", False, "Енергія"),
    184: ("Енергія споживання з мережі за день", 0.1, "kWh", False, "Енергія"),
    185: ("Енергія споживання з мережі за місяць", 0.1, "kWh", False, "Енергія"),
    186: ("Енергія споживання з мережі за рік", 0.1, "kWh", False, "Енергія"),
    187: ("Загальна енергія споживання з мережі", 0.1, "kWh", False, "Енергія"),
    188: ("Потужність навантаження на виході, фаза A", 1.0, "W", False, "Потужність"),
    189: ("Потужність навантаження на виході, фаза B", 1.0, "W", False, "Потужність"),
    190: ("Потужність навантаження на виході, фаза C", 1.0, "W", False, "Потужність"),

    321: ("Режим виходу", 1.0, "", False, "Режими"),
    322: ("Паралельний режим", 1.0, "", False, "Режими"),
    323: ("Пріоритет виходу", 1.0, "", False, "Режими"),
    324: ("Пріоритет заряджання", 1.0, "", False, "Режими"),
    325: ("Стан автомата інвертора", 1.0, "", False, "Режими"),
    337: ("Тип батареї", 1.0, "", False, "Батарея"),
    339: ("SOC батареї", 1.0, "%", True, "Батарея"),
    341: ("Напруга позитивної DC-шини", 0.1, "V", True, "Батарея"),
    342: ("Напруга позитивної клеми батареї", 0.1, "V", True, "Батарея"),
    343: ("Струм розряджання батареї", 0.1, "A", True, "Батарея"),
    344: ("Струм заряджання батареї", 0.1, "A", True, "Батарея"),
    345: ("Поріг сигналізації перенапруги", 0.1, "V", True, "Батарея"),
    346: ("Поріг сигналізації низької напруги", 0.1, "V", True, "Батарея"),
    349: ("Напруга відсікання другого виходу", 0.1, "V", True, "Батарея"),
    350: ("Час відсікання другого виходу", 1.0, "h", False, "Батарея"),

    375: ("Стан заряджання", 1.0, "", False, "Заряджання"),
    376: ("Напруга заряджання CV", 0.1, "V", True, "Заряджання"),
    377: ("Напруга підтримувального заряджання", 0.1, "V", True, "Заряджання"),
    378: ("Струм заряджання CV", 0.1, "A", True, "Заряджання"),
    379: ("Струм підтримувального заряджання", 0.1, "A", True, "Заряджання"),
    383: ("Напруга вирівнювального заряджання", 0.1, "V", True, "Заряджання"),
    384: ("Час вирівнювального заряджання", 1.0, "h", False, "Заряджання"),
    385: ("Затримка вирівнювального заряджання", 1.0, "h", False, "Заряджання"),
    386: ("Інтервал вирівнювального заряджання", 1.0, "d", False, "Заряджання"),

    401: ("Протокол зв’язку BMS (резерв)", 1.0, "", False, "BMS"),
    402: ("Стан зв’язку BMS", 1.0, "", False, "BMS"),
    403: ("ID пакета BMS", 1.0, "", False, "BMS"),
    404: ("Напруга батареї", 0.1, "V", False, "BMS"),
    405: ("Струм батареї", 0.1, "A", True, "BMS"),
    406: ("Температура батареї", 1.0, "°C", True, "Температура"),
    407: ("SOC батареї", 1.0, "%", False, "BMS"),
    408: ("SOH батареї", 1.0, "%", False, "BMS"),
    409: ("Поточна ємність батареї", 0.01, "Ah", False, "BMS"),
    410: ("Повна зарядна ємність батареї", 0.01, "Ah", False, "BMS"),
    411: ("Точка постійної напруги BMS", 0.1, "V", True, "BMS"),
    412: ("Максимальний струм заряджання BMS", 0.01, "A", True, "BMS"),
    413: ("Дозволений тривалий струм розряджання батареї", 0.1, "A", False, "BMS"),
    414: ("Поріг попередження низького SOC", 1.0, "%", True, "BMS"),
    415: ("Поріг вимкнення за низьким SOC", 1.0, "%", True, "BMS"),
    416: ("Резервний поріг перемикання низького SOC", 0.1, "V", True, "BMS"),
    417: ("Резервний поріг відсікання високого SOC", 0.1, "V", True, "BMS"),
    418: ("Сигналізація BMS", 1.0, "", False, "BMS"),
    419: ("Помилка BMS", 1.0, "", False, "BMS"),

    433: ("Напруга мережі, детальний канал", 0.1, "V", True, "AC"),
    434: ("Струм мережі, детальний канал", 0.01, "A", True, "AC"),
    435: ("Частота мережі, детальний канал", 0.01, "Hz", True, "AC"),
    436: ("Потужність мережі, детальний канал", 10.0, "W", True, "Потужність"),
    437: ("Потужність споживання з мережі", 10.0, "W", True, "Потужність"),
    448: ("Споживання мережі за день, старше слово", 1.0, "", False, "Енергія"),
    449: ("Споживання мережі за день, молодше слово", 1.0, "", False, "Енергія"),
    450: ("Споживання мережі за місяць, старше слово", 1.0, "", False, "Енергія"),
    451: ("Споживання мережі за місяць, молодше слово", 1.0, "", False, "Енергія"),
    452: ("Споживання мережі за рік, старше слово", 1.0, "", False, "Енергія"),
    453: ("Споживання мережі за рік, молодше слово", 1.0, "", False, "Енергія"),
    454: ("Загальне споживання мережі, старше слово", 1.0, "", False, "Енергія"),
    455: ("Загальне споживання мережі, молодше слово", 1.0, "", False, "Енергія"),
    529: ("Пріоритет виходу (фактичний)", 1.0, "", False, "Режими"),
    530: ("Режим входу AC (фактичний)", 1.0, "", False, "Режими"),
    537: ("Вихідна напруга інвертора", 0.1, "V", True, "AC"),
    538: ("Вихідна частота інвертора", 0.01, "Hz", True, "AC"),
    539: ("Вихідний струм інвертора", 0.01, "A", True, "AC"),
    541: ("Вихідна активна потужність інвертора", 1.0, "W", True, "Потужність"),
    542: ("Вихідна повна потужність інвертора", 1.0, "VA", True, "Потужність"),
    545: ("Завантаження виходу інвертора", 0.1, "%", True, "AC"),
    801: ("Швидкість вентилятора", 1.0, "%", False, "Температура"),
    802: ("Стан вентилятора", 1.0, "", False, "Температура"),
    817: ("Температура PV", 0.1, "°C", True, "Температура"),
    818: ("Температура інвертора", 0.1, "°C", True, "Температура"),
    819: ("Температура зарядного модуля", 0.1, "°C", True, "Температура"),
    820: ("Температура зарядного модуля 2", 0.1, "°C", True, "Температура"),
    821: ("Температура довкілля", 0.1, "°C", True, "Температура"),
    822: ("Температура розрядного модуля", 0.1, "°C", True, "Температура"),
    823: ("Температура PV2", 0.1, "°C", True, "Температура"),

    # Writable setup block 0x4100+. Public R labels remain one-based.
    16641: ("Налаштована вихідна напруга", 1.0, "", False, "Налаштування"),
    16642: ("Налаштована вихідна частота", 1.0, "", False, "Налаштування"),
    16643: ("Пріоритет вихідного джерела", 1.0, "", False, "Налаштування"),
    16644: ("Режим входу AC", 1.0, "", False, "Налаштування"),
    16645: ("Пріоритет джерела заряджання", 1.0, "", False, "Налаштування"),
    16646: ("Струм заряджання від AC", 1.0, "A", False, "Налаштування"),
    16647: ("Максимальний струм заряджання", 1.0, "", False, "Налаштування"),
    16648: ("Тип батареї", 1.0, "", False, "Налаштування"),
    16649: ("Поріг низької напруги батареї", 0.1, "V", False, "Налаштування"),
    16650: ("Поріг вимкнення батареї", 0.1, "V", False, "Налаштування"),
    16651: ("Напруга основного заряджання", 0.1, "V", False, "Налаштування"),
    16652: ("Напруга підтримувального заряджання", 0.1, "V", False, "Налаштування"),
    16653: ("Поріг переходу батарея → AC", 0.1, "V", False, "Налаштування"),
    16654: ("Поріг повернення AC → батарея", 0.1, "V", False, "Налаштування"),
    16655: ("Нижній поріг напруги мережі", 1.0, "V", False, "Налаштування"),
    16656: ("Верхній поріг напруги мережі", 1.0, "V", False, "Налаштування"),

}

REGISTER_MAP_COLUMNS = ("register", "name", "unit", "scale", "display")
register_map_lock = threading.RLock()
register_map_overrides: dict[int, dict[str, Any]] = {}
register_map_error = ""


def _safe_register_map_text(value: str, field: str, maximum: int) -> str:
    """Validate user-visible CSV metadata before it reaches HTML rendering."""
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValueError(f"{field} is longer than {maximum} characters")
    if any(character in cleaned for character in '<>"'):
        raise ValueError(f'{field} cannot contain <, >, or "')
    if any(ord(character) < 32 and character not in "\t" for character in cleaned):
        raise ValueError(f"{field} contains a control character")
    return cleaned


def parse_register_map_csv(payload: bytes) -> dict[int, dict[str, Any]]:
    """Parse a metadata-only register override CSV without changing Modbus state."""
    if len(payload) > REGISTER_MAP_MAX_BYTES:
        raise ValueError("CSV file is larger than 1 MiB")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("CSV file must use UTF-8 encoding") from error

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV header is missing")
    headers = {str(header).strip().lower(): str(header) for header in reader.fieldnames}

    def column(*aliases: str) -> str | None:
        return next((headers[alias] for alias in aliases if alias in headers), None)

    register_column = column("register", "r", "address", "mbpoll_register")
    name_column = column("name", "label")
    unit_column = column("unit", "units")
    scale_column = column("scale", "multiplier")
    display_column = column("display", "display_value", "value")
    if register_column is None:
        raise ValueError("CSV must contain a register column")
    if not any((name_column, unit_column, scale_column, display_column)):
        raise ValueError("CSV must contain at least one of: name, unit, scale, display")

    parsed: dict[int, dict[str, Any]] = {}
    for row_number, row in enumerate(reader, start=2):
        register_text = str(row.get(register_column, "") or "").strip()
        if not register_text and not any(str(value or "").strip() for value in row.values()):
            continue
        if register_text.upper().startswith("R"):
            register_text = register_text[1:].strip()
        try:
            register = int(register_text)
        except ValueError as error:
            raise ValueError(f"row {row_number}: invalid register {register_text!r}") from error
        if not 1 <= register <= 65536:
            raise ValueError(f"row {row_number}: register must be between 1 and 65536")
        if register in parsed:
            raise ValueError(f"row {row_number}: duplicate register R{register}")

        override: dict[str, Any] = {}
        if name_column is not None:
            name = _safe_register_map_text(str(row.get(name_column, "") or ""), "name", 200)
            if name:
                override["name"] = name
        if unit_column is not None:
            unit = _safe_register_map_text(
                str(row.get(unit_column, "") or ""), "unit", 30
            )
            if unit:
                override["unit"] = unit
        if scale_column is not None:
            scale_text = str(row.get(scale_column, "") or "").strip()
            if scale_text:
                try:
                    scale = float(scale_text)
                except ValueError as error:
                    raise ValueError(f"row {row_number}: invalid scale {scale_text!r}") from error
                if not math.isfinite(scale) or scale <= 0 or scale > 1_000_000:
                    raise ValueError(f"row {row_number}: scale must be greater than 0 and at most 1000000")
                override["scale"] = scale
        if display_column is not None:
            display = _safe_register_map_text(
                str(row.get(display_column, "") or ""), "display", 100
            )
            if display:
                override["display"] = display
        if not override:
            raise ValueError(f"row {row_number}: no metadata override was provided")
        parsed[register] = override
    return parsed


def _canonical_register_map_csv(overrides: dict[int, dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=REGISTER_MAP_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for register, override in sorted(overrides.items()):
        writer.writerow({
            "register": register,
            "name": override.get("name", ""),
            "unit": override.get("unit", ""),
            "scale": override.get("scale", ""),
            "display": override.get("display", ""),
        })
    return output.getvalue()


def replace_register_map(payload: bytes) -> dict[str, Any]:
    """Persist and activate a complete metadata-only register override map."""
    global register_map_error, register_map_overrides
    overrides = parse_register_map_csv(payload)
    csv_text = _canonical_register_map_csv(overrides)
    temporary_path = REGISTER_MAP_PATH.with_suffix(REGISTER_MAP_PATH.suffix + ".tmp")
    with register_map_lock:
        try:
            REGISTER_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(csv_text, encoding="utf-8", newline="")
            os.replace(temporary_path, REGISTER_MAP_PATH)
        except OSError as error:
            register_map_error = str(error)
            raise
        register_map_overrides = overrides
        register_map_error = ""
    return {"ok": True, "count": len(overrides), "filename": REGISTER_MAP_PATH.name}


def load_register_map() -> None:
    """Load persisted metadata overrides without preventing dashboard startup."""
    global register_map_error, register_map_overrides
    if not REGISTER_MAP_PATH.exists():
        return
    try:
        overrides = parse_register_map_csv(REGISTER_MAP_PATH.read_bytes())
    except (OSError, ValueError, csv.Error) as error:
        register_map_error = str(error)
        return
    with register_map_lock:
        register_map_overrides = overrides
        register_map_error = ""


def register_override(register: int) -> dict[str, Any]:
    with register_map_lock:
        return dict(register_map_overrides.get(register, {}))


def register_metadata(register: int) -> tuple[str, float, str, bool, str]:
    """Return built-in metadata merged with the current CSV override."""
    name, scale, unit, signed, group = REGISTER_CONFIG.get(
        register, (f"Регістр {register}", 1.0, "", False, "Сире")
    )
    override = register_override(register)
    return (
        str(override.get("name", name)),
        float(override.get("scale", scale)),
        str(override.get("unit", unit)),
        signed,
        group,
    )


def register_map_status() -> dict[str, Any]:
    with register_map_lock:
        return {
            "count": len(register_map_overrides),
            "filename": REGISTER_MAP_PATH.name if REGISTER_MAP_PATH.exists() else "",
            "error": register_map_error,
        }


load_register_map()

METER_DEFINITIONS = [
    (81, [433], "Напруга мережі", 0.0, 300.0, "V"),
    (82, [434], "Струм мережі", 0.0, 100.0, "A"),
    (84, [437, 436], "Потужність мережі", 0.0, 15000.0, "W"),
    (83, [435], "Частота мережі", 45.0, 55.0, "Hz"),
    (89, [537], "Вихідна напруга AC", 0.0, 300.0, "V"),
    (92, [], "Активна потужність навантаження", 0.0, 12000.0, "W"),
    (93, [], "Повна потужність навантаження", 0.0, 15000.0, "VA"),
    (90, [], "Вихідний струм AC", 0.0, 100.0, "A"),
    (94, [], "Завантаження інвертора", 0.0, 100.0, "%"),
    (151, [], "Напруга PV1", 0.0, 500.0, "V"),
    (152, [], "Струм PV1", 0.0, 50.0, "A"),
    (153, [], "Потужність PV1", 0.0, 12000.0, "W"),
    (154, [], "Напруга PV2", 0.0, 500.0, "V"),
    (155, [], "Струм PV2", 0.0, 50.0, "A"),
    (156, [], "Потужність PV2", 0.0, 12000.0, "W"),
    (16655, [], "Нижній поріг вхідної напруги мережі", 0.0, 300.0, "V"),
    (129, [137, 404, 342], "Напруга акумулятора", 40.0, 65.0, "V"),
    (130, [], "Струм акумулятора", -150.0, 150.0, "A"),
    (133, [139, 407, 339], "Рівень заряду акумулятора", 0.0, 100.0, "%"),
    (134, [], "Потужність акумулятора", -15000.0, 15000.0, "W"),
    (818, [], "Температура інвертора", -20.0, 150.0, "°C"),
    (140, [406], "Температура акумулятора BMS", -20.0, 100.0, "°C"),
    (408, [], "SOH батареї", 0.0, 100.0, "%"),
    (141, [411, 376, 377], "Максимальна напруга заряду", 40.0, 65.0, "V"),
    (343, [], "Струм BMS, канал 1", -150.0, 150.0, "A"),
    (344, [], "Струм BMS, канал 2", -150.0, 150.0, "A"),
    (345, [], "Верхня межа напруги", 40.0, 65.0, "V"),
    (346, [], "Нижня межа напруги", 40.0, 65.0, "V"),
    (349, [], "Поріг низької напруги", 40.0, 65.0, "V"),
    (412, [378, 379], "Максимальний струм заряджання", 0.0, 150.0, "A"),
    (413, [], "Дозволений тривалий струм розряджання батареї", 0.0, 250.0, "A"),
    (409, [], "Поточна ємність батареї", 0.0, 1000.0, "Ah"),
    (410, [], "Повна ємність батареї", 0.0, 1000.0, "Ah"),
    (415, [], "Поріг вимкнення за низьким SOC", 0.0, 100.0, "%"),
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
    name, scale, unit, use_signed, group = register_metadata(register)

    base = signed16(raw) if use_signed else raw
    # This installed inverter reports R130 with the opposite direction to the
    # UI convention: charging is positive and discharging is negative.
    if register == 130:
        base = -base
    value = base * scale

    if scale == 1.0:
        display = str(int(value))
    elif scale == 0.1:
        display = f"{value:.1f}"
    elif scale == 0.01:
        display = f"{value:.2f}"
    else:
        display = f"{value:.3f}".rstrip("0").rstrip(".")
    display = str(register_override(register).get("display", display))

    return name, display, unit, value, group


def decode_identifier(values: dict[int, int]) -> str:
    data = bytearray()

    for register in range(1, 11):
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
    if clean_page != "LCD" and re.fullmatch(r"P(?:[1-9]|1\d|2[0-6])", clean_page) is None:
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
    """Integrate confirmed PV1 + PV2 power into daily energy storage."""
    global solar_energy_last_sample_at, solar_energy_last_power_w
    global solar_energy_last_flush_monotonic, solar_energy_error

    powers: list[float] = []
    for register in (153, 156):
        if register not in fresh_values:
            continue
        value = normalize(register, fresh_values[register])[3]
        if value is not None:
            powers.append(max(0.0, value))
    if not powers:
        return

    now = datetime.now(MADRID_TIME_ZONE)
    power_w = sum(powers)
    with stats_lock:
        if solar_energy_last_sample_at is not None and solar_energy_last_power_w is not None:
            elapsed_seconds = (now - solar_energy_last_sample_at).total_seconds()
            if 0 < elapsed_seconds <= 30:
                watt_hours = (solar_energy_last_power_w + power_w) / 2 * elapsed_seconds / 3600
                day = now.date().isoformat()
                solar_energy_pending_wh[day] = solar_energy_pending_wh.get(day, 0.0) + watt_hours
        solar_energy_last_sample_at = now
        solar_energy_last_power_w = power_w
        if time.monotonic() - solar_energy_last_flush_monotonic >= 60:
            if flush_solar_energy_locked():
                solar_energy_last_flush_monotonic = time.monotonic()


def solar_energy_summary() -> dict[str, Any]:
    """Return current and all-time SQLite-backed production in kWh."""
    global solar_energy_error
    now = datetime.now(MADRID_TIME_ZONE)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    daily: dict[str, float] = {}
    with state_lock:
        live_values = dict(state.get("values", {}))
    direct_today = normalize(157, live_values[157])[3] if 157 in live_values else None
    direct_total = normalize(158, live_values[158])[3] if 158 in live_values else None

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
        "today_kwh": direct_today if direct_today is not None else total_since(today),
        "week_kwh": total_since(week_start),
        "month_kwh": total_since(month_start),
        "year_kwh": total_since(year_start),
        "total_kwh": direct_total if direct_total is not None else sum(daily.values()) / 1000,
        "source_register": "R157 / R158; R153 + R156",
        "storage": "sqlite",
        "estimated": False,
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
