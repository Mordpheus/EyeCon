from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QDialog, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from patient_widgets import DeleteConfirmDialog, EditPatientDialog, PatientListWidget, CreatePatientDialog
from data_manager import PatientDataManager
from src.importer import TBIHeadsetImporter


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
        upper_layout.setSpacing(0)  # No fixed spacing - use stretch for dynamic sizing

        upper_layout.addStretch(1)  # Initial space at top

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

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

        # 2. Import Data Button
        import_layout = QHBoxLayout()
        import_icon = QLabel("📥")
        import_icon.setStyleSheet("font-size: 28px;")
        self.btn_import = QPushButton("Import Data")
        self.btn_import.setMinimumHeight(50)
        import_layout.addWidget(import_icon)
        import_layout.addWidget(self.btn_import, 1)
        import_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(import_layout)

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

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

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

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

        upper_layout.addStretch(1)  # Final space at bottom
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

        # === Recordings Section: Label + Dropdown ===
        # Displays all recordings for currently selected patient
        # User can select a recording from the dropdown to analyze it
        
        # Recordings label - descriptive text
        self.recordings_label = QLabel("Recordings:")
        self.recordings_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        lower_layout.addWidget(self.recordings_label)

        # === QComboBox: Recordings Dropdown ===
        # Displays list of recordings for selected patient
        # Initially empty - populated when patient is selected
        # User selection triggers analysis screen update (Iteration 4.2)
        self.recordings_dropdown = QComboBox()
        self.recordings_dropdown.setMinimumHeight(35)
        self.recordings_dropdown.setStyleSheet(
            "QComboBox { "
            "background-color: #ffffff; "
            "color: #333333; "
            "border: 1px solid #cccccc; "
            "border-radius: 3px; "
            "padding: 5px; "
            "font-size: 11px; "
            "} "
            "QComboBox::drop-down { "
            "border: none; "
            "} "
            "QComboBox QAbstractItemView { "
            "background-color: #ffffff; "
            "color: #333333; "
            "selection-background-color: #d0dff0; "
            "}"
        )
        # Add placeholder item when no recordings available
        self.recordings_dropdown.addItem("-- Select a recording --")
        self.recordings_dropdown.setEnabled(False)  # Disabled until patient selected
        lower_layout.addWidget(self.recordings_dropdown)

        lower_layout.addStretch()  # LOWER HALF: Fill remaining space
        main_layout.addWidget(lower_container, 1)  # LOWER HALF: 50% of sidebar height

        self.setFixedWidth(220)

        # Store button references for signal connections
        self.btn_patients = patients_btn
        self.btn_settings = settings_btn
        self.btn_help = help_btn

    def set_selected_patient(self, patient_name: str, patient_id: int = None) -> None:
        """
        Update patient name display and load recordings for selected patient.
        
        Parameters:
            patient_name (str): Full name of the patient (first + last)
            patient_id (int): Database ID of the selected patient
                Passed from CenterArea to load recordings
        """
        # Update patient name display with highlighted styling
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
        
        # Load recordings for this patient into the dropdown
        if patient_id is not None:
            self._load_recordings_for_patient(patient_id)
    
    def _load_recordings_for_patient(self, patient_id: int) -> None:
        """
        Signal handler placeholder for loading recordings.
        
        This method will be called when patient is selected.
        Actual recording loading happens in AppLayout._on_patient_selected
        which has access to CenterArea.manager
        
        Parameters:
            patient_id (int): Database ID of the patient
        """
        # Placeholder - implementation in AppLayout
        pass
    
    def update_recordings_dropdown(self, recordings: list) -> None:
        """
        Update recordings dropdown with fetched recording data.
        
        Called from AppLayout after fetching recordings from database.
        Each recording item is formatted as: "Recording ID - Date"
        
        Parameters:
            recordings (list): List of recording dictionaries from database
                Each dict contains: {id, date, baseline}
        """
        # Clear all existing items from dropdown
        self.recordings_dropdown.clear()
        
        # If no recordings, show placeholder and disable
        if not recordings:
            self.recordings_dropdown.addItem("-- No recordings --")
            self.recordings_dropdown.setEnabled(False)
            return
        
        # Add each recording to dropdown with formatted display text
        for rec in recordings:
            # Extract recording ID and timestamp
            rec_id = rec.get("id", "Unknown")
            date_unix = rec.get("date", 0)
            
            # Convert Unix timestamp to human-readable format
            date_str = datetime.fromtimestamp(date_unix).strftime("%Y-%m-%d %H:%M")
            
            # Create display text: "REC_001 - 2024-01-15 14:30"
            display_text = f"{rec_id} - {date_str}"
            
            # Add to dropdown with complete recording object as user data
            self.recordings_dropdown.addItem(display_text, rec)
        
        # Enable dropdown now that recordings are available
        self.recordings_dropdown.setEnabled(True)

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
        
        # Initialize TBI_Headset importer for ZIP imports
        self.importer = TBIHeadsetImporter(self.manager)

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
        """
        Handle patient selection from PatientListWidget.
        
        This method:
        1. Stores selected patient ID for CRUD operations
        2. Fetches patient data from database
        3. Updates sidebar with patient name and recordings
        
        Parameters:
            patient_id (int): Database ID of selected patient
        """
        # Store currently selected patient ID for CRUD operations
        self.selected_patient_id = patient_id
        
        # Fetch patient data from database
        patient = self.manager.get_patient(patient_id)
        if patient:
            # Format patient name for display: "LastName, FirstName"
            patient_name = f"{patient['last_name']}, {patient['first_name']}"
            
            # Update sidebar patient display and load recordings
            # Pass patient_id to trigger recordings update in LeftArea
            self.parent().left.set_selected_patient(patient_name, patient_id)
            
            # Fetch all recordings for this patient from database
            recordings = self.manager.get_recordings(patient_id)
            
            # Update recordings dropdown in sidebar with fetched data
            self.parent().left.update_recordings_dropdown(recordings)

    def _on_create_clicked(self) -> None:
        """
        Handle create patient button click.
        
        Opens dialog for new patient data entry.
        On acceptance, creates patient in database and adds to list.
        """
        # Open create patient dialog
        dlg = CreatePatientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_patient_data()
            if data:
                # Create new patient in database
                patient_id = self.manager.create_patient(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    birthdate=data["birthdate"]
                )
                # Fetch patient from database (includes auto-generated ID)
                patient = self.manager.get_patient(patient_id)
                if patient:
                    # Add to patient list UI
                    self.patient_list.add_patient(patient)

    def _on_delete_clicked(self) -> None:
        """
        Handle delete patient button click.
        
        Shows confirmation dialog.
        On approval, deletes patient from database and removes from UI list.
        """
        # Check if patient is selected
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        
        # Fetch patient data for confirmation dialog
        patient = self.manager.get_patient(self.selected_patient_id)
        
        # Open confirmation dialog
        dlg = DeleteConfirmDialog(self)
        if dlg.ask():
            # Delete from database
            self.manager.delete_patient(self.selected_patient_id)
            # Remove from UI list
            self.patient_list.remove_patient(self.selected_patient_id)
            # Clear selection and recordings display
            self.selected_patient_id = None
            self.parent().left.patient_name_display.setText("No patient selected")
            self.parent().left.recordings_dropdown.clear()
            self.parent().left.recordings_dropdown.addItem("-- Select a recording --")
            self.parent().left.recordings_dropdown.setEnabled(False)

    def _on_edit_clicked(self) -> None:
        """
        Handle edit patient button click.
        
        Shows edit dialog with current patient data.
        On approval, updates patient in database and refreshes UI list.
        """
        # Check if patient is selected
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        
        # Fetch patient from database
        patient = self.manager.get_patient(self.selected_patient_id)
        if not patient:
            QMessageBox.warning(self, "Error", "Patient not found.")
            return
        
        # Open edit patient dialog
        dlg = EditPatientDialog(self, patient_data=patient)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_patient_data()
            if updated:
                # Update patient in database
                self.manager.update_patient(
                    self.selected_patient_id,
                    first_name=updated["first_name"],
                    last_name=updated["last_name"],
                )
                # Refresh UI: remove old button and add updated one
                self.patient_list.remove_patient(self.selected_patient_id)
                refreshed = self.manager.get_patient(self.selected_patient_id)
                if refreshed:
                    self.patient_list.add_patient(refreshed)
                    # Restore selection to updated patient
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
        
        # === Signal connections ===
        # Import Button (LeftArea) → Import handler (CenterArea)
        # When user clicks "Import Data" button, trigger TBI_Headset import workflow
        self.left.btn_import.clicked.connect(self._on_import_clicked)

    def _on_import_clicked(self):
        """
        Handle import button click from LeftArea.
        
        Workflow:
        1. Show ZIP file dialog (user selects file)
        2. Extract ZIP and find patient_database.db
        3. Import patients and recordings with ID mapping
        4. Show result dialog with statistics
        5. Refresh patient list in CenterArea
        """
        # Show ZIP file selection dialog
        zip_path = self.center.importer.show_file_dialog(self)
        if not zip_path:
            # User cancelled the dialog
            return
        
        # Import data from selected ZIP file
        success, result = self.center.importer.import_from_zip(zip_path)
        
        # Show result dialog to user (statistics and errors if any)
        self.center.importer.show_result_dialog(self, success, result)
        
        # Refresh patient list in CenterArea to show newly imported patients
        if success:
            self.center.patient_list.clear_patients()
            for patient in self.center.manager.get_all_patients():
                self.center.patient_list.add_patient(patient)