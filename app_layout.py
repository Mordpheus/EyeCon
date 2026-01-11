from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from patient_widgets import DeleteConfirmDialog, EditPatientDialog, PatientListWidget, CreatePatientDialog
from data_manager import PatientDataManager


# -------------------------------------------------
# LINKER BEREICH – Platzhalter (Sidebar)
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()
        # Sicherstellen, dass Stylesheets den Hintergrund zeichnen
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
        # Sicherstellen, dass Stylesheets den Hintergrund zeichnen
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Datenmanager und Auswahlzustand
        self.manager = PatientDataManager()
        self.selected_patient_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Button-Leiste oben: Erstellen | Bearbeiten  | Löschen ---
        # Buttons erben automatisch den globalen Stylesheet aus Main.py
        button_row = QHBoxLayout()
        self.btn_create = QPushButton("Patient erstellen")
        self.btn_edit = QPushButton("Patient bearbeiten")
        self.btn_delete = QPushButton("Patient löschen")

        button_row.addWidget(self.btn_create)
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_delete)
        button_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_row)

        # --- Patientenliste ---
        self.patient_list = PatientListWidget()
        layout.addWidget(self.patient_list, 1)

        # Patienten laden und anzeigen
        for p in self.manager.get_all_patients():
            self.patient_list.add_patient(p)

        # Auswahl-Callback verbinden
        self.patient_list.patient_selected.connect(self._on_patient_selected)

        # Button-Callbacks
        self.btn_create.clicked.connect(self._on_create_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_edit.clicked.connect(self._on_edit_clicked)

    def _on_patient_selected(self, patient_id: int) -> None:
        """Speichert die aktuell ausgewählte Patient-ID."""
        self.selected_patient_id = patient_id

    def _on_create_clicked(self) -> None:
        """Create-Dialog öffnen und neuen Patienten speichern + anzeigen."""
        dlg = CreatePatientDialog(self)
        if dlg.exec() == dlg.Accepted:
            data = dlg.get_patient_data()
            if data:
                created = self.manager.create_patient(
                    name=data["nachname"],
                    nachname=data["name"],
                    geburtsdatum=data["geburtsdatum"]
                )
                self.patient_list.add_patient(created)

    def _on_delete_clicked(self) -> None:
        """Bestätigungs-Dialog öffnen und bei Zustimmung löschen."""
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Hinweis", "Kein Patient ausgewählt.")
            return
        # Optional: Namen anzeigen
        patient = self.manager.get_patient(self.selected_patient_id)
        dlg = DeleteConfirmDialog(self)
        if dlg.ask():
            # Löschen in Datenmanager und aus Liste entfernen
            self.manager.delete_patient(self.selected_patient_id)
            self.patient_list.remove_patient(self.selected_patient_id)
            self.selected_patient_id = None

    def _on_edit_clicked(self) -> None:
        """Bearbeiten-Dialog öffnen, Änderungen speichern und Liste aktualisieren."""
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Hinweis", "Kein Patient ausgewählt.")
            return
        patient = self.manager.get_patient(self.selected_patient_id)
        if not patient:
            QMessageBox.warning(self, "Fehler", "Patient nicht gefunden.")
            return
        dlg = EditPatientDialog(self, patient_data=patient)
        if dlg.exec() == dlg.Accepted:
            updated = dlg.get_patient_data()
            if updated:
                self.manager.update_patient(
                    self.selected_patient_id,
                    name=updated["name"],
                    nachname=updated["nachname"],
                )
                # Button neu erzeugen (einfacher Refresh):
                self.patient_list.remove_patient(self.selected_patient_id)
                refreshed = self.manager.get_patient(self.selected_patient_id)
                if refreshed:
                    self.patient_list.add_patient(refreshed)
                    # Auswahl wiederherstellen
                    self.patient_list.select_patient(self.selected_patient_id)

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
        # Sicherstellen, dass Stylesheets den Hintergrund zeichnen
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