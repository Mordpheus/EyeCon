from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QGridLayout
)
from PySide6.QtCore import Qt


class PatientsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Patientenverwaltung")
        self.resize(600, 400)

        # Hier speichern wir die ID des ausgewählten Patienten
        self.selected_patient_id = None

        # ------------------- Layout-Struktur -------------------
        main_layout = QVBoxLayout(self)

        # Tabelle zur Anzeige der Patienten
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Vorname", "Nachname", "Geburtsdatum"])
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        main_layout.addWidget(self.table)

        # Steuerungs-Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Abbrechen")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # Aktionen verbinden
        self.ok_btn.clicked.connect(self.accept_selection)
        self.cancel_btn.clicked.connect(self.reject)

        # Patientenliste aus Datenbank laden
        self.load_patients()


    # ------------------- Patienten laden -------------------

    def load_patients(self):
        """Lädt alle Patienten aus der Datenbank in die Tabelle."""
        patients = self.db.list_patients()
        self.table.setRowCount(len(patients))

        for row, p in enumerate(patients):
            id_, _, first, last, birth, _ = p
            self.table.setItem(row, 0, QTableWidgetItem(str(id_)))
            self.table.setItem(row, 1, QTableWidgetItem(first or ""))
            self.table.setItem(row, 2, QTableWidgetItem(last or ""))
            self.table.setItem(row, 3, QTableWidgetItem(birth or ""))


    # ------------------- Auswahl bestätigen -------------------

    def accept_selection(self):
        """Wird aufgerufen, wenn 'OK' gedrückt wird."""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wähle einen Patienten aus.")
            return

        # Die erste Spalte (ID) im markierten Datensatz enthält die Patienten-ID
        row = self.table.currentRow()
        self.selected_patient_id = int(self.table.item(row, 0).text())

        # Dialog schließen und Ergebnis als 'Accepted' markieren
        self.accept()


    # ------------------- Rückgabe an das Hauptfenster -------------------

    def get_selected_patient_id(self):
        """
        Gibt die ID des ausgewählten Patienten zurück,
        oder None, falls keiner gewählt wurde.
        """
        return self.selected_patient_id


class DuplicatePatientDialog(QDialog):
    """
    Dialog for handling duplicate patient detection during TBI import.
    
    Presents existing patient and TBI import data side-by-side with three options:
    - Merge: Use existing patient, import only new recordings
    - Skip: Skip this patient, continue with remaining import
    - Cancel: Cancel the entire import process
    """
    
    # Dialog result codes
    MERGE = 1
    SKIP = 2
    CANCEL = 3
    
    def __init__(self, existing_patient: dict, tbi_patient: dict, parent=None):
        super().__init__(parent)
        self.existing_patient = existing_patient
        self.tbi_patient = tbi_patient
        self.decision = None
        
        self.setWindowTitle("Duplikat erkannt - Import-Entscheidung")
        self.resize(700, 450)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Build dialog UI with patient data and action buttons."""
        main_layout = QVBoxLayout(self)
        
        # Header label
        header = QLabel("Ein Patient mit diesem Namen ist schon vorhanden:")
        main_layout.addWidget(header)
        
        # Comparison grid: existing vs TBI data
        grid = QGridLayout()
        
        # Column headers
        grid.addWidget(QLabel("<b>System</b>"), 0, 0)
        grid.addWidget(QLabel("<b>TBI-Import</b>"), 0, 1)
        
        # Patient data rows
        existing_id = self.existing_patient.get('id', 'N/A')
        tbi_id = self.tbi_patient.get('id', 'N/A')
        
        grid.addWidget(QLabel(f"<b>ID:</b> {existing_id}"), 1, 0)
        grid.addWidget(QLabel(f"<b>ID:</b> {tbi_id}"), 1, 1)
        
        existing_name = f"{self.existing_patient.get('first_name', '')} {self.existing_patient.get('last_name', '')}".strip()
        # TBI uses patient ID as the name
        tbi_name = str(tbi_id)
        
        grid.addWidget(QLabel(f"Name: {existing_name}"), 2, 0)
        grid.addWidget(QLabel(f"Name: {tbi_name}"), 2, 1)
        
        existing_birth = self.existing_patient.get('birthdate', 'N/A')
        tbi_birth = self.tbi_patient.get('birthdate') or 'N/A'
        
        grid.addWidget(QLabel(f"Geburtsdatum: {existing_birth}"), 3, 0)
        grid.addWidget(QLabel(f"Geburtsdatum: {tbi_birth}"), 3, 1)
        
        existing_sex = self.existing_patient.get('sex', 'N/A')
        tbi_sex = self.tbi_patient.get('sex') or 'N/A'
        
        grid.addWidget(QLabel(f"Geschlecht: {existing_sex}"), 4, 0)
        grid.addWidget(QLabel(f"Geschlecht: {tbi_sex}"), 4, 1)
        
        main_layout.addLayout(grid)
        
        # Separator and option descriptions (each on its own line)
        main_layout.addSpacing(20)
        main_layout.addWidget(QLabel("<b>Optionen:</b>"))
        
        merge_desc = QLabel(
            "  <b>Ja, Merge:</b> Bestehenden Patienten verwenden, "
            "nur neue Aufnahmen importieren"
        )
        skip_desc = QLabel(
            "  <b>Nein:</b> Diesen Patienten \u00fcberspringen, "
            "mit Import fortfahren"
        )
        cancel_desc = QLabel(
            "  <b>Abbrechen:</b> Gesamten Import abbrechen"
        )
        
        main_layout.addWidget(merge_desc)
        main_layout.addWidget(skip_desc)
        main_layout.addWidget(cancel_desc)
        
        main_layout.addSpacing(10)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        merge_btn = QPushButton("Ja, Merge")
        merge_btn.clicked.connect(self._on_merge)
        btn_layout.addWidget(merge_btn)
        
        skip_btn = QPushButton("Nein")
        skip_btn.clicked.connect(self._on_skip)
        btn_layout.addWidget(skip_btn)
        
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)
    
    def _on_merge(self) -> None:
        """User chose to merge with existing patient."""
        self.decision = 'merge'
        self.accept()
    
    def _on_skip(self) -> None:
        """User chose to skip this patient and continue import."""
        self.decision = 'skip'
        self.accept()
    
    def _on_cancel(self) -> None:
        """User chose to cancel the entire import."""
        self.decision = 'cancel'
        self.reject()
    
    def get_decision(self) -> str:
        """
        Returns the user's decision after dialog execution.
        
        Returns:
            'merge': Use existing patient, import new recordings only
            'skip': Skip this patient, continue with import
            'cancel': Cancel entire import process
        """
        return self.decision if self.decision else 'cancel'
