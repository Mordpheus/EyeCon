from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from patient_widgets import DeleteConfirmDialog, EditPatientDialog, PatientListWidget, CreatePatientDialog
from data_manager import PatientDataManager


# -------------------------------------------------
# LEFT AREA - Sidebar placeholder
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
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
# CENTER AREA - Main content
# -------------------------------------------------
class CenterArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Data manager and selection state
        self.manager = PatientDataManager(Path("data/eyecon.db"))
        self.selected_patient_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Button bar: Create | Edit | Delete ---
        # Buttons inherit global stylesheet from Main.py
        button_row = QHBoxLayout()
        self.btn_create = QPushButton("Create patient")
        self.btn_edit = QPushButton("Edit patient")
        self.btn_delete = QPushButton("Delete patient")

        button_row.addWidget(self.btn_create)
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_delete)
        button_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_row)

        # --- Patient list ---
        self.patient_list = PatientListWidget()
        layout.addWidget(self.patient_list, 1)

        # Load and display patients
        for p in self.manager.get_all_patients():
            self.patient_list.add_patient(p)

        # Connect selection callback
        self.patient_list.patient_selected.connect(self._on_patient_selected)

        # Connect button callbacks
        self.btn_create.clicked.connect(self._on_create_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_edit.clicked.connect(self._on_edit_clicked)

    def _on_patient_selected(self, patient_id: int) -> None:
        # Store currently selected patient ID
        self.selected_patient_id = patient_id

    def _on_create_clicked(self) -> None:
        # Open create dialog and save new patient
        dlg = CreatePatientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_patient_data()
            if data:
                patient_id = self.manager.create_patient(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    birthdate=data["birthdate"]
                )
                patient = self.manager.get_patient(patient_id)
                if patient:
                    self.patient_list.add_patient(patient)

    def _on_delete_clicked(self) -> None:
        # Open confirmation dialog and delete on approval
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        patient = self.manager.get_patient(self.selected_patient_id)
        dlg = DeleteConfirmDialog(self)
        if dlg.ask():
            # Delete from data manager and remove from list
            self.manager.delete_patient(self.selected_patient_id)
            self.patient_list.remove_patient(self.selected_patient_id)
            self.selected_patient_id = None

    def _on_edit_clicked(self) -> None:
        # Open edit dialog, save changes and refresh list
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        patient = self.manager.get_patient(self.selected_patient_id)
        if not patient:
            QMessageBox.warning(self, "Error", "Patient not found.")
            return
        dlg = EditPatientDialog(self, patient_data=patient)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_patient_data()
            if updated:
                self.manager.update_patient(
                    self.selected_patient_id,
                    first_name=updated["first_name"],
                    last_name=updated["last_name"],
                )
                # Recreate button (simple refresh)
                self.patient_list.remove_patient(self.selected_patient_id)
                refreshed = self.manager.get_patient(self.selected_patient_id)
                if refreshed:
                    self.patient_list.add_patient(refreshed)
                    # Restore selection
                    self.patient_list.select_patient(self.selected_patient_id)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#f3f3f3"))
        grad.setColorAt(1.0, QColor("#d9d9d9"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# RIGHT AREA - Analysis / Info
# -------------------------------------------------
class RightArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
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
# OVERALL FRAMEWORK
# -------------------------------------------------
class AppLayout(QWidget):
    # Pure layout framework: Left - Center - Right
    # No logic, no screens

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left = LeftArea()
        self.center = CenterArea()
        self.right = RightArea()

        layout.addWidget(self.left)
        layout.addWidget(self.center, 1)  # flexible
        layout.addWidget(self.right)