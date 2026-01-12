"""
Einfacher Platzhalter-Dialog für Patienten (deutsch).

Der Dialog enthält aktuell keine echte Logik; er dient nur als
Strukturplatzhalter, damit spätere Implementierungen an dieser Stelle
anknüpfen können.
"""

from PySide6.QtWidgets import QDialog


class PatientenDialog(QDialog):
    """Minimaler Dialog, derzeit ohne funktionale Elemente."""

    def __init__(self, datenbank=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patienten (Platzhalter)")
        self.resize(400, 200)

    def get_auswahl(self):
        """Gibt aktuell keine Auswahl zurück (Platzhalter)."""
        return None
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox
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
