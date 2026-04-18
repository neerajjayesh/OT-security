# KSEB SCADA — OT Environment Simulator

A dark green-on-black SCADA HMI dashboard simulating a **Kerala State Electricity Board 33/11 kV substation** environment. Built with PyQt5 and pymodbus.

![Python](https://img.shields.io/badge/Python-3.10+-green) ![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-blue) ![Modbus](https://img.shields.io/badge/Modbus_TCP-5020-orange)

## What It Simulates

- **Generation Panel** — Active Power (MW), Grid Frequency (Hz) with red zones, Power Factor, Hydro source indicator
- **System Health Panel** — Large frequency/voltage readouts, Load Demand bar, kWh odometer, Trip meter
- **Feeder/Distribution Panel** — 4 feeder rows (status, load %, breaker), Transformer temperature gauge, Transformer load bar
- **Modbus TCP Server** — Virtual slave on `localhost:5020` with 13 holding registers updated in real time
- **Fault Injection** — Random fault scenarios with pulsing warning indicators and event logging
- **Live Simulation** — Bounded random-walk telemetry with mean-reversion, updated every 1 second

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Project Structure

- `main.py` — Application entry point
- `dashboard.py` — Core UI layout and main window (`KSEBDashboard`)
- `components.py` — Reusable SCADA UI widgets (gauges, indicators, panels)
- `simulation.py` — Live telemetry and fault injection simulation engine
- `modbus_server.py` — Virtual Modbus TCP slave running in background
- `theme.py` — Global style constants and UI theme helpers

## Keyboard Shortcuts

| Key  | Action             |
|------|--------------------|
| `F1` | Inject random fault |
| `F2` | Clear all faults   |
| `F3` | Toggle control mode (Remote SCADA / Local Manual) |
| `F5` | Reset simulation to initial values |
| `F10`| Toggle Modbus Monitor panel |

## Fault Injection via Modbus

The dashboard runs a Modbus TCP server on port **5020**. You can write directly to holding registers using any Modbus client (e.g., `mbpoll`):

```bash
# Set frequency to 48.80 Hz (register value = Hz × 100)
mbpoll localhost -p 5020 -r 40002 -t 4 -1 -- 4880

# Trip Feeder-1 (register value: 0=ACTIVE, 1=TRIPPED)
mbpoll localhost -p 5020 -r 40006 -t 4 -1 -- 1
```

## Modbus Register Map

| Register   | Field              | Encoding            |
|------------|--------------------|----------------------|
| **40001**  | Active Power       | MW × 10              |
| **40002**  | Grid Frequency     | Hz × 100             |
| **40003**  | Power Factor       | × 100                |
| **40004**  | Load Demand        | MW                   |
| **40005**  | Transformer Temp   | °C                   |
| **40006**  | Feeder-1 Status    | 0 = ACTIVE, 1 = TRIPPED |
| **40007**  | Feeder-2 Status    | 0 = ACTIVE, 1 = TRIPPED |
| **40008**  | Feeder-3 Status    | 0 = ACTIVE, 1 = TRIPPED |
| **40009**  | Feeder-4 Status    | 0 = ACTIVE, 1 = TRIPPED |
| **40010**  | Feeder-1 Load      | %                    |
| **40011**  | Feeder-2 Load      | %                    |
| **40012**  | Feeder-3 Load      | %                    |
| **40013**  | Feeder-4 Load      | %                    |

## Protocols

- **IEC 61850** — Simulated (protocol badge only)
- **Modbus TCP** — Live server on port 5020

## License

Educational / research use.
