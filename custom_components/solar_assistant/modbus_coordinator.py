"""Modbus coordinator for direct inverter connection."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    CONF_MODBUS_IP,
    CONF_MODBUS_PORT,
    CONF_MODBUS_SLAVE_ID,
)

_LOGGER = logging.getLogger(__name__)

# Confirmed register mapping shared with the standalone inverter dashboard.
# Registers whose meaning is still speculative are intentionally not exposed as
# Home Assistant entities.
REGISTER_MAP = {
    89: {"name": "grid_voltage_l1", "unit": "V", "factor": 0.1},
    90: {"name": "ac_output_current", "unit": "A", "factor": 0.01},
    91: {"name": "grid_frequency", "unit": "Hz", "factor": 0.01},
    92: {"name": "load_active_power", "unit": "W", "factor": 1.0},
    93: {"name": "load_apparent_power", "unit": "VA", "factor": 1.0},
    94: {"name": "inverter_load", "unit": "%", "factor": 0.1},
    129: {"name": "battery_voltage", "unit": "V", "factor": 0.1},
    130: {
        "name": "battery_current",
        "unit": "A",
        "factor": 0.1,
        "signed": True,
    },
    133: {"name": "battery_state_of_charge", "unit": "%", "factor": 1.0},
    134: {"name": "battery_power", "unit": "W", "factor": 1.0, "signed": True},
    137: {"name": "bms_battery_voltage", "unit": "V", "factor": 0.1},
    138: {"name": "bms_battery_current", "unit": "A", "factor": 0.1, "signed": True},
    139: {"name": "bms_state_of_charge", "unit": "%", "factor": 1.0},
    140: {"name": "battery_temperature", "unit": "°C", "factor": 0.1},
    141: {"name": "bms_max_charge_voltage", "unit": "V", "factor": 0.1},
    144: {"name": "bms_status_flags", "unit": "", "factor": 1.0},
    157: {"name": "inverter_operating_mode", "unit": "", "factor": 1.0},
    158: {"name": "grid_input_low_voltage_threshold", "unit": "V", "factor": 1.0},
    160: {"name": "grid_current", "unit": "A", "factor": 0.01},
    166: {"name": "grid_power", "unit": "W", "factor": 1.0},
    321: {"name": "bms_activity", "unit": "", "factor": 1.0},
    324: {"name": "bms_type_or_protocol", "unit": "", "factor": 1.0},
    325: {"name": "bms_configuration", "unit": "", "factor": 1.0},
    337: {"name": "bms_state", "unit": "", "factor": 1.0},
    339: {"name": "bms_extended_soc", "unit": "%", "factor": 1.0},
    341: {"name": "bms_unknown_dynamic_parameter", "unit": "", "factor": 1.0},
    342: {"name": "bms_extended_voltage", "unit": "V", "factor": 0.1},
    343: {"name": "bms_current_channel_1", "unit": "A", "factor": 0.1, "signed": True},
    344: {"name": "bms_current_channel_2", "unit": "A", "factor": 0.1, "signed": True},
    345: {"name": "bms_upper_voltage_limit", "unit": "V", "factor": 0.1},
    346: {"name": "bms_lower_voltage_limit", "unit": "V", "factor": 0.1},
    349: {"name": "bms_low_voltage_threshold", "unit": "V", "factor": 0.1},
    350: {"name": "bms_unknown_signed_parameter", "unit": "", "factor": 1.0, "signed": True},
    376: {"name": "charge_voltage", "unit": "V", "factor": 0.1},
    377: {"name": "float_voltage", "unit": "V", "factor": 0.1},
    378: {"name": "maximum_charge_current", "unit": "A", "factor": 0.1},
    379: {"name": "additional_charge_current_limit", "unit": "A", "factor": 0.1},
    383: {"name": "high_voltage_threshold", "unit": "V", "factor": 0.1},
    385: {"name": "power_limit_or_rating", "unit": "W", "factor": 1.0},
    386: {"name": "power_limiting_parameter", "unit": "W", "factor": 1.0},
    401: {"name": "battery_type_or_module_count", "unit": "", "factor": 1.0},
    402: {"name": "bms_communication", "unit": "", "factor": 1.0},
    403: {"name": "bms_primary_status_flags", "unit": "", "factor": 1.0},
    404: {"name": "bms_primary_voltage", "unit": "V", "factor": 0.1},
    405: {"name": "bms_primary_current", "unit": "A", "factor": 0.1, "signed": True},
    406: {"name": "bms_primary_temperature", "unit": "°C", "factor": 0.1},
    407: {"name": "bms_primary_soc", "unit": "%", "factor": 1.0},
    408: {"name": "bms_primary_soh", "unit": "%", "factor": 1.0},
    411: {"name": "bms_maximum_charge_voltage", "unit": "V", "factor": 0.1},
    412: {"name": "bms_maximum_allowed_current", "unit": "A", "factor": 0.1},
    413: {"name": "battery_capacity_parameter", "unit": "Ah", "factor": 0.1},
    414: {"name": "bms_reserved", "unit": "", "factor": 1.0},
    415: {"name": "low_soc_threshold", "unit": "%", "factor": 1.0},
    416: {"name": "middle_soc_threshold", "unit": "%", "factor": 1.0},
    417: {"name": "high_soc_threshold", "unit": "%", "factor": 1.0},
    16643: {"name": "output_source_priority", "unit": "", "factor": 1.0},
    16644: {"name": "ac_input_mode", "unit": "", "factor": 1.0},
    16645: {"name": "charging_source_priority", "unit": "", "factor": 1.0},
}

# Compact reads mirror the standalone dashboard and stay below the Modbus
# protocol limit of 125 holding registers per request. Register numbers in the
# project are one-based; pymodbus addresses are zero-based.
REGISTER_BLOCKS: tuple[tuple[int, int], ...] = (
    (89, 6),
    (129, 16),
    (157, 4),
    (166, 1),
    (321, 30),
    (376, 11),
    (401, 17),
    (16643, 3),
)


def convert_value(
    raw_value: int,
    factor: float,
    *,
    signed: bool = False,
    invert: bool = False,
) -> float | None:
    """Convert raw register value to engineering units."""
    if raw_value == 65535 or raw_value == -1:
        return None
    if signed and raw_value > 32767:
        raw_value = raw_value - 65536
    if invert:
        raw_value = -raw_value
    return round(raw_value * factor, 2)


class ModbusCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from Modbus inverter."""

    def __init__(self, hass: HomeAssistant, config_data: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        self.modbus_ip = config_data[CONF_MODBUS_IP]
        self.modbus_port = config_data.get(CONF_MODBUS_PORT, 502)
        self.modbus_slave_id = config_data.get(CONF_MODBUS_SLAVE_ID, 1)
        
        self.client = ModbusTcpClient(self.modbus_ip, port=self.modbus_port)
        
        super().__init__(
            hass,
            _LOGGER,
            name="SolarAssistant Modbus",
            update_interval=timedelta(seconds=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Modbus device."""
        return await self.hass.async_add_executor_job(self._read_register_data)

    def _read_holding_block(self, start: int, count: int) -> Any:
        """Read one one-based project block with old/new pymodbus support."""
        address = start - 1
        try:
            return self.client.read_holding_registers(
                address,
                count=count,
                device_id=self.modbus_slave_id,
            )
        except TypeError:
            return self.client.read_holding_registers(
                address,
                count=count,
                slave=self.modbus_slave_id,
            )

    def _read_register_data(self) -> dict[str, Any]:
        """Perform blocking Modbus I/O outside Home Assistant's event loop."""
        try:
            if not self.client.connect():
                _LOGGER.error("Failed to connect to Modbus device")
                return {}

            data: dict[str, Any] = {}
            successful_blocks = 0
            for start, count in REGISTER_BLOCKS:
                try:
                    result = self._read_holding_block(start, count)
                except (ModbusException, OSError) as error:
                    _LOGGER.warning("Modbus block R%s-R%s failed: %s", start, start + count - 1, error)
                    continue
                if result.isError():
                    _LOGGER.warning("Modbus block R%s-R%s returned error: %s", start, start + count - 1, result)
                    continue
                successful_blocks += 1
                for offset, raw_value in enumerate(result.registers):
                    reg_addr = start + offset
                    reg_info = REGISTER_MAP.get(reg_addr)
                    if reg_info is None:
                        continue
                    converted = convert_value(
                        raw_value,
                        reg_info["factor"],
                        signed=reg_info.get("signed", False),
                        invert=reg_info.get("invert", False),
                    )
                    
                    if converted is not None:
                        data[reg_info["name"]] = {
                            "value": converted,
                            "unit": reg_info["unit"],
                        }

            if successful_blocks == 0:
                _LOGGER.error("All Modbus register blocks failed")
                return {}

            battery_current = data.get("battery_current", {}).get("value")
            battery_power = data.get("battery_power", {}).get("value")
            if (
                isinstance(battery_current, (int, float))
                and abs(battery_current) >= 0.3
                and isinstance(battery_power, (int, float))
            ):
                data["battery_power"]["value"] = (
                    abs(battery_power) if battery_current > 0 else -abs(battery_power)
                )
            
            return data

        except ModbusException as error:
            _LOGGER.error("Modbus exception: %s", error)
            return {}
        except Exception:
            _LOGGER.exception("Unexpected error reading Modbus")
            return {}
        finally:
            self.client.close()

    async def async_stop(self) -> None:
        """Stop the coordinator and close connection."""
        self.client.close()
        await super().async_stop()
