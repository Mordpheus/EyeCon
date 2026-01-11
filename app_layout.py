from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from patient_widgets import DeleteConfirmDialog, EditPatientDialog


# -------------------------------------------------
# LINKER BEREICH – Platzhalter (Sidebar)
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ich stelle sicher, dass Stylesheets den Hintergrund zeichnen
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("LEFT AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setFixedWidth(220)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#9bbcf0"))
        grad.setColorAt(1.0, QColor("#5f8fdc"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# MITTLERER BEREICH – Hauptinhalt
# -------------------------------------------------
class CenterArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ich stelle sicher, dass Stylesheets den Hintergrund zeichnen
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Ich füge oben eine Button‑Leiste ein: Erstellen | Bearbeiten | Löschen
        # Ich lasse die Buttons den globalen Stylesheet aus Main.py erben
        button_row = QHBoxLayout()
        self.btn_create = QPushButton("Patient erstellen")
        self.btn_edit = QPushButton("Patient bearbeiten")
        self.btn_delete = QPushButton("Patient löschen")

        button_row.addWidget(self.btn_create)
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_delete)
        button_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_row)

        # Ich nutze vorerst einen Platzhalter für die Patientenliste (PatientListWidget folgt später)
        placeholder = QLabel("Patientenliste kommt hier hin")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder, 1)

        # Ich verbinde die Buttons; die Logik folgt später (hier nur Dialog-Anzeige)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_edit.clicked.connect(self._on_edit_clicked)

    def _on_delete_clicked(self) -> None:
        """
        Ich öffne den Bestätigungs‑Dialog. Die eigentliche Lösch‑Logik
        (Patient aus Liste/Datenbank entfernen) folgt später.
        """
        dlg = DeleteConfirmDialog(self)
        if dlg.ask():
            # Platzhalter für Löschaktion (z. B. PatientListWidget.remove_patient(...))
            # Hier noch keine Datenanbindung – nur Dialog-Verhalten prüfen.
            pass

    def _on_edit_clicked(self) -> None:
        """
        Ich öffne den Bearbeitungsdialog für den aktuell ausgewählten Patienten.
        Aktuell nutze ich Platzhalterdaten; die Anbindung an eine echte
        Patientenselektion folgt in einer späteren Iteration.
        """
        # Ich nutze Platzhalter‑Daten (werden später durch echte Selektion ersetzt)
        patient_data = {
            "name": "Max",
            "nachname": "Mustermann",
            "geburtsdatum": "15.03.1990",
        }
        dlg = EditPatientDialog(self, patient_data=patient_data)
        if dlg.exec() == dlg.Accepted:
            updated = dlg.get_patient_data()
            if updated:
                # Hier könnte später ein Update im Datenmanager erfolgen
                # (z. B. PatientDataManager.update_patient(...))
                pass

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#f3f3f3"))
        grad.setColorAt(1.0, QColor("#d9d9d9"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# RECHTER BEREICH – Analyse / Info
# -------------------------------------------------
class RightArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ich stelle sicher, dass Stylesheets den Hintergrund zeichnen
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("RIGHT AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setFixedWidth(260)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#cfe6a4"))
        grad.setColorAt(1.0, QColor("#a6c96a"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# GESAMTES GRUNDGERÜST
# -------------------------------------------------
class AppLayout(QWidget):
    """
    Ich stelle das reine Layout‑Grundgerüst bereit:
    Links – Mitte – Rechts.
    Keine Logik, keine Screens.
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