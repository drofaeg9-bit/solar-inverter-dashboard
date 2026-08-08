from __future__ import annotations

from typing import Any


def effective_battery_soc(value: float | None, terminal_raw: Any) -> float | None:
    """Return display SOC consistent with the R68 battery terminal state."""
    try:
        battery_state = (int(terminal_raw) >> 8) & 0x07
    except (TypeError, ValueError):
        battery_state = None
    return 100.0 if battery_state == 4 else value
