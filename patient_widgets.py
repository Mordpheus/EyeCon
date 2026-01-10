"""
Patient-spezifische UI-Widgets für das Dashboard
Iteration 2: UI-Komponenten

Dependencies:
- PySide6.QtWidgets: QPushButton, QWidget, QVBoxLayout, QScrollArea, QDialog, QLineEdit, QMessageBox
- PySide6.QtCore: Qt, Signal
- PySide6.QtGui: QFont, QColor
"""
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Dict, Any


class PatientButton(QPushButton):
    """
    Iteration 2.1: PatientButton - Grundstruktur
    Iteration 2.2: PatientButton - Styling & Layout
    Iteration 2.3: PatientButton - Signals & Click-Interaktion
    
    Anklickbarer Button mit Patientendaten.
    Zeigt Name, Nachname, Geburtsdatum und IDs an.
    Mit Styling: Grün wenn selektiert, Grau sonst.
    Emittiert Signal bei Klick für externe Verarbeitung.
    """
    
    # === ITERATION 2.3: Custom Signal Definition ===
    # Dependency: PySide6.QtCore.Signal
    # Dieses Signal wird emittiert, wenn der Button geklickt wird
    # Parameter: int = Patient-ID des geklickten Buttons
    # Verwendung: Andere Komponenten können sich darauf verbinden:
    #   button.patient_clicked.connect(meine_handler_funktion)
    patient_clicked = Signal(int)
    
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
        
        # === ITERATION 2.3: Signal-Verbindung ===
        # Dependency: Interner QPushButton-Signal "clicked"
        # Verbinde Qt-Standard-Signal "clicked" mit eigenem Handler
        # Funktionsweise:
        # 1. Nutzer klickt auf Button
        # 2. Qt emittiert intern clicked-Signal (ohne Parameter)
        # 3. Unser Handler _on_click() wird aufgerufen
        # 4. _on_click() emittiert dann unser Custom-Signal patient_clicked(int)
        self.clicked.connect(self._on_click)
    
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
    
    def _on_click(self) -> None:
        """
        === ITERATION 2.3: Click-Handler ===
        
        Dependency: Interner QPushButton clicked-Signal
        
        Wird aufgerufen wenn der Button geklickt wird.
        Emittiert das Custom-Signal patient_clicked mit der Patient-ID.
        
        Signal-Flow:
        1. Nutzer klickt Button
        2. Qt emittiert QPushButton.clicked() (kein Parameter)
        3. Verbundener Handler _on_click() wird aufgerufen
        4. _on_click() emittiert patient_clicked(int) mit self.patient_id
        5. Listener des patient_clicked Signals werden benachrichtigt
        
        Beispiel-Verwendung in PatientListWidget:
            btn.patient_clicked.connect(self._on_patient_clicked)
        """
        self.patient_clicked.emit(self.patient_id)
