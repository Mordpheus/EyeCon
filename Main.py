"""
EyeCon - Hauptanwendungsdatei

Diese Datei startet die Anwendung mit einem einfachen leeren Hauptfenster.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from app_layout import AppLayout


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # === Globales StyleSheet für alle QPushButtons ===
    # Einheitliches Design für alle Buttons im gesamten Projekt
    btn_style = """
    QPushButton {
        background-color: #e7ecf8;
        color: #1f2d4d;
        border: 1px solid #c4d1f2;
        border-radius: 6px;
        padding: 8px 12px;
    }
    QPushButton:hover {
        background-color: #d2ddf6;
    }
    QPushButton:pressed {
        background-color: #c0cff1;
    }
    """
    app.setStyleSheet(btn_style)

    # === Hauptfenster erstellen ===
    win = QMainWindow()
    win.setWindowTitle("Layout Prototype")
    win.resize(1200, 800)
    win.setCentralWidget(AppLayout())
    win.show()

    sys.exit(app.exec())
