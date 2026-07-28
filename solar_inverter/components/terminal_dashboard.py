from __future__ import annotations

import threading
import time
from types import ModuleType

try:
    import curses
except ModuleNotFoundError:  # The standard Windows build does not ship _curses.
    curses: ModuleType | None = None

from ..services.inverter_service import *

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
    if curses is None:
        raise RuntimeError("The terminal dashboard requires Python curses support")

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
