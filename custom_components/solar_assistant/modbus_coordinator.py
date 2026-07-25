"""Modbus coordinator for direct inverter connection."""
from __future__ import annotations

import logging
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

# Register mapping and conversion factors
REGISTER_MAP = {
    # Grid voltage (V)
    89: {"name": "grid_voltage_l1", "unit": "V", "factor": 0.1},
    90: {"name": "grid_voltage_l2", "unit": "V", "factor": 0.1},
    91: {"name": "grid_voltage_l3", "unit": "V", "factor": 0.1},
    
    # Grid current (A)
    92: {"name": "grid_current_l1", "unit": "A", "factor": 0.01},
    93: {"name": "grid_current_l2", "unit": "A", "factor": 0.01},
    94: {"name": "grid_current_l3", "unit": "A", "factor": 0.01},
    
    # PV voltage (V)
    129: {"name": "pv1_voltage", "unit": "V", "factor": 0.1},
    137: {"name": "pv2_voltage", "unit": "V", "factor": 0.1},
    
    # PV current (A)
    130: {"name": "pv1_current", "unit": "A", "factor": 0.01},
    138: {"name": "pv2_current", "unit": "A", "factor": 0.01},
    
    # PV power (W)
    341: {"name": "pv1_power", "unit": "W", "factor": 1},
    342: {"name": "pv2_power", "unit": "W", "factor": 1},
    
    # Battery voltage (V)
    343: {"name": "battery_voltage", "unit": "V", "factor": 0.1},
    
    # Battery current (A)
    344: {"name": "battery_current", "unit": "A", "factor": 0.01},
    
    # Battery power (W)
    345: {"name": "battery_power", "unit": "W", "factor": 1},
    
    # Total power (W)
    385: {"name": "total_output_power", "unit": "W", "factor": 1},
    
    # Frequency (Hz)
    386: {"name": "grid_frequency", "unit": "Hz", "factor": 0.01},
    
    # Temperature (C)
    376: {"name": "inverter_temperature", "unit": "°C", "factor": 0.1},
    377: {"name": "heat_sink_temperature", "unit": "°C", "factor": 0.1},
    
    # Daily energy (kWh)
    413: {"name": "daily_energy", "unit": "kWh", "factor": 0.1},
    
    # Total energy (kWh)
    451: {"name": "total_energy", "unit": "kWh", "factor": 0.1},
}


def convert_value(raw_value: int, factor: float) -> float | None:
    """Convert raw register value to engineering units."""
    if raw_value == 65535 or raw_value == -1:
        return None
    # Handle signed 16-bit values
    if raw_value > 32767:
        raw_value = raw_value - 65536
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
            update_interval=1,  # Update every second
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Modbus device."""
        try:
            # Connect to Modbus device
            if not self.client.connect():
                _LOGGER.error("Failed to connect to Modbus device")
                return {}
            
            # Read all registers (1-500)
            result = self.client.read_holding_registers(1, 500, slave=self.modbus_slave_id)
            
            if result.isError():
                _LOGGER.error(f"Modbus read error: {result}")
                return {}
            
            # Convert registers to sensor data
            data = {}
            registers = result.registers
            
            for reg_addr, reg_info in REGISTER_MAP.items():
                if reg_addr <= len(registers):
                    raw_value = registers[reg_addr - 1]  # 0-indexed
                    converted = convert_value(raw_value, reg_info["factor"])
                    
                    if converted is not None:
                        data[reg_info["name"]] = {
                            "value": converted,
                            "unit": reg_info["unit"],
                        }
            
            return data
            
        except ModbusException as e:
            _LOGGER.error(f"Modbus exception: {e}")
            return {}
        except Exception as e:
            _LOGGER.exception("Unexpected error reading Modbus")
            return {}
        finally:
            self.client.close()

    async def async_stop(self) -> None:
        """Stop the coordinator and close connection."""
        self.client.close()
        await super().async_stop()
