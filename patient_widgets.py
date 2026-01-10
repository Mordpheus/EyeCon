"""
Patient-spezifische UI-Widgets für das Dashboard
Iteration 2: UI-Komponenten
"""
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import Dict, Any


class PatientButton(QPushButton):
    """
    Iteration 2.1: PatientButton - Grundstruktur
    
    Anklickbarer Button mit Patientendaten.
    Zeigt Name, Nachname, Geburtsdatum und IDs an.
    """
    
    def __init__(self, patient_data: Dict[str, Any]):
        """
        Initialisiert einen PatientButton
        
        Args:
            patient_data: Dict mit id, name, nachname, geburtsdatum, ext_id
        """
        super().__init__()
        
        self.patient_id = patient_data["id"]
        self.patient_data = patient_data
        
        # Für die Suchfunktion und Standardisierung lieber den Nachnamen zuerst anzeigen
        name_display = f"{patient_data['nachname']}, {patient_data['name']}"
        geb = patient_data["geburtsdatum"]
        app_id = f"App-ID: {self.patient_id}"
        
        ext_id_text = ""
        if patient_data.get("ext_id"):
            ext_id_text = f"Ext-ID: {patient_data['ext_id']}\n"
        
        text = f"{name_display}\nGeboren: {geb}\n{ext_id_text}{app_id}"
        
        self.setText(text)
        
        # Basis-Größe
        self.setMinimumHeight(100)
        self.setMinimumWidth(300)
        
        # Basis-Font
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
