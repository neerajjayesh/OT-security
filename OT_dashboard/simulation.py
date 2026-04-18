import math
import random
from PyQt5.QtCore import QThread, pyqtSignal

class SimulationEngine(QThread):
    """
    Emits `tick` every ~1 s with a dict of updated telemetry values.
    All values do a bounded random-walk around their set-points.
    """

    tick = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

        # state
        self.active_power = 312.0
        self.frequency    = 50.00
        self.power_factor = 0.92
        self.load_demand  = 487.0
        self.xfmr_temp    = 67.0
        self.feeder_loads = [78.0, 65.0, 0.0, 88.0]
        self.feeder_status = ["ACTIVE", "ACTIVE", "TRIPPED", "ACTIVE"]
        self.feeder_breaker = ["CLOSED", "CLOSED", "OPEN", "CLOSED"]

        # fault overrides (cleared after a duration)
        self._fault_name = None
        self._fault_ticks = 0

    # ── random walk helper ──
    @staticmethod
    def _walk(val, step, lo, hi, center=None, pull=0.05):
        delta = random.uniform(-step, step)
        if center is not None:
            delta += (center - val) * pull  # mean-reversion
        return max(lo, min(hi, val + delta))

    # ── fault injection (called from main thread) ──
    def inject_fault(self, fault_type: str):
        self._fault_name = fault_type
        self._fault_ticks = 8  # lasts 8 seconds

    def clear_faults(self):
        """Immediately clear any active fault."""
        self._fault_name = None
        self._fault_ticks = 0
        self.feeder_status = ["ACTIVE", "ACTIVE", "TRIPPED", "ACTIVE"]
        self.feeder_breaker = ["CLOSED", "CLOSED", "OPEN", "CLOSED"]

    def reset(self):
        """Reset all values to initial set-points."""
        self.active_power = 312.0
        self.frequency    = 50.00
        self.power_factor = 0.92
        self.load_demand  = 487.0
        self.xfmr_temp    = 67.0
        self.feeder_loads = [78.0, 65.0, 0.0, 88.0]
        self.feeder_status = ["ACTIVE", "ACTIVE", "TRIPPED", "ACTIVE"]
        self.feeder_breaker = ["CLOSED", "CLOSED", "OPEN", "CLOSED"]
        self._fault_name = None
        self._fault_ticks = 0

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            # normal random-walk
            self.active_power = self._walk(self.active_power, 5, 200, 450, center=312)
            self.frequency    = self._walk(self.frequency, 0.10, 48.5, 51.5, center=50.00, pull=0.12)
            self.power_factor = self._walk(self.power_factor, 0.02, 0.80, 1.00, center=0.92)
            self.load_demand  = self._walk(self.load_demand, 10, 200, 900, center=487)
            self.xfmr_temp    = self._walk(self.xfmr_temp, 1.0, 40, 110, center=67, pull=0.06)

            xfmr_load = max(10, min(100, self.load_demand / 10.0))

            # feeder loads (independent walks; tripped feeder stays at 0)
            for i in range(4):
                if self.feeder_status[i] == "ACTIVE":
                    self.feeder_loads[i] = self._walk(
                        self.feeder_loads[i], 4, 30, 99,
                        center=[78, 65, 60, 88][i],
                    )
                else:
                    self.feeder_loads[i] = 0.0

            # ── apply active fault overrides ──
            if self._fault_ticks > 0:
                ft = self._fault_name
                if ft == "FEEDER2_TRIP":
                    self.feeder_status[1] = "TRIPPED"
                    self.feeder_breaker[1] = "OPEN"
                    self.feeder_loads[1] = 0.0
                elif ft == "XFMR_OVERTEMP":
                    self.xfmr_temp = max(self.xfmr_temp, random.uniform(96, 108))
                elif ft == "FREQ_DIP":
                    self.frequency = random.uniform(48.75, 48.90)
                elif ft == "RTU_OFFLINE":
                    pass  # UI-only; values still flow but indicator lights

                self._fault_ticks -= 1
                if self._fault_ticks == 0:
                    # auto-recover
                    if ft == "FEEDER2_TRIP":
                        self.feeder_status[1] = "ACTIVE"
                        self.feeder_breaker[1] = "CLOSED"
                    self._fault_name = None

            self.tick.emit({
                "active_power":   round(self.active_power, 1),
                "frequency":      round(self.frequency, 2),
                "power_factor":   round(self.power_factor, 2),
                "load_demand":    round(self.load_demand, 1),
                "xfmr_temp":      round(self.xfmr_temp, 1),
                "xfmr_load":      round(xfmr_load, 1),
                "feeder_loads":   [round(f, 1) for f in self.feeder_loads],
                "feeder_status":  list(self.feeder_status),
                "feeder_breaker": list(self.feeder_breaker),
                "fault_active":   self._fault_name if self._fault_ticks > 0 else None,
            })

            self.msleep(1000)
