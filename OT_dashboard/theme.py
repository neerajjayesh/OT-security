import sys
from PyQt5.QtWidgets import QLabel, QFrame
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# ── colour palette ──────────────────────────────────────────────────
BG_BLACK      = "#0a0a0a"
PANEL_BG      = "#0d1a0d"
BORDER_GREEN  = "#1a3a1a"
TEXT_GREEN     = "#33ff33"
TEXT_DIM_GREEN = "#1a8c1a"
ACCENT_AMBER  = "#ffbf00"
ACCENT_RED    = "#ff3333"
ACCENT_CYAN   = "#00e5ff"
HEADER_BG     = "#0f1e0f"
BTN_ACTIVE    = "#00cc44"
BTN_INACTIVE  = "#555555"
INDICATOR_OFF = "#1a1a1a"
INDICATOR_ON  = "#33ff33"
INDICATOR_WARN = "#ffbf00"
INDICATOR_CRIT = "#ff3333"
GAUGE_BG      = "#111a11"
BAR_BG        = "#0a150a"
BAR_FILL      = "#1aaa1a"
BAR_FILL_WARN = "#ff6600"
BAR_FILL_CRIT = "#ff2222"

GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG_BLACK};
    color: {TEXT_GREEN};
}}
QLabel {{
    color: {TEXT_GREEN};
    border: none;
}}
"""


def _frame_style(bg: str = PANEL_BG, border: str = BORDER_GREEN) -> str:
    return (
        f"background-color: {bg};"
        f"border: 1px solid {border};"
        "border-radius: 4px;"
    )


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Consolas", 8))
    lbl.setStyleSheet(f"color: {TEXT_DIM_GREEN}; border: none;")
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


def _h_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background-color: {BORDER_GREEN}; border: none;")
    return sep
