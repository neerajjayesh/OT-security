# What to do? — Interaction Guide

This dashboard currently acts as a **SCADA Master simulation** that pushes telemetry to an integrated **Modbus TCP slave/server**. 

Here are all the ways you can currently interact with the simulated environment:

## 1. GUI Controls and Keyboard Shortcuts

You can interact directly with the PyQt5 interface using the following buttons and hotkeys:

### **Faults & Simulation Control**
*   **`F1` (or click `⚠ FAULT INJECT`)**
    *   **Action**: Introduces a spontaneous failure. It randomly picks an event like a "Feeder Trip", "Transformer Overtemp", or "Frequency Dip". 
    *   **Effect**: You will see warning indicators pulse red/amber, the event log will capture the fault, and affected dials/bars will reflect the compromised values (e.g. if a feeder trips, its status turns red and load drops to 0%).
*   **`F2`**
    *   **Action**: Clear active faults.
    *   **Effect**: Aborts any active fault injections mid-way, returning the system to a normal active state immediately.
*   **`F5`** 
    *   **Action**: Reset Simulation.
    *   **Effect**: Completely restores the simulation engine variables (telemetry levels and odometers) back to their baseline initial values.

### **View & Mode Control**
*   **`F3` (or click the Mode button at top right)**
    *   **Action**: Toggles the operational mode (Remote SCADA vs. Local Manual).
    *   **Effect**: Changes the style of the button and drops a log entry. *(Right now this is just cosmetic and demonstrates event logging, but later stages could use this to lock out the Modbus interface).*
*   **`F10`**
    *   **Action**: Toggle the bottom right Modbus monitor panel on or off to inspect the raw hex/decimal values held in the Modbus memory block.

---

## 2. Modbus TCP Network Interaction (`mbpoll`)

The UI runs a real network server exposing a standard Modbus TCP interface on `localhost:5020`. You can use external clients to query it or write to it.

> Note: The simulation engine updates the Modbus registers every 1 second based on its internal state. Therefore, if you write a value via Modbus, the simulation engine will overwrite your manual entry on the next tick. The UI itself reads from the simulation engine, not the Modbus registers, except for the internal "Modbus Monitor" panel. 

You can use the open-source CLI tool **`mbpoll`** to interact with the registers:

### **Reading Registers**
You can pole (-1 for single poll) the holding registers (-t 4) to monitor the values externally. This is identical to how a real external HMI or PLC would monitor a substation.

*   Read the holding register for **Active Power** (Register offset 1):
    ```bash
    mbpoll localhost -p 5020 -r 1 -t 4 -1
    ```
*   Read all **13 available registers** at once:
    ```bash
    mbpoll localhost -p 5020 -r 1 -c 13 -t 4 -1
    ```

### **Writing Registers**
When you want to impersonate a Master and change values (e.g. for penetration testing or verifying server write access):

*   Write a frequency of 48.80Hz (value mapping `4880` because Hz × 100) to the Grid Frequency register:
    ```bash
    mbpoll localhost -p 5020 -r 2 -t 4 -1 4880
    ```
    *(The `--` flag used in previous examples helps command lines parse negative integers if you ever need to inject them, e.g., `mbpoll ... -- -4880`)*

*   Trip **Feeder-2** mechanically over Modbus (value `1` represents tripped):
    ```bash
    mbpoll localhost -p 5020 -r 7 -t 4 -1 1
    ```

### Register Map Reference
| Offset  | Description         | Decoding Rule      | Modbus Address Format |
|---------|---------------------|--------------------|-----------------------|
| `1`     | Active Power        | MW × 10            | `40001`              |
| `2`     | Grid Frequency      | Hz × 100           | `40002`              |
| `3`     | Power Factor        | PF × 100           | `40003`              |
| `4`     | Total Load Demand   | MW                 | `40004`              |
| `5`     | Transformer Temp    | °C                 | `40005`              |
| `6`     | Feeder 1 Status     | 0=Active, 1=Tripped| `40006`              |
| `7`     | Feeder 2 Status     | 0=Active, 1=Tripped| `40007`              |
| `8`     | Feeder 3 Status     | 0=Active, 1=Tripped| `40008`              |
| `9`     | Feeder 4 Status     | 0=Active, 1=Tripped| `40009`              |
| `10`    | Feeder 1 Load %     | percentage         | `40010`              |
| `11`    | Feeder 2 Load %     | percentage         | `40011`              |
| `12`    | Feeder 3 Load %     | percentage         | `40012`              |
| `13`    | Feeder 4 Load %     | percentage         | `40013`              |
