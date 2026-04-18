import sys
from PyQt5.QtWidgets import QApplication
from dashboard import KSEBDashboard

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = KSEBDashboard()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
