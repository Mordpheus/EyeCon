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
    Iteration 2.2: PatientButton - Styling & Layout
    
    Anklickbarer Button mit Patientendaten.
    Zeigt Name, Nachname, Geburtsdatum und IDs an.
    Mit Styling: Grün wenn selektiert, Grau sonst.
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
        self.is_selected = False
        
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
        
        # Wende Standard-Styling an (nicht selektiert)
        self._update_style()
    
    def _update_style(self) -> None:
        """
        Iteration 2.2: Aktualisiert Button-Stil basierend auf Selektionsstatus
        
        Aktuelle Implementierung: Vollständige Hintergrund-Färbung
        - Grün (#4CAF50) Hintergrund wenn selektiert
        - Grau (#f5f5f5) Hintergrund wenn nicht selektiert
        
        Alternative (auskommentiert): Nur Border-Highlighting
        - Grüner Border (3px) wenn selektiert
        - Grauer Border (1px) wenn nicht selektiert
        - Hintergrund bleibt weiß
        """
        if self.is_selected:
            # === AKTUELLE IMPLEMENTIERUNG: Vollständige Hintergrund-Färbung ===
            bg_color = "#4CAF50"  # Grün
            text_color = "white"
            border = "2px solid #2E7D32"  # Dunkelgrün
            
            # === ALTERNATIVE: Nur Border-Highlighting (auskommentiert) ===
            # bg_color = "white"  # Weißer Hintergrund
            # text_color = "#333333"  # Dunkelgrau Text
            # border = "3px solid #4CAF50"  # Grüner Border für Highlight
        else:
            # === AKTUELLE IMPLEMENTIERUNG: Graue Hintergrund ===
            bg_color = "#f5f5f5"  # Hellgrau
            text_color = "#333333"  # Dunkelgrau
            border = "1px solid #cccccc"  # Hellgrau Border
            
            # === ALTERNATIVE: Weißer Hintergrund mit dünnem Border ===
            # bg_color = "white"  # Weißer Hintergrund
            # text_color = "#333333"  # Dunkelgrau Text
            # border = "1px solid #cccccc"  # Feiner grauer Border
        
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
        Setzt Selektionsstatus und aktualisiert Styling
        
        Args:
            selected: True = selektiert (grün), False = nicht selektiert (grau)
        """
        self.is_selected = selected
        self._update_style()
