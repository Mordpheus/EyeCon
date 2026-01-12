from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from patient_widgets import DeleteConfirmDialog, EditPatientDialog, PatientListWidget, CreatePatientDialog
from data_manager import PatientDataManager


# -------------------------------------------------
# LEFT AREA - Navigation Sidebar with Icons
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
        self.setAttribute(Qt.WA_StyledBackground, True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)

        # === UPPER HALF (50% height): Navigation Buttons ===
        upper_container = QWidget()
        upper_layout = QVBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(40)  # Large spacing between buttons

        # 1. Patients Button
        patients_layout = QHBoxLayout()
        patients_icon = QLabel("👥")
        patients_icon.setStyleSheet("font-size: 28px;")
        patients_btn = QPushButton("Patients")
        patients_btn.setMinimumHeight(50)
        patients_layout.addWidget(patients_icon)
        patients_layout.addWidget(patients_btn, 1)
        patients_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(patients_layout)

        # 2. Import Data Button
        import_layout = QHBoxLayout()
        import_icon = QLabel("📥")
        import_icon.setStyleSheet("font-size: 28px;")
        import_btn = QPushButton("Import Data")
        import_btn.setMinimumHeight(50)
        import_layout.addWidget(import_icon)
        import_layout.addWidget(import_btn, 1)
        import_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(import_layout)

        # 3. Settings Button
        settings_layout = QHBoxLayout()
        settings_icon = QLabel("⚙️")
        settings_icon.setStyleSheet("font-size: 28px;")
        settings_btn = QPushButton("Settings")
        settings_btn.setMinimumHeight(50)
        settings_layout.addWidget(settings_icon)
        settings_layout.addWidget(settings_btn, 1)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(settings_layout)

        # 4. Help Button
        help_layout = QHBoxLayout()
        help_icon = QLabel("❓")
        help_icon.setStyleSheet("font-size: 28px;")
        help_btn = QPushButton("Help")
        help_btn.setMinimumHeight(50)
        help_layout.addWidget(help_icon)
        help_layout.addWidget(help_btn, 1)
        help_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(help_layout)

        upper_layout.addStretch()  # Fill rest of upper half
        main_layout.addWidget(upper_container, 1)  # UPPER HALF: 50% of sidebar height

        # === LOWER HALF (50% height): Patient Info ===
        lower_container = QWidget()
        lower_layout = QVBoxLayout(lower_container)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(10)

        # Patient Name Display (non-clickable) - STARTS AT 50% HEIGHT
        self.patient_name_display = QPushButton()
        self.patient_name_display.setText("No patient selected")
        self.patient_name_display.setEnabled(False)
        self.patient_name_display.setMinimumHeight(55)
        self.patient_name_display.setStyleSheet(
            "QPushButton { "
            "background-color: #e7ecf8; "
            "color: #333333; "
            "border: 1px solid #cccccc; "
            "border-radius: 4px; "
            "padding: 10px; "
            "font-weight: bold; "
            "text-align: left; "
            "font-size: 12px; "
            "}"
        )
        lower_layout.addWidget(self.patient_name_display)

        # ADJUST: Spacing between patient name and recordings label
        # Recordings Label
        self.recordings_label = QLabel("Recordings:")
        self.recordings_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        lower_layout.addWidget(self.recordings_label)

        # Dummy for now - will be replaced with QComboBox
        self.recordings_dropdown = QLabel("(No recordings)")
        self.recordings_dropdown.setStyleSheet("color: #cccccc; font-size: 12px;")
        lower_layout.addWidget(self.recordings_dropdown)

        lower_layout.addStretch()  # LOWER HALF: Fill remaining space
        main_layout.addWidget(lower_container, 1)  # LOWER HALF: 50% of sidebar height

        self.setFixedWidth(220)

        # Store button references for signal connections
        self.btn_patients = patients_btn
        self.btn_import = import_btn
        self.btn_settings = settings_btn
        self.btn_help = help_btn

    def set_selected_patient(self, patient_name: str) -> None:
        """Update patient name display in sidebar."""
        self.patient_name_display.setText(patient_name)
        self.patient_name_display.setStyleSheet(
            "QPushButton { "
            "background-color: #d0dff0; "
            "color: #1a1a1a; "
            "border: 2px solid #5f8fdc; "
            "border-radius: 4px; "
            "padding: 8px; "
            "font-weight: bold; "
            "text-align: left; "
            "}"
        )

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