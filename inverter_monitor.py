#!/usr/bin/env python3
"""
Simple terminal UI to monitor inverter data from Modbus registers.
Updates every second with converted values.
"""
import time
import sys
from datetime import datetime

# Register mapping and conversion factors
# Based on typical solar inverter register layouts
REGISTER_MAP = {
    # Grid voltage (V) - typically register 089
    89: {"name": "Grid Voltage L1", "unit": "V", "factor": 0.1},
    90: {"name": "Grid Voltage L2", "unit": "V", "factor": 0.1},
    91: {"name": "Grid Voltage L3", "unit": "V", "factor": 0.1},
    
    # Grid current (A) - typically register 092-094
    92: {"name": "Grid Current L1", "unit": "A", "factor": 0.01},
    93: {"name": "Grid Current L2", "unit": "A", "factor": 0.01},
    94: {"name": "Grid Current L3", "unit": "A", "factor": 0.01},
    
    # PV voltage (V) - typically register 129, 137
    129: {"name": "PV1 Voltage", "unit": "V", "factor": 0.1},
    137: {"name": "PV2 Voltage", "unit": "V", "factor": 0.1},
    
    # PV current (A) - typically register 130, 138
    130: {"name": "PV1 Current", "unit": "A", "factor": 0.01},
    138: {"name": "PV2 Current", "unit": "A", "factor": 0.01},
    
    # PV power (W) - typically register 341, 342
    341: {"name": "PV1 Power", "unit": "W", "factor": 1},
    342: {"name": "PV2 Power", "unit": "W", "factor": 1},
    
    # Battery voltage (V) - typically register 343
    343: {"name": "Battery Voltage", "unit": "V", "factor": 0.1},
    
    # Battery current (A) - typically register 344
    344: {"name": "Battery Current", "unit": "A", "factor": 0.01},
    
    # Battery power (W) - typically register 345
    345: {"name": "Battery Power", "unit": "W", "factor": 1},
    
    # Total power (W) - typically register 385
    385: {"name": "Total Output Power", "unit": "W", "factor": 1},
    
    # Frequency (Hz) - typically register 386
    386: {"name": "Grid Frequency", "unit": "Hz", "factor": 0.01},
    
    # Temperature (C) - typically register 376, 377
    376: {"name": "Inverter Temperature", "unit": "°C", "factor": 0.1},
    377: {"name": "Heat Sink Temperature", "unit": "°C", "factor": 0.1},
    
    # Daily energy (kWh) - typically register 413
    413: {"name": "Daily Energy", "unit": "kWh", "factor": 0.1},
    
    # Total energy (kWh) - typically register 451
    451: {"name": "Total Energy", "unit": "kWh", "factor": 0.1},
}

# Sample data from your scan (will be replaced with real Modbus reads)
SAMPLE_DATA = {
    89: 2300, 90: 239, 91: 5000, 92: 243, 93: 550, 94: 45,
    129: 530, 130: 55, 137: 530, 138: -59,
    341: 4568, 342: 530, 343: -82, 344: -84, 345: 610,
    385: 7200, 386: 2160,
    376: 571, 377: 571,
    413: 1700, 451: 19604,
}

def convert_value(raw_value, factor):
    """Convert raw register value to engineering units."""
    if raw_value == 65535 or raw_value == -1:
        return "N/A"
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
        elif reg in data:
            print(f"  Register {reg:3d}: {data[reg]:>8} (raw)")

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

def simulate_modbus_read():
    """Simulate reading from Modbus (replace with actual Modbus library)."""
    # In real implementation, this would use pymodbus or similar
    # For now, return sample data with slight variations
    import random
    data = SAMPLE_DATA.copy()
    
    # Add some random variation to simulate live data
    for reg in [89, 90, 91, 385, 341, 342]:
        if reg in data:
            variation = random.randint(-5, 5)
            data[reg] = max(0, data[reg] + variation)
    
    return data

def main():
    """Main monitoring loop."""
    print("Starting Inverter Monitor...")
    print("Press Ctrl+C to stop\n")
    time.sleep(2)
    
    try:
        while True:
            # Read data from inverter (replace with actual Modbus read)
            data = simulate_modbus_read()
            
            # Display the data
            display_all_metrics(data)
            
            # Wait 1 second before next update
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
