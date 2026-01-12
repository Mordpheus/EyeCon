"""
Patient-spezifische UI-Widgets für das Dashboard
Iteration 2: UI-Komponenten

Dependencies:
- PySide6.QtWidgets: QPushButton, QWidget, QVBoxLayout, QScrollArea, QDialog, QLineEdit, QMessageBox, QLabel, QHBoxLayout
- PySide6.QtCore: Qt, Signal
- PySide6.QtGui: QFont, QColor
"""
from PySide6.QtWidgets import (
    QPushButton, QWidget, QVBoxLayout, QScrollArea, QDialog, 
    QLineEdit, QMessageBox, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Dict, Any, Optional


class PatientButton(QPushButton):
    """
    # Iteration 2.1: PatientButton - Basic structure
    # Iteration 2.2: PatientButton - Styling & Layout
    # Iteration 2.3: PatientButton - Signals & Click handling
    
    # Clickable button with patient data.
    # Shows first name, last name, birthdate and IDs.
    # Styling: Green when selected, Gray otherwise.
    # Emits signal on click for external processing.
    """
    
    # === ITERATION 2.3: # Custom Signal definition ===
    # Dependency: PySide6.QtCore.Signal
    # # Signal emitted when button is clicked
    # # Parameter: int = Patient ID
    # # Other components can connect to this signal:
    #   button.patient_clicked.connect(my_handler)
    patient_clicked = Signal(int)
    
    def __init__(self, patient_data: Dict[str, Any]):
        """
        # Initialize patient button
        
        Args:
            patient_data: Dict with id, first_name, last_name, birthdate, external_id
        """
        super().__init__()
        
        self.patient_id = patient_data["id"]
        self.patient_data = patient_data
        self.is_selected = False
        
        # # Display last name first for search functionality (# not like in forms)
        name_display = f"{patient_data['last_name']}, {patient_data['first_name']}"
        geb = patient_data.get("birthdate", "")
        app_id = f"App-ID: {self.patient_id}"
        
        ext_id_text = ""
        if patient_data.get("external_id"):
            ext_id_text = f"Ext-ID: {patient_data['external_id']}\n"
        
        text = f"{name_display}\nBorn: {geb}\n{ext_id_text}{app_id}"
        
        self.setText(text)
        
        # # Base size
        self.setMinimumHeight(100)
        self.setMinimumWidth(300)
        
        # # Base font
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        # # Apply default styling (not selected)
        self._update_style()
        
        # === ITERATION 2.3: # Signal connection ===
        # # Dependency: Internal QPushButton signal "clicked"
        # # Connect Qt standard signal to custom handler
        # # How it works:
        # 1. # 1. User clicks button
        # 2. # 2. Qt emits clicked signal internally
        # 3. # 3. Our handler _on_click() is called
        # 4. # 4. _on_click() emits patient_clicked signal with ID
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
    patient_selected = Signal(int)
    
    def __init__(self):
        """
        # Initialize PatientListWidget
        
        Layout-Struktur:
        PatientListWidget (QWidget)
            └─ QVBoxLayout
                └─ QScrollArea
                    └─ Container (QWidget)
                        └─ QVBoxLayout
                            └─ [PatientButton, PatientButton, ...]
        """
        super().__init__()
        
        # === State-Management ===
        # # Stores currently selected patient
        self.selected_patient_id = None
        
        # # Dict for quick button lookup by patient ID
        # # Structure: {patient_id: PatientButton}
        self.patient_buttons: dict = {}
        
        # === # Layout setup ===
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === # ScrollArea for long patient lists ===
        # Dependency: PySide6.QtWidgets.QScrollArea
        # # Enables scrolling for many patients
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # === # Container for patient buttons ===
        # # Widget embedded in ScrollArea
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
    
    def remove_patient(self, patient_id: int) -> None:
        """
        # Remove patient from list
        
        # Process:
        1. # 1. Get button from dict
        2. # 2. Remove button from layout
        3. # 3. Delete button widget
        4. # 4. Remove from dict
        5. # 5. Deselect if was selected
        
        Args:
            patient_id: ID of patient to delete
        """
        if patient_id in self.patient_buttons:
            btn = self.patient_buttons[patient_id]
            # Entferne vom visuellen Layout
            self.container_layout.removeWidget(btn)
            # Lösche Qt-Widget
            btn.deleteLater()
            # # 4. Remove from dictionary
            del self.patient_buttons[patient_id]
            
            # Falls dieser Patient selektiert war, deselektiere
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
    
    def select_patient(self, patient_id: int) -> None:
        """
        # Select a patient in list
        
        # Process:
        1. # 1. If patient selected, deselect it (set_selected(False))
        2. # 2. Select new patient (set_selected(True))
        3. # 3. Store new selection
        4. # 4. Send patient_selected signal
        
        Args:
            patient_id: ID of patient to select
        """
        # # Deselect old selection
        if self.selected_patient_id and self.selected_patient_id in self.patient_buttons:
            self.patient_buttons[self.selected_patient_id].set_selected(False)
        
        # # 2. Select new patient
        if patient_id in self.patient_buttons:
            self.patient_buttons[patient_id].set_selected(True)
            self.selected_patient_id = patient_id
            
            # === # Send signal using emit() ===
            # Dependency: Signal.emit()
            # # Notify listeners that patient was selected
            self.patient_selected.emit(patient_id)
    
    def _on_patient_clicked(self, patient_id: int) -> None:
        """
        === ITERATION 2.4: # Patient click handler ===
        
        # Called when PatientButton is clicked
        (# via signal connection: btn.patient_clicked.connect())
        
        # Process:
        1. # 1. Call select_patient() to select patient
        2. # 2. select_patient() updates styling and emits signal
        
        Args:
            patient_id: ID des geklickten Patienten
        """
        self.select_patient(patient_id)


# === ITERATION 2.5: CreatePatientDialog ===
# Dependencies:
# - PySide6.QtWidgets: QDialog, QLineEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
# - PySide6.QtCore: Qt

class CreatePatientDialog(QDialog):
    """
    Iteration 2.5: # Modal dialog for creating new patient
    
    # Features:
    - # Modal dialog (blocks main window until closed)
    - # 3 input fields: First name, Last name, Birthdate (dd.mm.yyyy)
    - # Validation: Date format and required fields
    - # Returns Dict with patient data or None
    
    Usage:
        dialog = CreatePatientDialog(parent_widget)
        if dialog.exec() == QDialog.Accepted:
            patient_data = dialog.get_patient_data()
            if patient_data:
                # # Create patient with patient_data
    """
    
    def __init__(self, parent=None):
        """
        Initialisiert den CreatePatientDialog
        
        Args:
            parent: Parent widget (for modal behavior)
        """
        super().__init__(parent)
        
        # === # Dialog configuration ===
        self.setWindowTitle("Neuen Patienten erstellen")
        # setModal(True) makes dialog modal (blocks parent)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # === # Layout setup ===
        layout = QVBoxLayout()
        
        # --- # First name input ---
        layout.addWidget(QLabel("First name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Max")
        layout.addWidget(self.name_input)
        
        # --- # Last name input ---
        layout.addWidget(QLabel("Last name:"))
        self.nachname_input = QLineEdit()
        self.nachname_input.setPlaceholderText("e.g. Mustermann")
        layout.addWidget(self.nachname_input)
        
        # --- # Birthdate input ---
        layout.addWidget(QLabel("Geburtsdatum (dd.mm.yyyy):"))
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("e.g. 15.03.1990")
        layout.addWidget(self.date_input)
        
        # --- # Dialog buttons ---
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Erstellen")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_patient_data(self):
        """
        === ITERATION 2.5: # Data validation ===
        
        Gibt eingegebene Patientendaten zurück oder None bei Validierungsfehler.
        
        # Validation steps:
        1. # 1. Get input from QLineEdit fields
        2. # 2. Trim whitespace (.strip())
        3. # 3. Check if required fields are empty
        4. # 4. Validate date format (dd.mm.yyyy)
        5. # 5. Return Dict or None
        
        Dependencies:
        - QMessageBox for error output
        
        Returns:
            Dict with {first_name, last_name, birthdate} or None on error
        """
        # # Get and clean input
        name = self.name_input.text().strip()
        nachname = self.nachname_input.text().strip()
        geburtsdatum = self.date_input.text().strip()
        
        # # Validation: First name required
        if not name:
            QMessageBox.warning(self, "Error", "First name is required!")
            return None
        
        # Validierung: Nachname erforderlich
        if not nachname:
            QMessageBox.warning(self, "Error", "Last name is required!")
            return None
        
        # Validierung: Geburtsdatum erforderlich
        if not geburtsdatum:
            QMessageBox.warning(self, "Error", "Birthdate is required!")
            return None
        
        # === # Validate date format ===
        # Dependency: String.split()
        # # Check format: dd.mm.yyyy
        # Regeln:
        # - # Exactly 3 parts (separated by .)
        # - # Day: 2 digits (01-31)
        # - # Month: 2 digits (01-12)
        # - # Year: 4 digits (1900-2100)
        try:
            parts = geburtsdatum.split(".")
            # # Check structure
            if len(parts) != 3 or len(parts[0]) != 2 or len(parts[1]) != 2 or len(parts[2]) != 4:
                raise ValueError("# Wrong format")
            
            # # Check value ranges
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                raise ValueError("# Invalid values")
                
        except (ValueError, IndexError):
            QMessageBox.warning(self, "Error", "Invalid date format!\nPlease use: dd.mm.yyyy\n\nExample: 15.03.1990")
            return None
        
        # # All validations passed → return Dict
        return {
            "first_name": first_name,
            "last_name": last_name,
            "birthdate": birthdate
        }


class EditPatientDialog(QDialog):
    """
    Iteration 3_1: # Dialog for editing patient
    Like CreatePatientDialog but shows existing data und and uses same error messages
    """
    def __init__(self, parent=None, patient_data = None):
        super().__init__(parent)

        self.setWindowTitle("Edit patient")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("First name:"))
        self.name_input = QLineEdit()
        self.name_input.setText(patient_data.get("first_name", "") if patient_data else "")
        layout.addWidget(self.name_input)

        
        layout.addWidget(QLabel("Last name:"))
        self.nachname_input = QLineEdit()
        self.nachname_input.setText(patient_data.get("last_name", "") if patient_data else "")
        layout.addWidget(self.nachname_input)
        
        layout.addWidget(QLabel("Birthdate (dd.mm.yyyy):"))
        self.date_input = QLineEdit()
        self.date_input.setText(patient_data.get("birthdate", "") if patient_data else "")
        layout.addWidget(self.date_input)

        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn= QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_patient_data(self):
        """# Validate and return updated patient data (wie CreatePatientDialog)"""
        name = self.name_input.text().strip()
        nachname = self.nachname_input.text().strip()
        geburtsdatum = self.date_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "First name is required!")
            return None

        if not nachname:
            QMessageBox.warning(self, "Error", "Last name is required!")
            return None

        if not geburtsdatum:
            QMessageBox.warning(self, "Error", "Birthdate is required!")
            return None

        try:
            parts = geburtsdatum.split(".")
            if len(parts) != 3 or len(parts[0]) != 2 or len(parts[1]) != 2 or len(parts[2]) != 4:
                raise ValueError("# Wrong format")

            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                raise ValueError("# Invalid values")

        except (ValueError, IndexError):
            QMessageBox.warning(self, "Error", "Invalid date format!\nPlease use: dd.mm.yyyy\n\nExample: 15.03.1990")
            return None

        return {
            "first_name": first_name,
            "last_name": last_name,
            "birthdate": birthdate
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
