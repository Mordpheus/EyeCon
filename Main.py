"""
EyeCon - Hauptanwendungsdatei

Diese Datei startet die Anwendung mit einem einfachen leeren Hauptfenster.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from app_layout import AppLayout


if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = QMainWindow()
    win.setWindowTitle("Layout Prototype")
    win.resize(1200, 800)
    win.setCentralWidget(AppLayout())
    win.show()

    sys.exit(app.exec())
