import random
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont

from theme import (
    GLOBAL_STYLE, _frame_style, _section_label, _h_separator,
    HEADER_BG, BORDER_GREEN, ACCENT_AMBER, TEXT_GREEN, TEXT_DIM_GREEN,
    ACCENT_CYAN, BTN_ACTIVE, ACCENT_RED
)
from modbus_server import ModbusServerThread
from simulation import SimulationEngine
from components import (
    IndicatorDot, DialGauge, BarGauge, TempGauge, DigitalReadout,
    OdometerDisplay, FeederRow, EventLog, ModbusMonitor
)

# ═══════════════════════════════════════════════════════════════════
#  Main Dashboard Window
# ═══════════════════════════════════════════════════════════════════
class KSEBDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "KSEB SCADA \u2013 OT Environment Simulator | IEC 61850 / Modbus TCP"
        )
        self.setMinimumSize(1400, 800)
        self.resize(1400, 800)
        self.setStyleSheet(GLOBAL_STYLE)

        self._remote_mode = True
        self._energy_kwh = 14283451  # running odometer

        # ── Start Modbus TCP server ──
        self._modbus = ModbusServerThread()
        self._modbus.start()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_top_bar())

        panels = QHBoxLayout()
        panels.setSpacing(6)
        panels.addWidget(self._build_left_panel(), stretch=1)
        panels.addWidget(self._build_center_panel(), stretch=2)
        panels.addWidget(self._build_right_panel(), stretch=1)
        root.addLayout(panels, stretch=1)

        # bottom area: event log + indicators + modbus monitor
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self._event_log = EventLog()
        self._event_log.setFixedHeight(120)
        self._event_log.setFixedWidth(340)
        bottom.addWidget(self._event_log)
        bottom.addWidget(self._build_bottom_bar(), stretch=1)
        self._modbus_monitor = ModbusMonitor(self._modbus)
        self._modbus_monitor.setFixedHeight(120)
        self._modbus_monitor.setFixedWidth(340)
        bottom.addWidget(self._modbus_monitor)
        root.addLayout(bottom)

        # keyboard shortcut panel
        shortcut_bar = QFrame()
        shortcut_bar.setFixedHeight(24)
        shortcut_bar.setStyleSheet(
            f"background-color: #060a06; border: 1px solid {BORDER_GREEN}; border-radius: 2px;"
        )
        sc_layout = QHBoxLayout(shortcut_bar)
        sc_layout.setContentsMargins(10, 0, 10, 0)
        sc_layout.setSpacing(0)
        shortcuts = [
            ("F1", "Inject Fault"), ("F2", "Clear Faults"),
            ("F3", "Toggle Mode"), ("F5", "Reset Sim"),
            ("F10", "Modbus Mon"),
        ]
        for key, desc in shortcuts:
            lbl = QLabel(f"  {key} ")
            lbl.setFont(QFont("Consolas", 7, QFont.Bold))
            lbl.setStyleSheet(
                f"color: {ACCENT_AMBER}; background-color: #1a1a0a;"
                "border: 1px solid #3a3a1a; border-radius: 2px; padding: 0 3px;"
            )
            sc_layout.addWidget(lbl)
            dl = QLabel(f" {desc}  │")
            dl.setFont(QFont("Consolas", 7))
            dl.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
            sc_layout.addWidget(dl)
        # modbus hint at end
        mb_hint = QLabel(
            "  💡 Modbus: mbpoll localhost -p 5020 -r 40002 -t 4 -1 -- 4880"
        )
        mb_hint.setFont(QFont("Consolas", 7))
        mb_hint.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
        sc_layout.addStretch()
        sc_layout.addWidget(mb_hint)
        root.addWidget(shortcut_bar)

        # clock timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        # start simulation
        self._sim = SimulationEngine()
        self._sim.tick.connect(self._on_sim_tick)
        self._sim.start()

        # log startup
        self._event_log.add_event("Dashboard initialised — simulation ONLINE", "INFO")
        self._event_log.add_event("Modbus TCP server on localhost:5020", "INFO")

    def closeEvent(self, event):
        self._sim.stop()
        self._sim.wait(2000)
        super().closeEvent(event)

    # ── KEYBOARD SHORTCUTS ──────────────────────────────────────────
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F1:
            self._inject_fault()
        elif key == Qt.Key_F2:
            self._clear_all_faults()
        elif key == Qt.Key_F3:
            self._toggle_mode()
        elif key == Qt.Key_F5:
            self._reset_simulation()
        elif key == Qt.Key_F10:
            vis = self._modbus_monitor.isVisible()
            self._modbus_monitor.setVisible(not vis)
        else:
            super().keyPressEvent(event)

    def _clear_all_faults(self):
        self._sim.clear_faults()
        for ind in self._indicators:
            ind.set_state(0)
        self._event_log.add_event("All faults CLEARED manually", "WARN")

    def _reset_simulation(self):
        self._sim.reset()
        self._energy_kwh = 14283451
        self._event_log.add_event("Simulation RESET to initial values", "WARN")

    # ── TOP STATUS BAR ──────────────────────────────────────────────
    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(_frame_style(HEADER_BG, BORDER_GREEN))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 4, 14, 4)

        ss_label = QLabel("⚡  33/11 kV SUBSTATION")
        ss_label.setFont(QFont("Consolas", 13, QFont.Bold))
        ss_label.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        layout.addWidget(ss_label)

        layout.addStretch()

        self._clock_label = QLabel()
        self._clock_label.setFont(QFont("Consolas", 12))
        self._clock_label.setStyleSheet(f"color: {TEXT_GREEN}; border: none;")
        layout.addWidget(self._clock_label)

        layout.addSpacing(12)

        # ── Alerts counter badge ──
        self._alert_badge = QLabel("  ⚠ 0 FAULTS  ")
        self._alert_badge.setFont(QFont("Consolas", 9, QFont.Bold))
        self._alert_badge.setAlignment(Qt.AlignCenter)
        self._alert_badge.setFixedWidth(150)
        self._alert_badge.setStyleSheet(
            f"color: {TEXT_DIM_GREEN}; background-color: #0f1a0f;"
            f"border: 1px solid {BORDER_GREEN}; border-radius: 3px; padding: 2px 6px;"
        )
        layout.addWidget(self._alert_badge)

        layout.addSpacing(12)

        proto = QLabel("  IEC 61850  ")
        proto.setFont(QFont("Consolas", 10, QFont.Bold))
        proto.setStyleSheet(
            f"color: {TEXT_GREEN}; background-color: #0f2b0f;"
            "border: 1px solid #1a5c1a; border-radius: 3px; padding: 2px 8px;"
        )
        layout.addWidget(proto)

        layout.addSpacing(12)

        # ── FAULT INJECT button ──
        fault_btn = QPushButton("⚠  FAULT INJECT")
        fault_btn.setFont(QFont("Consolas", 9, QFont.Bold))
        fault_btn.setCursor(Qt.PointingHandCursor)
        fault_btn.setFixedWidth(150)
        fault_btn.setStyleSheet(
            f"QPushButton {{ background-color: #3f0a0a; color: {ACCENT_RED};"
            "border: 1px solid #6b1a1a; border-radius: 3px; padding: 4px; }"
            "QPushButton:hover { background-color: #5a1010; }"
            "QPushButton:pressed { background-color: #7a2020; }"
        )
        fault_btn.clicked.connect(self._inject_fault)
        layout.addWidget(fault_btn)

        layout.addSpacing(12)

        self._mode_btn = QPushButton()
        self._mode_btn.setFont(QFont("Consolas", 10, QFont.Bold))
        self._mode_btn.setCursor(Qt.PointingHandCursor)
        self._mode_btn.setFixedWidth(180)
        self._mode_btn.clicked.connect(self._toggle_mode)
        self._apply_mode_style()
        layout.addWidget(self._mode_btn)

        return bar

    def _apply_mode_style(self):
        if self._remote_mode:
            self._mode_btn.setText("⏼  REMOTE SCADA")
            self._mode_btn.setStyleSheet(
                f"QPushButton {{ background-color: #0f3f0f; color: {BTN_ACTIVE};"
                "border: 1px solid #1a6b1a; border-radius: 3px; padding: 4px; }"
                "QPushButton:hover { background-color: #165a16; }"
            )
        else:
            self._mode_btn.setText("⏻  LOCAL MANUAL")
            self._mode_btn.setStyleSheet(
                f"QPushButton {{ background-color: #3f1a0a; color: {ACCENT_AMBER};"
                "border: 1px solid #6b3a1a; border-radius: 3px; padding: 4px; }"
                "QPushButton:hover { background-color: #5a2a10; }"
            )

    def _toggle_mode(self):
        self._remote_mode = not self._remote_mode
        self._apply_mode_style()
        mode_text = "REMOTE SCADA" if self._remote_mode else "LOCAL MANUAL"
        self._event_log.add_event(f"Control mode → {mode_text}", "WARN")

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        self._clock_label.setText(now.toString("dd-MMM-yyyy  HH:mm:ss"))

    # ── FAULT INJECTION ─────────────────────────────────────────────
    def _inject_fault(self):
        faults = [
            ("FEEDER2_TRIP",  "Feeder-2 TRIPPED — overcurrent detected"),
            ("XFMR_OVERTEMP", "Transformer OIL TEMP critically high"),
            ("FREQ_DIP",      "Grid frequency DIP — under-frequency event"),
            ("RTU_OFFLINE",   "RTU communication LOST — link timeout"),
        ]
        fault_type, msg = random.choice(faults)
        self._sim.inject_fault(fault_type)
        self._event_log.add_event(msg, "FAULT")

    # ── LEFT PANEL — Generation ─────────────────────────────────────
    def _build_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("── GENERATION ──")
        title.setFont(QFont("Consolas", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        layout.addWidget(title)
        layout.addWidget(_h_separator())

        layout.addWidget(_section_label("ACTIVE POWER"))
        self._power_gauge = DialGauge("ACTIVE POWER", "MW", 0, 500, 312, size=180)
        layout.addWidget(self._power_gauge, alignment=Qt.AlignCenter)

        layout.addSpacing(4)
        layout.addWidget(_h_separator())

        layout.addWidget(_section_label("GRID FREQUENCY"))
        self._freq_gauge = DialGauge("FREQUENCY", "Hz", 48.5, 51.5, 49.97,
                                      red_lo=49.5, red_hi=50.5, size=180)
        layout.addWidget(self._freq_gauge, alignment=Qt.AlignCenter)

        layout.addSpacing(4)
        layout.addWidget(_h_separator())

        # Power Factor
        pf_box = QFrame()
        pf_box.setStyleSheet("background-color: #0a140a; border: 1px solid #1a3a1a; border-radius: 4px;")
        pf_layout = QVBoxLayout(pf_box)
        pf_layout.setContentsMargins(8, 6, 8, 6)
        pf_lbl = QLabel("POWER FACTOR")
        pf_lbl.setFont(QFont("Consolas", 7, QFont.Bold))
        pf_lbl.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
        pf_lbl.setAlignment(Qt.AlignCenter)
        pf_layout.addWidget(pf_lbl)
        self._pf_val = QLabel("0.92")
        self._pf_val.setFont(QFont("Consolas", 22, QFont.Bold))
        self._pf_val.setStyleSheet(f"color: {TEXT_GREEN}; border: none;")
        self._pf_val.setAlignment(Qt.AlignCenter)
        pf_layout.addWidget(self._pf_val)
        layout.addWidget(pf_box)

        layout.addSpacing(4)

        # Source
        src_box = QFrame()
        src_box.setStyleSheet("background-color: #0a1418; border: 1px solid #1a3a4a; border-radius: 4px;")
        src_layout = QHBoxLayout(src_box)
        src_layout.setContentsMargins(8, 6, 8, 6)
        src_lbl = QLabel("SOURCE")
        src_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
        src_lbl.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
        src_layout.addWidget(src_lbl)
        src_layout.addStretch()
        src_val = QLabel("◆  HYDRO")
        src_val.setFont(QFont("Consolas", 12, QFont.Bold))
        src_val.setStyleSheet(f"color: {ACCENT_CYAN}; border: none;")
        src_layout.addWidget(src_val)
        layout.addWidget(src_box)

        layout.addStretch()
        return frame

    # ── CENTER PANEL — System Health ────────────────────────────────
    def _build_center_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("── SYSTEM HEALTH ──")
        title.setFont(QFont("Consolas", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        layout.addWidget(title)
        layout.addWidget(_h_separator())

        self._freq_readout = DigitalReadout("49.97", "GRID FREQUENCY", "Hz",
                                             TEXT_GREEN, 42)
        layout.addWidget(self._freq_readout)

        layout.addSpacing(6)

        self._volt_readout = DigitalReadout("110", "SYSTEM VOLTAGE", "kV",
                                             ACCENT_AMBER, 38)
        layout.addWidget(self._volt_readout)

        layout.addSpacing(6)
        layout.addWidget(_h_separator())

        self._load_bar = BarGauge("TOTAL LOAD DEMAND", "MW", 0, 1000, 487)
        layout.addWidget(self._load_bar)

        layout.addSpacing(10)
        layout.addWidget(_h_separator())
        layout.addSpacing(4)

        self._energy_odo = OdometerDisplay("ENERGY METER (kWh)", "1,42,83,451")
        layout.addWidget(self._energy_odo)

        layout.addSpacing(4)

        self._trip_odo = OdometerDisplay("TRIP TODAY (kWh)", "18,432")
        layout.addWidget(self._trip_odo)

        layout.addStretch()
        return frame

    # ── RIGHT PANEL — Feeder / Distribution ─────────────────────────
    def _build_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(_frame_style())
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("── FEEDER / DISTRIBUTION ──")
        title.setFont(QFont("Consolas", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        layout.addWidget(title)
        layout.addWidget(_h_separator())

        hdr = QFrame()
        hdr.setStyleSheet("border: none;")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(8, 0, 8, 0)
        hdr_layout.setSpacing(6)
        for text, width in [("FEEDER", 80), ("STATUS", 72), ("LOAD", 40), ("BKR", 62)]:
            l = QLabel(text)
            l.setFont(QFont("Consolas", 7, QFont.Bold))
            l.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
            l.setFixedWidth(width)
            l.setAlignment(Qt.AlignCenter)
            hdr_layout.addWidget(l)
        layout.addWidget(hdr)

        feeders_init = [
            ("Feeder-1", "ACTIVE", 78, "CLOSED"),
            ("Feeder-2", "ACTIVE", 65, "CLOSED"),
            ("Feeder-3", "TRIPPED", 0, "OPEN"),
            ("Feeder-4", "ACTIVE", 88, "CLOSED"),
        ]
        self._feeder_rows: list[FeederRow] = []
        for name, status, load, brk in feeders_init:
            row = FeederRow(name, status, load, brk)
            self._feeder_rows.append(row)
            layout.addWidget(row)

        layout.addSpacing(8)
        layout.addWidget(_h_separator())
        layout.addSpacing(4)

        layout.addWidget(_section_label("TRANSFORMER TEMP"))
        self._temp_gauge = TempGauge("OIL TEMP", 0, 120, 67, red_above=90, size=180)
        layout.addWidget(self._temp_gauge, alignment=Qt.AlignCenter)

        layout.addSpacing(6)

        self._xfmr_bar = BarGauge("TRANSFORMER LOAD", "%", 0, 100, 71)
        layout.addWidget(self._xfmr_bar)

        layout.addStretch()
        return frame

    # ── BOTTOM WARNING INDICATOR BAR ────────────────────────────────
    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(110)
        bar.setStyleSheet(_frame_style(HEADER_BG, BORDER_GREEN))

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)

        indicator_labels = [
            "EARTH\nFAULT", "OVER\nCURRENT", "OVER\nLOAD",
            "RTU\nOFFLINE", "TAMPER", "LOW\nBATT",
            "REVERSE\nPOWER", "ISLAND\nING", "CYBER\nALERT",
        ]

        self._indicators: list[IndicatorDot] = []
        layout.addStretch()
        for text in indicator_labels:
            dot = IndicatorDot(text)
            self._indicators.append(dot)
            layout.addWidget(dot)
            layout.addSpacing(12)
        layout.addStretch()

        return bar

    # ── SIMULATION TICK HANDLER ─────────────────────────────────────
    def _on_sim_tick(self, data: dict):
        # LEFT PANEL
        self._power_gauge.set_value(data["active_power"])
        self._freq_gauge.set_value(data["frequency"])
        self._pf_val.setText(f"{data['power_factor']:.2f}")

        # recolor PF if low
        pf = data["power_factor"]
        if pf < 0.85:
            self._pf_val.setStyleSheet(f"color: {ACCENT_RED}; border: none;")
        elif pf < 0.90:
            self._pf_val.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        else:
            self._pf_val.setStyleSheet(f"color: {TEXT_GREEN}; border: none;")

        # CENTER PANEL
        self._freq_readout.set_value(f"{data['frequency']:.2f}")
        self._load_bar.set_value(data["load_demand"])

        # increment energy odometer
        self._energy_kwh += int(data["load_demand"] / 3600 * 1000)
        s = str(self._energy_kwh)
        # Indian comma format: last 3, then groups of 2
        if len(s) > 3:
            tail = s[-3:]
            head = s[:-3]
            parts = []
            while head:
                parts.append(head[-2:])
                head = head[:-2]
            parts.reverse()
            formatted = ",".join(parts) + "," + tail
        else:
            formatted = s
        self._energy_odo.set_value(formatted)

        # trip meter (proportional daily slice)
        trip_val = 18432 + (self._energy_kwh - 14283451) // 100
        t_s = str(max(0, trip_val))
        if len(t_s) > 3:
            t_formatted = t_s[:-3] + "," + t_s[-3:]
        else:
            t_formatted = t_s
        self._trip_odo.set_value(t_formatted)

        # RIGHT PANEL — feeders
        for i, row in enumerate(self._feeder_rows):
            row.update_data(
                data["feeder_status"][i],
                data["feeder_loads"][i],
                data["feeder_breaker"][i],
            )

        self._temp_gauge.set_value(data["xfmr_temp"])
        self._xfmr_bar.set_value(data["xfmr_load"])

        # ── Push values to Modbus registers ──
        try:
            self._modbus.write_registers(data)
        except Exception:
            pass

        # ── Update warning indicators ──
        fault = data.get("fault_active")

        # reset all
        for ind in self._indicators:
            ind.set_state(0)

        # EARTH FAULT [0] — not currently triggered by sim
        # OVERCURRENT [1] — feeder trip
        if any(s == "TRIPPED" for s in data["feeder_status"]):
            self._indicators[1].set_state(2)  # red

        # OVERLOAD [2] — transformer overtemp
        if data["xfmr_temp"] >= 90:
            self._indicators[2].set_state(2)
        elif data["xfmr_temp"] >= 80:
            self._indicators[2].set_state(1)  # amber warning

        # RTU OFFLINE [3]
        if fault == "RTU_OFFLINE":
            self._indicators[3].set_state(2)

        # TAMPER [4] — not triggered
        # LOW BATT [5] — not triggered

        # REVERSE POWER [6] — if load_demand very low
        if data["load_demand"] < 250:
            self._indicators[6].set_state(1)

        # ISLANDING [7] — frequency out of range
        freq = data["frequency"]
        if freq < 49.0 or freq > 51.0:
            self._indicators[7].set_state(2)
        elif freq < 49.5 or freq > 50.5:
            self._indicators[7].set_state(1)

        # CYBER ALERT [8] — not triggered by sim

        # ── Update alert badge ──
        active_count = sum(1 for ind in self._indicators if ind._state > 0)
        if active_count > 0:
            self._alert_badge.setText(f"  ⚠ {active_count} ACTIVE FAULT{'S' if active_count > 1 else ''}  ")
            self._alert_badge.setStyleSheet(
                f"color: {ACCENT_AMBER}; background-color: #2b1a00;"
                f"border: 1px solid #6b4a00; border-radius: 3px; padding: 2px 6px;"
            )
        else:
            self._alert_badge.setText("  ⚠ 0 FAULTS  ")
            self._alert_badge.setStyleSheet(
                f"color: {TEXT_DIM_GREEN}; background-color: #0f1a0f;"
                f"border: 1px solid {BORDER_GREEN}; border-radius: 3px; padding: 2px 6px;"
            )
