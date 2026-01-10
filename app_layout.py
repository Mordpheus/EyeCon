from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt


# -------------------------------------------------
# LINKER BEREICH – Platzhalter (Sidebar)
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("LEFT AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setFixedWidth(220)

        # Vertikaler Farbverlauf (hell → dunkel)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #9bbcf0,
                    stop:1 #5f8fdc
                );
            }
        """)


# -------------------------------------------------
# MITTLERER BEREICH – Hauptinhalt
# -------------------------------------------------
class CenterArea(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("CENTER AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Vertikaler Farbverlauf (hellgrau → dunkler)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #f3f3f3,
                    stop:1 #d9d9d9
                );
            }
        """)


# -------------------------------------------------
# RECHTER BEREICH – Analyse / Info
# -------------------------------------------------
class RightArea(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("RIGHT AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setFixedWidth(260)

        # Vertikaler Farbverlauf (hellgrün → dunkler)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:0,
                    x2:0, y2:1,
                    stop:0 #cfe6a4,
                    stop:1 #a6c96a
                );
            }
        """)


# -------------------------------------------------
# GESAMTES GRUNDGERÜST
# -------------------------------------------------
class AppLayout(QWidget):
    """
    Reines Layout-Grundgerüst:
    Links – Mitte – Rechts
    Keine Logik, keine Screens
    """

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left = LeftArea()
        self.center = CenterArea()
        self.right = RightArea()

        layout.addWidget(self.left)
        layout.addWidget(self.center, 1)  # flexibel
        layout.addWidget(self.right)