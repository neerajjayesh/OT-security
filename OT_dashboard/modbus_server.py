import threading
import logging
from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext,
)
try:
    from pymodbus.device import ModbusDeviceIdentification
except ImportError:
    ModbusDeviceIdentification = None

# Suppress noisy pymodbus logs
logging.getLogger("pymodbus").setLevel(logging.WARNING)

# Register map (0-based internally; user-facing as 40001–40013)
# 0: Active Power  (MW × 10)
# 1: Frequency     (Hz × 100)
# 2: Power Factor  (× 100)
# 3: Load Demand   (MW)
# 4: Xfmr Temp     (°C)
# 5-8:  Feeder 1-4 status  (0=ACTIVE, 1=TRIPPED)
# 9-12: Feeder 1-4 load %
REG_COUNT = 13


class ModbusServerThread(threading.Thread):
    """Runs a Modbus TCP slave on localhost:5020 in a daemon thread."""

    def __init__(self):
        super().__init__(daemon=True)
        init_vals = [0] * REG_COUNT
        block = ModbusSequentialDataBlock(0, init_vals)
        self.store = ModbusSlaveContext(
            hr=block, ir=block, di=block, co=block, zero_mode=True,
        )
        self.context = ModbusServerContext(slaves=self.store, single=True)
        self._hr = block  # direct ref for fast read/write

    def write_registers(self, data: dict):
        """Called from main thread to push sim values into registers."""
        vals = [
            int(data["active_power"] * 10),
            int(data["frequency"] * 100),
            int(data["power_factor"] * 100),
            int(data["load_demand"]),
            int(data["xfmr_temp"]),
        ]
        for i in range(4):
            vals.append(1 if data["feeder_status"][i] == "TRIPPED" else 0)
        for i in range(4):
            vals.append(int(data["feeder_loads"][i]))
        self._hr.setValues(0, vals)

    def read_registers(self) -> list:
        """Read all 13 registers for the monitor display."""
        return self._hr.getValues(0, REG_COUNT)

    def run(self):
        kwargs = {"context": self.context, "address": ("0.0.0.0", 5020)}
        if ModbusDeviceIdentification is not None:
            identity = ModbusDeviceIdentification()
            identity.VendorName = "KSEB-OT-Sim"
            identity.ProductCode = "SCADA-SIM"
            identity.ProductName = "KSEB Modbus Simulator"
            kwargs["identity"] = identity
        StartTcpServer(**kwargs)
