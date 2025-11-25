"""
EyeCon - Hauptanwendungsdatei

Diese Datei startet die Anwendung mit einem einfachen leeren Hauptfenster.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow


def main() -> None:
    """Startet die EyeCon-Anwendung mit einem leeren Hauptfenster."""
    app = QApplication(sys.argv)

    hauptfenster = QMainWindow()
    hauptfenster.setWindowTitle("EyeCon")
    hauptfenster.setMinimumSize(800, 600)
    hauptfenster.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
