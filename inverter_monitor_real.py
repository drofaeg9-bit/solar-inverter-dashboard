#!/usr/bin/env python3
"""
Terminal UI to monitor inverter data from actual Modbus device.
Requires: pip install pymodbus
"""
import time
import sys
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# Register mapping and conversion factors
REGISTER_MAP = {
    # Grid voltage (V)
    89: {"name": "Grid Voltage L1", "unit": "V", "factor": 0.1},
    90: {"name": "Grid Voltage L2", "unit": "V", "factor": 0.1},
    91: {"name": "Grid Voltage L3", "unit": "V", "factor": 0.1},
    
    # Grid current (A)
    92: {"name": "Grid Current L1", "unit": "A", "factor": 0.01},
    93: {"name": "Grid Current L2", "unit": "A", "factor": 0.01},
    94: {"name": "Grid Current L3", "unit": "A", "factor": 0.01},
    
    # PV voltage (V)
    129: {"name": "PV1 Voltage", "unit": "V", "factor": 0.1},
    137: {"name": "PV2 Voltage", "unit": "V", "factor": 0.1},
    
    # PV current (A)
    130: {"name": "PV1 Current", "unit": "A", "factor": 0.01},
    138: {"name": "PV2 Current", "unit": "A", "factor": 0.01},
    
    # PV power (W)
    341: {"name": "PV1 Power", "unit": "W", "factor": 1},
    342: {"name": "PV2 Power", "unit": "W", "factor": 1},
    
    # Battery voltage (V)
    343: {"name": "Battery Voltage", "unit": "V", "factor": 0.1},
    
    # Battery current (A)
    344: {"name": "Battery Current", "unit": "A", "factor": 0.01},
    
    # Battery power (W)
    345: {"name": "Battery Power", "unit": "W", "factor": 1},
    
    # Total power (W)
    385: {"name": "Total Output Power", "unit": "W", "factor": 1},
    
    # Frequency (Hz)
    386: {"name": "Grid Frequency", "unit": "Hz", "factor": 0.01},
    
    # Temperature (C)
    376: {"name": "Inverter Temperature", "unit": "°C", "factor": 0.1},
    377: {"name": "Heat Sink Temperature", "unit": "°C", "factor": 0.1},
    
    # Daily energy (kWh)
    413: {"name": "Daily Energy", "unit": "kWh", "factor": 0.1},
    
    # Total energy (kWh)
    451: {"name": "Total Energy", "unit": "kWh", "factor": 0.1},
}

def convert_value(raw_value, factor):
    """Convert raw register value to engineering units."""
    if raw_value == 65535 or raw_value == -1:
        return "N/A"
    # Handle signed 16-bit values
    if raw_value > 32767:
        raw_value = raw_value - 65536
    return round(raw_value * factor, 2)

def display_header():
    """Display the header of the monitoring UI."""
    print("\n" + "=" * 60)
    print(" " * 15 + "INVERTER MONITOR")
    print(" " * 20 + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

def display_section(title, registers, data):
    """Display a section of related metrics."""
    print(f"\n{title}")
    print("-" * 60)
    
    for reg in registers:
        if reg in REGISTER_MAP and reg in data:
            info = REGISTER_MAP[reg]
            raw = data[reg]
            converted = convert_value(raw, info["factor"])
            print(f"  {info['name']:25s}: {converted:>8} {info['unit']}")

def display_all_metrics(data):
    """Display all metrics in organized sections."""
    # Clear screen (works on most terminals)
    print("\033c", end="")
    
    display_header()
    
    # Grid section
    display_section("GRID METRICS", [89, 90, 91, 92, 93, 94, 386], data)
    
    # PV section
    display_section("PV METRICS", [129, 130, 137, 138, 341, 342], data)
    
    # Battery section
    display_section("BATTERY METRICS", [343, 344, 345], data)
    
    # Power section
    display_section("POWER METRICS", [385, 413, 451], data)
    
    # Temperature section
    display_section("TEMPERATURE", [376, 377], data)
    
    print("\n" + "=" * 60)
    print("Press Ctrl+C to exit | Updating every 1 second")
    print("=" * 60 + "\n")

def read_modbus_registers(client, start_addr=1, count=500):
    """Read registers from Modbus device."""
    try:
        result = client.read_holding_registers(start_addr, count)
        if not result.isError():
            return result.registers
        else:
            print(f"Modbus error: {result}")
            return None
    except ModbusException as e:
        print(f"Modbus exception: {e}")
        return None

def main():
    """Main monitoring loop."""
    # Modbus connection settings - replace with your inverter's IP
    MODBUS_IP = "192.168.1.100"  # REPLACE THIS with your Orange Pi 3 IP address
    MODBUS_PORT = 502
    
    print(f"Connecting to Modbus device at {MODBUS_IP}:{MODBUS_PORT}...")
    
    client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)
    
    if not client.connect():
        print("Failed to connect to Modbus device")
        sys.exit(1)
    
    print("Connected! Starting monitor...")
    print("Press Ctrl+C to stop\n")
    time.sleep(2)
    
    try:
        while True:
            # Read all registers (1-500)
            registers = read_modbus_registers(client)
            
            if registers:
                # Convert to dict with register addresses
                data = {i+1: val for i, val in enumerate(registers)}
                
                # Display the data
                display_all_metrics(data)
            else:
                print("Failed to read registers, retrying...")
            
            # Wait 1 second before next update
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    finally:
        client.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
