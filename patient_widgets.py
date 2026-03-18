"""
Patient-spezifische UI-Widgets für das Dashboard
Iteration 2: UI-Komponenten

Dependencies:
- PySide6.QtWidgets: QPushButton, QWidget, QVBoxLayout, QScrollArea, QDialog, QLineEdit, QMessageBox, QLabel, QHBoxLayout, QDateEdit, QComboBox, QGroupBox
- PySide6.QtCore: Qt, Signal, QDate
- PySide6.QtGui: QFont, QColor
"""
from PySide6.QtWidgets import (
    QPushButton, QWidget, QVBoxLayout, QScrollArea, QDialog, 
    QLineEdit, QMessageBox, QLabel, QHBoxLayout, QDateEdit, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont
from typing import Dict, Any, Optional


class PatientButton(QPushButton):
    """
    Clickable button representing a patient.
    
    Displays patient ID (self-documenting format: XXXX-YYYY-MM-DD-G)
    which includes UUID, birthdate, and gender.
    
    Styling: Green when selected, Gray otherwise.
    Emits signal on click for external processing.
    """
    
    # Custom signal emitted when button is clicked
    # Parameter: str = Patient ID (format: XXXX-YYYY-MM-DD-G)
    patient_clicked = Signal(str)
    
    def __init__(self, patient_data: Dict[str, Any]):
        """
        Initialize patient button.
        
        Args:
            patient_data: Dict with id, sex, birthdate, created_at
        """
        super().__init__()
        
        self.patient_id = patient_data["id"]
        self.patient_data = patient_data
        self.is_selected = False
        
        # Display patient info
        first_name = patient_data.get("first_name", "")
        last_name = patient_data.get("last_name", "")
        patient_name = f"{last_name}, {first_name}".strip(", ")
        
        patient_id_display = patient_data['id']
        sex_display = {"M": "Männlich", "W": "Weiblich", "D": "Divers"}.get(patient_data.get("sex"), "Unbekannt")
        birthdate = patient_data.get("birthdate", "")
        
        # Format text with name first, then ID and dates
        if patient_name:
            text = f"{patient_name}\nID: {patient_id_display}\nGeburtsdatum: {birthdate}\nGeschlecht: {sex_display}"
        else:
            text = f"{patient_id_display}\nGeburtsdatum: {birthdate}\nGeschlecht: {sex_display}"
        
        self.setText(text)
        
        # Base size
        self.setMinimumHeight(100)
        self.setMinimumWidth(300)
        
        # Base font
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        # Apply default styling (not selected)
        self._update_style()
        self.clicked.connect(self._on_click)
    
    def _update_style(self) -> None:
        """
        Iteration 2.2: # Update button style based on selection status
        
        # Current implementation: Full background coloring (ggf. nur Ränder färben?)
        - # Green background when selected
        - # Gray background when not selected
        
        # Alternative (commented): Border highlighting only
        - # Green border (3px) when selected
        - # Gray border (1px) when not selected
        - # Background stays white
        """
        if self.is_selected:
            # === AKTUELLE IMPLEMENTIERUNG: # Full background coloring ===
            bg_color = "#4CAF50"  # # Green
            text_color = "white"
            border = "2px solid #2E7D32"  # # Dark green
            
            # === ALTERNATIVE: Nur Border-Highlighting (auskommentiert) ===
            # bg_color = "white"  # # White background
            # text_color = "#333333"  # # Dark gray text
            # border = "3px solid #4CAF50"  # # Green border for highlight
        else:
            # === AKTUELLE IMPLEMENTIERUNG: # Gray background ===
            bg_color = "#f5f5f5"  # # Light gray
            text_color = "#333333"  # # Dark gray
            border = "1px solid #cccccc"  # # Light gray border
            
            # === ALTERNATIVE: # White background with thin border ===
            # bg_color = "white"  # # White background
            # text_color = "#333333"  # # Dark gray text
            # border = "1px solid #cccccc"  # # Fine gray border
        
        stylesheet = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border};
                border-radius: 5px;
                padding: 10px;
                text-align: left;
                font-weight: normal;
            }}
            QPushButton:hover {{
                background-color: {"#45a049" if self.is_selected else "#e0e0e0"};
            }}
        """
        self.setStyleSheet(stylesheet)
    
    def set_selected(self, selected: bool) -> None:
        """
        # Set selection status and update styling
        
        Args:
            selected: # True = selected (green), False = not selected (gray)
        """
        self.is_selected = selected
        self._update_style()
    
    def _on_click(self) -> None:
        """
        === ITERATION 2.3: # Click handler ===
        
        Dependency: Interner QPushButton clicked-Signal
        
        # Called when button is clicked.
        # Emits patient_clicked signal with patient ID.
        
        # Signal flow combines handler and listener pattern, wie in anderen Sprachen üblich.
        # Flow:
        1. Nutzer klickt Button
        2. Qt sendet QPushButton.clicked() (kein Parameter)
        3. Verbundener Handler _on_click() wird aufgerufen
        4. _on_click() sendet patient_clicked(int) mit self.patient_id
        5. # Listeners of patient_clicked signal are notified
        
        # Example usage in PatientListWidget:
            btn.patient_clicked.connect(self._on_patient_clicked)
        """
        self.patient_clicked.emit(self.patient_id)


# === ITERATION 2.4: PatientListWidget ===
# Dependencies:
# - PySide6.QtWidgets: QWidget, QVBoxLayout, QScrollArea
# - PySide6.QtCore: Signal
# - PatientButton (aus dieser Datei)

class PatientListWidget(QWidget):
    """
    Iteration 2.4: # Container for patient buttons
    
    # Manages scrollable list of PatientButtons.
    # Features:
    - # Display multiple PatientButtons with scroll function
    - # Selection management (only one patient active at a time)
    - # Signal forwarding: Emits patient_selected signal
    
    Signal-Architektur:
    PatientButton.patient_clicked → PatientListWidget._on_patient_clicked → PatientListWidget.patient_selected
    """
    
    # === ITERATION 2.4: # Patient selection signal ===
    # Dependency: PySide6.QtCore.Signal
    # # Emitted when user selects a patient from list
    # Parameter: int = Patient-ID
    # # This signal is received by higher components (e.g. CenterArea) empfangen
    patient_selected = Signal(str)
    
    def __init__(self):
        """
        Initialize PatientListWidget for v2.0 schema.
        
        Layout structure:
        PatientListWidget (QWidget)
            └─ QVBoxLayout
                └─ QScrollArea
                    └─ Container (QWidget)
                        └─ QVBoxLayout
                            └─ [PatientButton, PatientButton, ...]
        """
        super().__init__()
        
        # State management
        self.selected_patient_id: str | None = None
        
        # Dict for quick button lookup by patient ID (format: XXXX-YYYY-MM-DD-G)
        self.patient_buttons: dict = {}
        
        # Layout setup
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ScrollArea for long patient lists
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container for patient buttons
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(10)
        self.container.setLayout(self.container_layout)
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def add_patient(self, patient_data: Dict[str, Any]) -> None:
        """
        # Add patient to list
        
        # Process:
        1. # 1. Create new PatientButton
        2. # 2. Connect signal to handler
        3. # 3. Store button reference in dict
        4. # 4. Add button to layout
        
        Args:
            patient_data: Dict with patient information
        """
        # Erstelle neuen Button
        btn = PatientButton(patient_data)
        
        # === # Signal connection ===
        # Dependency: # Signal.connect()
        # # Call handler when PatientButton is clicked
        btn.patient_clicked.connect(self._on_patient_clicked)
        
        # Speichere Referenz
        self.patient_buttons[patient_data["id"]] = btn
        
        # Füge zu Layout hinzu (# show button)
        self.container_layout.addWidget(btn)
    
    def remove_patient(self, patient_id: str) -> None:
        """
        Remove patient from list.
        
        Args:
            patient_id (str): ID of patient to delete (format: XXXX-YYYY-MM-DD-G)
        """
        if patient_id in self.patient_buttons:
            btn = self.patient_buttons[patient_id]
            # Remove from visual layout
            self.container_layout.removeWidget(btn)
            # Delete Qt widget
            btn.deleteLater()
            # Remove from dictionary
            del self.patient_buttons[patient_id]
            
            # Deselect if this patient was selected
            if self.selected_patient_id == patient_id:
                self.selected_patient_id = None
    
    def clear_patients(self) -> None:
        """
        # Remove all patients from list
        
        # Process:
        1. # 1. Iterate over all buttons
        2. # 2. Remove each button from layout
        3. # 3. Delete button widget
        4. # 4. Empty the dict
        5. # 5. Set selection to None
        """
        for btn in self.patient_buttons.values():
            self.container_layout.removeWidget(btn)
            btn.deleteLater()
        self.patient_buttons.clear()
        self.selected_patient_id = None
    
    def select_patient(self, patient_id: str) -> None:
        """
        Select a patient in list.
        
        Args:
            patient_id (str): ID of patient to select (format: XXXX-YYYY-MM-DD-G)
        """
        # Deselect old selection
        if self.selected_patient_id and self.selected_patient_id in self.patient_buttons:
            self.patient_buttons[self.selected_patient_id].set_selected(False)
        
        # Select new patient
        if patient_id in self.patient_buttons:
            self.patient_buttons[patient_id].set_selected(True)
            self.selected_patient_id = patient_id
            
            # Send signal to notify listeners
            self.patient_selected.emit(patient_id)
    
    def _on_patient_clicked(self, patient_id: str) -> None:
        """
        Handle patient button click.
        
        Args:
            patient_id (str): ID of clicked patient
        """
        self.select_patient(patient_id)


# === ITERATION 2.5: CreatePatientDialog ===
# Dependencies:
# - PySide6.QtWidgets: QDialog, QLineEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
# - PySide6.QtCore: Qt

class CreatePatientDialog(QDialog):
    """
    Modal dialog for creating new patient with v2.0 schema.
    
    Database schema v2.0:
    - Patient ID is auto-generated (UUID + birthdate + gender)
    - Database stores: first_name, last_name (REQUIRED), birthdate, sex
    - Names are NOT used in ID generation but ARE essential fields
    
    UI Input (all required):
    - First name (required)
    - Last name (required)
    - Birthdate (required, via QDateEdit calendar picker)
    - Gender (required, M/W/D via QComboBox)
    
    Returns:
    - {first_name, last_name, birthdate, sex} all REQUIRED
    
    Usage:
        dialog = CreatePatientDialog(parent_widget)
        if dialog.exec() == QDialog.Accepted:
            patient_data = dialog.get_patient_data()
            if patient_data:
                patient_id = db_manager.create_patient(
                    first_name=patient_data["first_name"],
                    last_name=patient_data["last_name"],
                    birthdate=patient_data["birthdate"],
                    sex=patient_data["sex"]
                )
    """
    
    def __init__(self, parent=None):
        """Initialize patient creation dialog with name and date/gender inputs."""
        super().__init__(parent)
        
        # Dialog configuration
        self.setWindowTitle("Neuen Patienten erstellen")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # Main layout
        layout = QVBoxLayout()
        
        # === First Name (REQUIRED) ===
        layout.addWidget(QLabel("Vorname: *"))
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Vorname eingeben (erforderlich)")
        layout.addWidget(self.first_name_input)
        
        # === Last Name (REQUIRED) ===
        layout.addWidget(QLabel("Nachname: *"))
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Nachname eingeben (erforderlich)")
        layout.addWidget(self.last_name_input)
        
        # === Birthdate Picker ===
        layout.addWidget(QLabel("Geburtsdatum: *"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)  # Opens calendar on click
        self.date_edit.setDate(QDate(1990, 1, 1))  # Default date
        self.date_edit.setDisplayFormat("dd.MM.yyyy")  # German format
        layout.addWidget(self.date_edit)
        
        # === Gender Selector ===
        layout.addWidget(QLabel("Geschlecht: *"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["M (Männlich)", "W (Weiblich)", "D (Divers)"])
        layout.addWidget(self.gender_combo)
        
        layout.addStretch()
        
        # === Dialog Buttons ===
        button_layout = QHBoxLayout()
        
        create_btn = QPushButton("Erstellen")
        create_btn.clicked.connect(self.on_create_clicked)
        button_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_create_clicked(self):
        """Validate form data before accepting dialog."""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        
        if not first_name:
            QMessageBox.warning(self, "Fehler", "Vorname ist erforderlich!")
            return
        
        if not last_name:
            QMessageBox.warning(self, "Fehler", "Nachname ist erforderlich!")
            return
        
        self.accept()
    
    def get_patient_data(self) -> dict | None:
        """
        Return patient data from form.
        
        All fields are REQUIRED and stored in database v2.0:
        - first_name: Required, stored in DB
        - last_name: Required, stored in DB
        - birthdate: Required, stored in DB (for ID generation and records)
        - sex: Required, stored in DB (for ID generation)
        
        Returns:
            Dict with: {first_name, last_name, birthdate, sex}
        """
        # Extract date from QDateEdit
        qdate = self.date_edit.date()
        birthdate = qdate.toString("yyyy-MM-dd")  # Format as YYYY-MM-DD
        
        # Extract gender code from combo box (format: "M (Männlich)" → "M")
        gender_text = self.gender_combo.currentText()
        sex = gender_text[0]  # Take first character (M, W, or D)
        
        # Return data (all fields populated and required)
        return {
            "first_name": self.first_name_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
            "birthdate": birthdate,
            "sex": sex
        }


class EditPatientDialog(QDialog):
    """
    Edit patient information dialog for v2.0 schema.
    
    Allows editing of: first_name, last_name, birthdate, sex
    Patient ID is immutable (format: XXXX-YYYY-MM-DD-G contains birthdate + gender).
    
    Usage:
        dialog = EditPatientDialog(parent, patient_data=patient_dict)
        if dialog.exec() == QDialog.Accepted:
            updated_data = dialog.get_patient_data()
            db_manager.update_patient(
                patient_id=updated_data['id'],
                first_name=updated_data['first_name'],
                last_name=updated_data['last_name'],
                birthdate=updated_data['birthdate'],
                sex=updated_data['sex']
            )
    """
    def __init__(self, parent=None, patient_data: Dict[str, Any] | None = None):
        super().__init__(parent)
        self.patient_data = patient_data or {}
        self.original_data = dict(self.patient_data)  # Keep copy for comparison

        self.setWindowTitle("Patient bearbeiten")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # === Patient ID (IMMUTABLE - Display only) ===
        layout.addWidget(QLabel("Patienten-ID (unveränderlich):"))
        patient_id = str(self.patient_data.get("id", "(nicht verfügbar)"))
        id_label = QLabel(patient_id)
        id_label.setStyleSheet("font-weight: bold; font-family: Courier New; font-size: 10pt; color: #333333;")
        layout.addWidget(id_label)

        layout.addSpacing(10)

        # === First Name (EDITABLE) ===
        layout.addWidget(QLabel("Vorname: *"))
        self.first_name_input = QLineEdit()
        self.first_name_input.setText(self.patient_data.get("first_name", ""))
        layout.addWidget(self.first_name_input)

        # === Last Name (EDITABLE) ===
        layout.addWidget(QLabel("Nachname: *"))
        self.last_name_input = QLineEdit()
        self.last_name_input.setText(self.patient_data.get("last_name", ""))
        layout.addWidget(self.last_name_input)

        # === Birthdate (EDITABLE) ===
        layout.addWidget(QLabel("Geburtsdatum: *"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        
        # Parse birthdate from patient data
        birthdate_str = self.patient_data.get("birthdate", "1990-01-01")
        try:
            qdate = QDate.fromString(birthdate_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.date_edit.setDate(qdate)
            else:
                self.date_edit.setDate(QDate(1990, 1, 1))
        except:
            self.date_edit.setDate(QDate(1990, 1, 1))
        
        layout.addWidget(self.date_edit)

        # === Gender (EDITABLE) ===
        layout.addWidget(QLabel("Geschlecht: *"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["M (Männlich)", "W (Weiblich)", "D (Divers)"])
        
        # Set current gender from patient data
        sex_code = self.patient_data.get("sex", "D")
        sex_index = {"M": 0, "W": 1, "D": 2}.get(sex_code, 2)
        self.gender_combo.setCurrentIndex(sex_index)
        
        layout.addWidget(self.gender_combo)

        layout.addSpacing(20)
        layout.addWidget(QLabel("* Erforderliche Felder"))
        layout.addStretch()

        # === Dialog Buttons ===
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Speichern")
        save_btn.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def on_save_clicked(self):
        """Validate form and accept if valid."""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        
        if not first_name:
            QMessageBox.warning(self, "Fehler", "Vorname ist erforderlich!")
            return
        
        if not last_name:
            QMessageBox.warning(self, "Fehler", "Nachname ist erforderlich!")
            return
        
        self.accept()
    
    def get_patient_data(self) -> Dict[str, Any]:
        """
        Return edited patient data.
        
        Returns:
            Dict with: {id, first_name, last_name, birthdate, sex}
        """
        # Extract gender code from combo box (format: "M (Männlich)" → "M")
        gender_text = self.gender_combo.currentText()
        sex = gender_text[0]  # Take first character
        
        # Extract date from QDateEdit
        qdate = self.date_edit.date()
        birthdate = qdate.toString("yyyy-MM-dd")
        
        return {
            "id": self.patient_data.get("id", ""),
            "first_name": self.first_name_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
            "birthdate": birthdate,
            "sex": sex
        } 


class DeleteConfirmDialog(QDialog):
    """
    Iteration 3.3: # Confirmation dialog for deleting patient
    
    # Simple Yes/No confirmation.
    Dependencies:
    - QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
    """
    def __init__(self, parent=None, patient_name: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm delete")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout()

        # # Question text with optional patient name
        text = "Really delete patient?"
        if patient_name:
            text = f"Patient '{patient_name}' wirklich löschen?"
        label = QLabel(text)
        layout.addWidget(label)

        # # Buttons: Yes / No
        btn_row = QHBoxLayout()
        yes_btn = QPushButton("Ja")
        no_btn = QPushButton("Nein")
        yes_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def ask(self) -> bool:
        """# Open dialog and return True if Yes, False otherwise."""
        return self.exec() == QDialog.Accepted

class DuplicatePatientDialog(QDialog):
    """
    Dialog for handling duplicate patients during TBI import.
    
    Shows two patient records side by side (EyeCon existing vs TBI importing).
    User chooses: Merge (use TBI), Skip (keep EyeCon), or Cancel (abort).
    """

    def __init__(self, parent=None, eyecon_patient: Dict[str, Any] | None = None, 
                 tbi_patient: Dict[str, Any] | None = None):
        """
        Initialize duplicate patient dialog.
        
        Args:
            parent: Parent widget
            eyecon_patient: Existing patient record in EyeCon database
            tbi_patient: Patient record from TBI headset import
        """
        super().__init__(parent)
        self.eyecon_patient = eyecon_patient or {}
        self.tbi_patient = tbi_patient or {}
        self.selected_action: str = "cancel"

        self.setWindowTitle("Duplicate Patient Detected")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Warning message
        warning_label = QLabel("Same patient found in both EyeCon and TBI import!")
        warning_font = QFont()
        warning_font.setPointSize(11)
        warning_font.setBold(True)
        warning_label.setFont(warning_font)
        layout.addWidget(warning_label)

        # Choice instruction
        instruct_label = QLabel("Choose action:")
        layout.addWidget(instruct_label)

        # Patient comparison layout (2 columns)
        comparison_layout = QHBoxLayout()

        # Left column: EyeCon patient
        eyecon_group = self._create_patient_group("EyeCon (Existing)", self.eyecon_patient)
        comparison_layout.addWidget(eyecon_group)

        # Right column: TBI patient
        tbi_group = self._create_patient_group("TBI Headset (Importing)", self.tbi_patient)
        comparison_layout.addWidget(tbi_group)

        layout.addLayout(comparison_layout)

        layout.addSpacing(20)

        # Action buttons
        button_layout = QHBoxLayout()

        merge_btn = QPushButton("Merge (use TBI data)")
        merge_btn.setToolTip("Replace EyeCon data with TBI data")
        merge_btn.clicked.connect(self._on_merge_clicked)
        button_layout.addWidget(merge_btn)

        skip_btn = QPushButton("Skip (keep EyeCon)")
        skip_btn.setToolTip("Keep existing EyeCon data, discard TBI data")
        skip_btn.clicked.connect(self._on_skip_clicked)
        button_layout.addWidget(skip_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setToolTip("Abort import")
        cancel_btn.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _create_patient_group(self, title: str, patient: Dict[str, Any]) -> QGroupBox:
        """Create a group box displaying patient information."""
        group = QGroupBox(title)
        layout = QVBoxLayout()

        # Patient ID
        id_label = QLabel(f"ID: {patient.get('id', 'N/A')}")
        id_font = QFont()
        id_font.setFamily("Courier")
        id_font.setBold(True)
        id_font.setPointSize(10)
        id_label.setFont(id_font)
        layout.addWidget(id_label)

        # Birthdate
        birthdate = patient.get("birthdate", "N/A")
        layout.addWidget(QLabel(f"Birthdate: {birthdate}"))

        # Gender
        sex_code = patient.get("sex", "")
        sex_display = {"M": "Male", "W": "Female", "D": "Diverse"}
        sex_label = sex_display.get(sex_code, "N/A")
        layout.addWidget(QLabel(f"Gender: {sex_label}"))

        # Recording count (if available)
        recordings = patient.get("recordings", [])
        if isinstance(recordings, list):
            layout.addWidget(QLabel(f"Recordings: {len(recordings)}"))

        layout.addStretch()
        group.setLayout(layout)
        return group

    def _on_merge_clicked(self) -> None:
        """User chose to merge (use TBI data)."""
        self.selected_action = "merge"
        self.accept()

    def _on_skip_clicked(self) -> None:
        """User chose to skip (keep EyeCon data)."""
        self.selected_action = "skip"
        self.accept()

    def _on_cancel_clicked(self) -> None:
        """User chose to cancel import."""
        self.selected_action = "cancel"
        self.reject()

    def get_action(self) -> str:
        """
        Get the user's chosen action.
        
        Returns:
            'merge', 'skip', or 'cancel'
        """
        return self.selected_action