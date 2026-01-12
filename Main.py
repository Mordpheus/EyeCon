"""
EyeCon - Main application file

Starts the application with a main window and layout.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from app_layout import AppLayout


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # === Global stylesheet for all QPushButtons ===
    # Unified design for all buttons throughout the project
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

    # === Create main window ===
    win = QMainWindow()
    win.setWindowTitle("Layout Prototype")
    win.resize(1200, 800)
    win.setCentralWidget(AppLayout())
    win.show()

    sys.exit(app.exec())
