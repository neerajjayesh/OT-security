import math
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt, QTimer, QDateTime, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QTextCursor

from theme import (
    INDICATOR_OFF, INDICATOR_WARN, INDICATOR_CRIT, BORDER_GREEN, TEXT_DIM_GREEN,
    ACCENT_RED, TEXT_GREEN, ACCENT_AMBER, BAR_BG, BAR_FILL, BAR_FILL_WARN,
    BAR_FILL_CRIT, ACCENT_CYAN, _frame_style
)
from modbus_server import ModbusServerThread

# ═══════════════════════════════════════════════════════════════════
#  Bottom-bar circular indicator  (with pulse animation)
# ═══════════════════════════════════════════════════════════════════
class IndicatorDot(QWidget):
    def __init__(self, label_text: str, parent=None):
        super().__init__(parent)
        self._state = 0        # 0=off  1=warn(amber)  2=crit(red)
        self._label_text = label_text
        self._blink_on = True  # toggles for pulse
        self.setFixedSize(72, 72)

        # pulse timer — shared across all dots via class-level start
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.start(500)

    def _on_pulse(self):
        if self._state > 0:
            self._blink_on = not self._blink_on
            self.update()

    def set_state(self, state: int):
        """0=off, 1=warn/amber, 2=critical/red"""
        self._state = state
        if state == 0:
            self._blink_on = True
        self.update()

    def set_on(self, on: bool):
        self.set_state(2 if on else 0)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        dot_radius = 14
        cx, cy = self.width() // 2, 22

        if self._state == 0:
            color = QColor(INDICATOR_OFF)
        elif self._blink_on:
            color = QColor(INDICATOR_WARN) if self._state == 1 else QColor(INDICATOR_CRIT)
        else:
            color = QColor(INDICATOR_OFF).lighter(140)

        p.setPen(QPen(QColor(BORDER_GREEN), 1.5))
        p.setBrush(QBrush(color))
        p.drawEllipse(cx - dot_radius, cy - dot_radius,
                       dot_radius * 2, dot_radius * 2)

        if self._state > 0 and self._blink_on:
            glow = QColor(color)
            glow.setAlpha(80)
            p.setPen(QPen(glow, 4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(cx - dot_radius - 4, cy - dot_radius - 4,
                           (dot_radius + 4) * 2, (dot_radius + 4) * 2)

        p.setPen(QColor(TEXT_DIM_GREEN))
        font = QFont("Consolas", 6)
        font.setBold(True)
        p.setFont(font)
        text_rect = self.rect().adjusted(0, 42, 0, 0)
        p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self._label_text)
        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Circular Dial Gauge  (now with set_value)
# ═══════════════════════════════════════════════════════════════════
class DialGauge(QWidget):
    def __init__(
        self, title: str, unit: str,
        min_val: float, max_val: float, value: float,
        red_lo: float = None, red_hi: float = None,
        size: int = 180, parent=None,
    ):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._min = min_val
        self._max = max_val
        self._value = value
        self._red_lo = red_lo
        self._red_hi = red_hi
        self.setFixedSize(size, size)

    def set_value(self, v: float):
        self._value = v
        self.update()

    def _val_to_angle(self, v: float) -> float:
        ratio = (v - self._min) / (self._max - self._min)
        ratio = max(0.0, min(1.0, ratio))
        return 210.0 - ratio * 240.0

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 12
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        pen_width = 8

        # bg arc
        p.setPen(QPen(QColor("#1a2e1a"), pen_width, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, int(-30 * 16), int(240 * 16))

        # red zones
        if self._red_lo is not None:
            a_start = self._val_to_angle(self._min)
            a_end = self._val_to_angle(self._red_lo)
            span = a_start - a_end
            p.setPen(QPen(QColor(ACCENT_RED).darker(140), pen_width, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc_rect, int(a_end * 16), int(span * 16))

        if self._red_hi is not None:
            a_start = self._val_to_angle(self._red_hi)
            a_end = self._val_to_angle(self._max)
            span = a_start - a_end
            p.setPen(QPen(QColor(ACCENT_RED).darker(140), pen_width, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(arc_rect, int(a_end * 16), int(span * 16))

        # active arc
        a_start_deg = 210.0
        a_end_deg = self._val_to_angle(self._value)
        sweep = a_start_deg - a_end_deg

        # color depends on whether in red zone
        in_red = False
        if self._red_lo is not None and self._value < self._red_lo:
            in_red = True
        if self._red_hi is not None and self._value > self._red_hi:
            in_red = True
        arc_color = QColor(ACCENT_RED) if in_red else QColor(TEXT_GREEN)

        p.setPen(QPen(arc_color, pen_width, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, int(a_end_deg * 16), int(sweep * 16))

        # needle
        needle_angle_rad = math.radians(a_end_deg)
        needle_len = radius - 16
        nx = cx + needle_len * math.cos(needle_angle_rad)
        ny = cy - needle_len * math.sin(needle_angle_rad)
        p.setPen(QPen(QColor(ACCENT_AMBER), 2))
        p.drawLine(QPointF(cx, cy), QPointF(nx, ny))

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(ACCENT_AMBER)))
        p.drawEllipse(QPointF(cx, cy), 5, 5)

        # value text
        p.setPen(arc_color)
        val_font = QFont("Consolas", 16, QFont.Bold)
        p.setFont(val_font)
        if self._max - self._min < 10:
            val_str = f"{self._value:.2f}"
        else:
            val_str = f"{self._value:.0f}"
        fm = QFontMetrics(val_font)
        tw = fm.horizontalAdvance(val_str)
        p.drawText(int(cx - tw / 2), int(cy + 24), val_str)

        # unit
        p.setPen(QColor(TEXT_DIM_GREEN))
        unit_font = QFont("Consolas", 8)
        p.setFont(unit_font)
        ufm = QFontMetrics(unit_font)
        uw = ufm.horizontalAdvance(self._unit)
        p.drawText(int(cx - uw / 2), int(cy + 40), self._unit)

        # title
        p.setPen(QColor(TEXT_DIM_GREEN))
        title_font = QFont("Consolas", 7, QFont.Bold)
        p.setFont(title_font)
        tfm = QFontMetrics(title_font)
        ttw = tfm.horizontalAdvance(self._title)
        p.drawText(int(cx - ttw / 2), int(h - 4), self._title)

        # min / max labels
        p.setFont(QFont("Consolas", 6))
        p.setPen(QColor(TEXT_DIM_GREEN))
        min_str = f"{self._min:.1f}" if self._min != int(self._min) else f"{self._min:.0f}"
        max_str = f"{self._max:.1f}" if self._max != int(self._max) else f"{self._max:.0f}"
        p.drawText(int(cx - radius + 2), int(cy + radius - 6), min_str)
        max_w = QFontMetrics(QFont("Consolas", 6)).horizontalAdvance(max_str)
        p.drawText(int(cx + radius - max_w - 2), int(cy + radius - 6), max_str)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Horizontal Bar Gauge (with set_value)
# ═══════════════════════════════════════════════════════════════════
class BarGauge(QWidget):
    def __init__(self, title, unit, min_val, max_val, value,
                 warn_pct=0.75, crit_pct=0.90, parent=None):
        super().__init__(parent)
        self._title = title
        self._unit = unit
        self._min = min_val
        self._max = max_val
        self._value = value
        self._warn = warn_pct
        self._crit = crit_pct
        self.setFixedHeight(48)
        self.setMinimumWidth(120)

    def set_value(self, v: float):
        self._value = v
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ml, mr = 8, 8
        bar_y, bar_h = 20, 16
        bar_w = w - ml - mr

        p.setPen(QColor(TEXT_DIM_GREEN))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        p.drawText(ml, 14, self._title)

        val_str = f"{self._value:.0f} {self._unit}"
        p.setPen(QColor(TEXT_GREEN))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        fm = QFontMetrics(p.font())
        vw = fm.horizontalAdvance(val_str)
        p.drawText(w - mr - vw, 14, val_str)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(BAR_BG))
        p.drawRoundedRect(ml, bar_y, bar_w, bar_h, 3, 3)

        ratio = (self._value - self._min) / (self._max - self._min)
        ratio = max(0.0, min(1.0, ratio))
        fill_w = int(bar_w * ratio)
        if ratio >= self._crit:
            fill_color = QColor(BAR_FILL_CRIT)
        elif ratio >= self._warn:
            fill_color = QColor(BAR_FILL_WARN)
        else:
            fill_color = QColor(BAR_FILL)
        p.setBrush(fill_color)
        p.drawRoundedRect(ml, bar_y, fill_w, bar_h, 3, 3)

        p.setPen(QPen(QColor(BORDER_GREEN), 1))
        for pct in (0.25, 0.5, 0.75):
            tx = ml + int(bar_w * pct)
            p.drawLine(tx, bar_y, tx, bar_y + bar_h)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Semicircular Temperature Gauge (with set_value)
# ═══════════════════════════════════════════════════════════════════
class TempGauge(QWidget):
    def __init__(self, title, min_val, max_val, value,
                 red_above=90, size=150, parent=None):
        super().__init__(parent)
        self._title = title
        self._min = min_val
        self._max = max_val
        self._value = value
        self._red = red_above
        self.setFixedSize(size, int(size * 0.72))

    def set_value(self, v: float):
        self._value = v
        self.update()

    def _pct(self, v):
        return (v - self._min) / (self._max - self._min)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h - 10
        radius = min(w / 2, h) - 14
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        pen_w = 8

        p.setPen(QPen(QColor("#1a2e1a"), pen_w, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, 0, 180 * 16)

        red_pct = self._pct(self._red)
        red_span_deg = (1.0 - red_pct) * 180.0
        p.setPen(QPen(QColor(ACCENT_RED).darker(150), pen_w, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, 0, int(red_span_deg * 16))

        val_pct = self._pct(self._value)
        val_deg = val_pct * 180.0
        in_red = self._value >= self._red
        fill_col = QColor(ACCENT_RED) if in_red else QColor(TEXT_GREEN)
        p.setPen(QPen(fill_col, pen_w, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(arc_rect, int((180.0 - val_deg) * 16), int(val_deg * 16))

        p.setPen(fill_col)
        p.setFont(QFont("Consolas", 14, QFont.Bold))
        val_str = f"{self._value:.0f}°C"
        fm = QFontMetrics(p.font())
        tw = fm.horizontalAdvance(val_str)
        p.drawText(int(cx - tw / 2), int(cy - 8), val_str)

        p.setPen(QColor(TEXT_DIM_GREEN))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        tfm = QFontMetrics(p.font())
        ttw = tfm.horizontalAdvance(self._title)
        p.drawText(int(cx - ttw / 2), int(cy + 8), self._title)
        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Large Digital Readout (with set_value)
# ═══════════════════════════════════════════════════════════════════
class DigitalReadout(QWidget):
    def __init__(self, value, label, unit="",
                 color=TEXT_GREEN, size_pt=36, parent=None):
        super().__init__(parent)
        self._value = value
        self._label = label
        self._unit = unit
        self._color = color
        self._size_pt = size_pt
        self.setFixedHeight(90)

    def set_value(self, v: str):
        self._value = v
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2

        box_rect = QRectF(8, 4, w - 16, h - 8)
        p.setPen(QPen(QColor(BORDER_GREEN), 1))
        p.setBrush(QColor("#0a140a"))
        p.drawRoundedRect(box_rect, 6, 6)

        p.setPen(QColor(TEXT_DIM_GREEN))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(box_rect.adjusted(10, 6, 0, 0), Qt.AlignLeft | Qt.AlignTop, self._label)

        p.setPen(QColor(self._color))
        val_font = QFont("Consolas", self._size_pt, QFont.Bold)
        p.setFont(val_font)
        fm = QFontMetrics(val_font)
        vw = fm.horizontalAdvance(self._value)
        p.drawText(int(cx - vw / 2), int(h / 2 + self._size_pt / 2 + 2), self._value)

        if self._unit:
            p.setPen(QColor(TEXT_DIM_GREEN))
            p.setFont(QFont("Consolas", 10))
            p.drawText(int(cx + vw / 2 + 6), int(h / 2 + self._size_pt / 2 + 2), self._unit)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Odometer Display (with set_value)
# ═══════════════════════════════════════════════════════════════════
class OdometerDisplay(QWidget):
    def __init__(self, label, value, parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        self.setFixedHeight(56)

    def set_value(self, v: str):
        self._value = v
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(QColor(TEXT_DIM_GREEN))
        p.setFont(QFont("Consolas", 7, QFont.Bold))
        p.drawText(12, 14, self._label)

        display_str = self._value
        char_w, char_h = 18, 26
        total_w = len(display_str) * char_w
        start_x = (w - total_w) // 2
        y = 22

        for i, ch in enumerate(display_str):
            if ch == ",":
                p.setPen(QColor(TEXT_DIM_GREEN))
                p.setFont(QFont("Consolas", 12))
                p.drawText(start_x + i * char_w + 4, y + 20, ",")
            else:
                x = start_x + i * char_w
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#0a0f0a"))
                p.drawRoundedRect(x + 1, y, char_w - 2, char_h, 2, 2)
                p.setPen(QPen(QColor(BORDER_GREEN), 0.5))
                p.drawRoundedRect(x + 1, y, char_w - 2, char_h, 2, 2)
                p.setPen(QColor(TEXT_GREEN))
                p.setFont(QFont("Consolas", 14, QFont.Bold))
                fm = QFontMetrics(p.font())
                cw = fm.horizontalAdvance(ch)
                p.drawText(int(x + (char_w - cw) / 2), y + 20, ch)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  Feeder Status Row (now fully updatable)
# ═══════════════════════════════════════════════════════════════════
class FeederRow(QFrame):
    def __init__(self, name, status, load_pct, breaker, parent=None):
        super().__init__(parent)
        self._name = name
        self.setFixedHeight(38)
        self.setStyleSheet(
            f"background-color: #0a140a; border: 1px solid {BORDER_GREEN}; border-radius: 3px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        self._name_lbl = QLabel(name)
        self._name_lbl.setFont(QFont("Consolas", 9, QFont.Bold))
        self._name_lbl.setFixedWidth(80)
        layout.addWidget(self._name_lbl)

        self._status_lbl = QLabel()
        self._status_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setFixedWidth(72)
        layout.addWidget(self._status_lbl)

        self._load_lbl = QLabel()
        self._load_lbl.setFont(QFont("Consolas", 9))
        self._load_lbl.setAlignment(Qt.AlignCenter)
        self._load_lbl.setFixedWidth(40)
        layout.addWidget(self._load_lbl)

        self._brk_lbl = QLabel()
        self._brk_lbl.setFont(QFont("Consolas", 7, QFont.Bold))
        self._brk_lbl.setAlignment(Qt.AlignCenter)
        self._brk_lbl.setFixedWidth(62)
        layout.addWidget(self._brk_lbl)

        self.update_data(status, load_pct, breaker)

    def update_data(self, status: str, load_pct: float, breaker: str):
        is_active = status == "ACTIVE"
        self._status_lbl.setText(f" {status} ")
        if is_active:
            self._status_lbl.setStyleSheet(
                f"color: {TEXT_GREEN}; background-color: #0f2b0f;"
                f"border: 1px solid {TEXT_DIM_GREEN}; border-radius: 2px;"
            )
        else:
            self._status_lbl.setStyleSheet(
                f"color: {ACCENT_RED}; background-color: #2b0f0f;"
                "border: 1px solid #5c1a1a; border-radius: 2px;"
            )

        load_int = int(round(load_pct))
        self._load_lbl.setText(f"{load_int}%")
        if load_int > 85:
            self._load_lbl.setStyleSheet(f"color: {ACCENT_RED}; border: none;")
        elif load_int > 70:
            self._load_lbl.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        else:
            self._load_lbl.setStyleSheet(f"color: {TEXT_GREEN}; border: none;")

        brk_closed = breaker == "CLOSED"
        self._brk_lbl.setText(f" {breaker} ")
        if brk_closed:
            self._brk_lbl.setStyleSheet(
                f"color: {TEXT_GREEN}; background-color: #0f2b0f;"
                "border: 1px solid #1a5c1a; border-radius: 2px;"
            )
        else:
            self._brk_lbl.setStyleSheet(
                f"color: {ACCENT_RED}; background-color: #2b0f0f;"
                "border: 1px solid #5c1a1a; border-radius: 2px;"
            )


# ═══════════════════════════════════════════════════════════════════
#  Event Log Widget (bottom-left)
# ═══════════════════════════════════════════════════════════════════
class EventLog(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_frame_style("#0a100a", BORDER_GREEN))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        hdr = QLabel("  EVENT LOG")
        hdr.setFont(QFont("Consolas", 8, QFont.Bold))
        hdr.setStyleSheet(f"color: {ACCENT_AMBER}; border: none;")
        layout.addWidget(hdr)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 7))
        self._text.setStyleSheet(
            f"background-color: #060a06; color: {TEXT_GREEN};"
            f"border: 1px solid {BORDER_GREEN}; border-radius: 3px;"
        )
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._text)

    def add_event(self, msg: str, level: str = "INFO"):
        ts = QDateTime.currentDateTime().toString("HH:mm:ss")
        color = {
            "INFO": TEXT_DIM_GREEN,
            "WARN": ACCENT_AMBER,
            "FAULT": ACCENT_RED,
        }.get(level, TEXT_GREEN)
        html = f'<span style="color:{TEXT_DIM_GREEN}">{ts}</span> '\
               f'<span style="color:{color}">▸ [{level}]</span> '\
               f'<span style="color:{TEXT_GREEN}">{msg}</span><br>'
        self._text.moveCursor(QTextCursor.End)
        self._text.insertHtml(html)
        self._text.moveCursor(QTextCursor.End)


# ═══════════════════════════════════════════════════════════════════
#  Modbus Monitor Widget (bottom-right)
# ═══════════════════════════════════════════════════════════════════
REG_NAMES = [
    ("Active Power",  lambda v: f"{v/10:.1f} MW"),
    ("Frequency",     lambda v: f"{v/100:.2f} Hz"),
    ("Power Factor",  lambda v: f"{v/100:.2f}"),
    ("Load Demand",   lambda v: f"{v} MW"),
    ("Xfmr Temp",     lambda v: f"{v} °C"),
    ("Fdr-1 Status",  lambda v: "TRIPPED" if v else "ACTIVE"),
    ("Fdr-2 Status",  lambda v: "TRIPPED" if v else "ACTIVE"),
    ("Fdr-3 Status",  lambda v: "TRIPPED" if v else "ACTIVE"),
    ("Fdr-4 Status",  lambda v: "TRIPPED" if v else "ACTIVE"),
    ("Fdr-1 Load",    lambda v: f"{v}%"),
    ("Fdr-2 Load",    lambda v: f"{v}%"),
    ("Fdr-3 Load",    lambda v: f"{v}%"),
    ("Fdr-4 Load",    lambda v: f"{v}%"),
]


class ModbusMonitor(QFrame):
    def __init__(self, modbus_server: ModbusServerThread, parent=None):
        super().__init__(parent)
        self._server = modbus_server
        self.setStyleSheet(_frame_style("#0a100a", BORDER_GREEN))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        hdr = QLabel("  MODBUS MONITOR  :5020")
        hdr.setFont(QFont("Consolas", 8, QFont.Bold))
        hdr.setStyleSheet(f"color: {ACCENT_CYAN}; border: none;")
        layout.addWidget(hdr)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 7))
        self._text.setStyleSheet(
            f"background-color: #060a06; color: {TEXT_GREEN};"
            f"border: 1px solid {BORDER_GREEN}; border-radius: 3px;"
        )
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._text)

        # refresh every 2 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)

    def _refresh(self):
        try:
            regs = self._server.read_registers()
        except Exception:
            return
        lines = []
        for i, val in enumerate(regs):
            name, fmt = REG_NAMES[i]
            lines.append(
                f'<span style="color:{TEXT_DIM_GREEN}">Reg {40001+i}</span>'
                f' → <span style="color:{TEXT_GREEN}">{val:>5}</span>'
                f'  <span style="color:{TEXT_DIM_GREEN}">({fmt(val)})</span>'
            )
        self._text.setHtml(
            f'<pre style="color:{TEXT_GREEN}; font-size:7pt">' +
            "<br>".join(lines) + "</pre>"
        )
