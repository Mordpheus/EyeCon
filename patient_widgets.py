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
    Iteration 2.1: PatientButton – Grundstruktur
    Iteration 2.2: PatientButton – Styling & Layout
    Iteration 2.3: PatientButton – Signals & Click-Interaktion
    
    Anklickbarer Button mit Patientendaten.
    Zeigt Name, Nachname, Geburtsdatum und IDs an.
    Mit Styling: Grün wenn selektiert, Grau sonst.
    Sendet Signal bei Klick für externe Verarbeitung.
    """
    
    # === ITERATION 2.3: Custom Signal Definition ===
    # Dependency: PySide6.QtCore.Signal
    # Dieses Signal wird gesendet, wenn der Button geklickt wird
    # Parameter: int = Patient-ID des geklickten Buttons
    # Verwendung: Andere Komponenten können sich darauf verbinden:
    #   button.patient_clicked.connect(meine_handler_funktion)
    patient_clicked = Signal(int)
    
    def __init__(self, patient_data: Dict[str, Any]):
        """
        Initialisiert einen PatientButton
        
        Args:
            patient_data: speichern in eibem Dict mit id, name, nachname, geburtsdatum, ext_id
        """
        super().__init__()
        
        self.patient_id = patient_data["id"]
        self.patient_data = patient_data
        self.is_selected = False
        
        # Für die Suchfunktion und Standardisierung lieber den Nachnamen zuerst anzeigen (nicht wie in Formularen)
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
        # 2. Qt sendet intern clicked-Signal (ohne Parameter)
        # 3. Unser Handler _on_click() wird aufgerufen
        # 4. _on_click() sendet dann unser Custom-Signal patient_clicked(int)
        self.clicked.connect(self._on_click)
    
    def _update_style(self) -> None:
        """
        Iteration 2.2: Aktualisiert Button-Stil basierend auf Selektionsstatus
        
        Aktuelle Implementierung: Vollständige Hintergrund-Färbung (ggf. nur Ränder färben?)
        - Grün (Farbcode: #4CAF50) Hintergrund wenn selektiert
        - Grau (Farbcode: #f5f5f5) Hintergrund wenn nicht selektiert
        
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
        Sendet das Custom-Signal patient_clicked mit der Patient-ID.
        
        Signal-Flow: Kombination aus handler und onClick Listener, wie in anderen Sprachen üblich.
        Ablauf:
        1. Nutzer klickt Button
        2. Qt sendet QPushButton.clicked() (kein Parameter)
        3. Verbundener Handler _on_click() wird aufgerufen
        4. _on_click() sendet patient_clicked(int) mit self.patient_id
        5. Listener des patient_clicked Signals werden benachrichtigt
        
        Beispiel-Verwendung in PatientListWidget:
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
    Iteration 2.4: PatientListWidget – Container für Patient-Buttons
    
    Verwaltet eine scrollbare Liste von PatientButtons.
    Funktionen:
    - Anzeige mehrerer PatientButtons mit Scroll-Funktion
    - Selektions-Verwaltung (nur ein Patient aktiv zur Zeit)
    - Signal-Weiterleitung: Emittiert patient_selected Signal
    
    Signal-Architektur:
    PatientButton.patient_clicked → PatientListWidget._on_patient_clicked → PatientListWidget.patient_selected
    """
    
    # === ITERATION 2.4: Patient-Auswahl Signal ===
    # Dependency: PySide6.QtCore.Signal
    # Emittiert wenn Nutzer einen Patient aus der Liste auswählt
    # Parameter: int = Patient-ID
    # Diese Signal wird von höheren Komponenten (z.B. CenterArea) empfangen
    patient_selected = Signal(int)
    
    def __init__(self):
        """
        Initialisiert das PatientListWidget
        
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
        # Speichert derzeit selektierten Patient
        self.selected_patient_id = None
        
        # Dictionary zur schnellen Button-Referenzierung nach Patient-ID
        # Struktur: {patient_id: PatientButton}
        self.patient_buttons: dict = {}
        
        # === Layout-Aufbau ===
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === ScrollArea für lange Patient-Listen ===
        # Dependency: PySide6.QtWidgets.QScrollArea
        # Ermöglicht Scrolling wenn zu viele Patienten vorhanden sind
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # === Container für Patient-Buttons ===
        # Ist das Widget das in ScrollArea eingebettet wird
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(10)
        self.container.setLayout(self.container_layout)
        
        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
    
    def add_patient(self, patient_data: Dict[str, Any]) -> None:
        """
        Fügt einen Patienten zur Liste hinzu
        
        Prozess:
        1. Erstelle neuen PatientButton mit Patientendaten
        2. Verbinde PatientButton.patient_clicked Signal mit eigenem Handler
        3. Speichere Button-Referenz im patient_buttons Dict
        4. Füge Button zu Container-Layout hinzu
        
        Args:
            patient_data: Dict mit Patient-Informationen
        """
        # Erstelle neuen Button
        btn = PatientButton(patient_data)
        
        # === Signal-Verbindung ===
        # Dependency: Signal.connect()
        # Wenn PatientButton geklickt wird, handler _on_patient_clicked aufrufen
        btn.patient_clicked.connect(self._on_patient_clicked)
        
        # Speichere Referenz
        self.patient_buttons[patient_data["id"]] = btn
        
        # Füge zu Layout hinzu (zeige den Button)
        self.container_layout.addWidget(btn)
    
    def remove_patient(self, patient_id: int) -> None:
        """
        Entfernt einen Patienten aus der Liste
        
        Prozess:
        1. Hole Button aus Dict
        2. Entferne Button vom Layout
        3. Lösche Button-Widget
        4. Entferne aus Dict
        5. Falls Patient selektiert war, deselektiere
        
        Args:
            patient_id: ID des zu löschenden Patienten
        """
        if patient_id in self.patient_buttons:
            btn = self.patient_buttons[patient_id]
            # Entferne vom visuellen Layout
            self.container_layout.removeWidget(btn)
            # Lösche Qt-Widget
            btn.deleteLater()
            # Entferne aus Dictionary
            del self.patient_buttons[patient_id]
            
            # Falls dieser Patient selektiert war, deselektiere
            if self.selected_patient_id == patient_id:
                self.selected_patient_id = None
    
    def clear_patients(self) -> None:
        """
        Entfernt alle Patienten aus der Liste
        
        Prozess:
        1. Iteriere über alle Buttons
        2. Entferne jeden Button vom Layout
        3. Lösche Button-Widget
        4. Leere das Dictionary
        5. Setze Selektion auf None
        """
        for btn in self.patient_buttons.values():
            self.container_layout.removeWidget(btn)
            btn.deleteLater()
        self.patient_buttons.clear()
        self.selected_patient_id = None
    
    def select_patient(self, patient_id: int) -> None:
        """
        Selektiert einen Patienten in der Liste
        
        Prozess:
        1. Wenn bereits Patient selektiert: deselektiere ihn (set_selected(False))
        2. Selektiere neuen Patient (set_selected(True))
        3. Speichere neue Selektion in selected_patient_id
        4. Sende patient_selected Signal
        
        Args:
            patient_id: ID des zu selektierenden Patienten
        """
        # Deselektiere alte Auswahl
        if self.selected_patient_id and self.selected_patient_id in self.patient_buttons:
            self.patient_buttons[self.selected_patient_id].set_selected(False)
        
        # Selektiere neuen Patient
        if patient_id in self.patient_buttons:
            self.patient_buttons[patient_id].set_selected(True)
            self.selected_patient_id = patient_id
            
            # === Signal-Senden durch emit() Funktion ===
            # Dependency: Signal.emit()
            # Benachrichtige Listener dass Patient ausgewählt wurde
            self.patient_selected.emit(patient_id)
    
    def _on_patient_clicked(self, patient_id: int) -> None:
        """
        === ITERATION 2.4: Patient-Click Handler ===
        
        Wird aufgerufen wenn ein PatientButton geklickt wird
        (über Signal-Verbindung: btn.patient_clicked.connect())
        
        Prozess:
        1. Rufe select_patient() auf um Patient zu selektieren
        2. select_patient() macht das Styling-Update und emittiert Signal
        
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
    Iteration 2.5: CreatePatientDialog – Modal Dialog zur Patient-Erstellung
    
    Funktionen:
    - Ich bin ein Modal Dialog (blockiere Hauptfenster bis geschlossen)
    - 3 Input-Felder: Vorname, Nachname, Geburtsdatum (dd.mm.yyyy)
    - Ich validiere Datumsformat und erforderliche Felder
    - Ich gebe Dict mit Patientendaten oder None zurück
    
    Usage:
        dialog = CreatePatientDialog(parent_widget)
        if dialog.exec() == QDialog.Accepted:
            patient_data = dialog.get_patient_data()
            if patient_data:
                # Patient erstellen mit patient_data
    """
    
    def __init__(self, parent=None):
        """
        Initialisiert den CreatePatientDialog
        
        Args:
            parent: Parent-Widget (für Modal-Verhalten)
        """
        super().__init__(parent)
        
        # === Dialog-Konfiguration ===
        self.setWindowTitle("Neuen Patienten erstellen")
        # setModal(True) macht Dialog modal (blockiert Parent)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        # === Layout-Aufbau ===
        layout = QVBoxLayout()
        
        # --- Vorname Input ---
        layout.addWidget(QLabel("Vorname:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z.B. Max")
        layout.addWidget(self.name_input)
        
        # --- Nachname Input ---
        layout.addWidget(QLabel("Nachname:"))
        self.nachname_input = QLineEdit()
        self.nachname_input.setPlaceholderText("z.B. Mustermann")
        layout.addWidget(self.nachname_input)
        
        # --- Geburtsdatum Input ---
        layout.addWidget(QLabel("Geburtsdatum (dd.mm.yyyy):"))
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("z.B. 15.03.1990")
        layout.addWidget(self.date_input)
        
        # --- Dialog-Buttons ---
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("Erstellen")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_patient_data(self):
        """
        === ITERATION 2.5: Daten-Validierung ===
        
        Gibt eingegebene Patientendaten zurück oder None bei Validierungsfehler.
        
        Validierungsschritte:
        1. Hole Eingaben aus QLineEdit Feldern
        2. Trim Whitespace (.strip())
        3. Prüfe ob erforderliche Felder leer sind
        4. Validiere Datumsformat (dd.mm.yyyy)
        5. Gebe Dict zurück oder None
        
        Dependencies:
        - QMessageBox: Für Fehlerausgaben
        
        Returns:
            Dict mit {name, nachname, geburtsdatum} oder None bei Fehler
        """
        # Hole und bereinige Eingaben
        name = self.name_input.text().strip()
        nachname = self.nachname_input.text().strip()
        geburtsdatum = self.date_input.text().strip()
        
        # Validierung: Vorname erforderlich
        if not name:
            QMessageBox.warning(self, "Fehler", "Vorname ist erforderlich!")
            return None
        
        # Validierung: Nachname erforderlich
        if not nachname:
            QMessageBox.warning(self, "Fehler", "Nachname ist erforderlich!")
            return None
        
        # Validierung: Geburtsdatum erforderlich
        if not geburtsdatum:
            QMessageBox.warning(self, "Fehler", "Geburtsdatum ist erforderlich!")
            return None
        
        # === Datumsformat-Validierung ===
        # Dependency: String.split()
        # Format prüfen: dd.mm.yyyy
        # Regeln:
        # - Genau 3 Teile (separiert durch .)
        # - Tag: 2 Ziffern (01-31)
        # - Monat: 2 Ziffern (01-12)
        # - Jahr: 4 Ziffern (1900-2100)
        try:
            parts = geburtsdatum.split(".")
            # Prüfe Struktur
            if len(parts) != 3 or len(parts[0]) != 2 or len(parts[1]) != 2 or len(parts[2]) != 4:
                raise ValueError("Falsches Format")
            
            # Prüfe Wertebereiche
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                raise ValueError("Ungültige Werte")
                
        except (ValueError, IndexError):
            QMessageBox.warning(self, "Fehler", "Ungültiges Datumsformat!\nBitte verwenden Sie: dd.mm.yyyy\n\nBeispiel: 15.03.1990")
            return None
        
        # Alle Validierungen bestanden → gebe Dict zurück
        return {
            "name": name,
            "nachname": nachname,
            "geburtsdatum": geburtsdatum
        }


class EditPatientDialog(QDialog):
    """
    Iteration 3.1: EditPatientDialog – Dialog zur Patient-Bearbeitung
    Ich funktioniere wie CreatePatientDialog, aber ich zeige bestehende Daten an und verwende dieselben Fehlermeldungen
    """
    def __init__(self, parent=None, patient_data = None):
        super().__init__(parent)

        self.setWindowTitle("Patienten bearbeiten")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Vorname:"))
        self.name_input = QLineEdit()
        self.name_input.setText(patient_data.get("name", "") if patient_data else "")
        layout.addWidget(self.name_input)

        
        layout.addWidget(QLabel("Nachname:"))
        self.nachname_input = QLineEdit()
        self.nachname_input.setText(patient_data.get("nachname", "") if patient_data else "")
        layout.addWidget(self.nachname_input)
        
        layout.addWidget(QLabel("Geburtsdatum(dd.mm.jjjj):"))
        self.date_input = QLineEdit()
        self.date_input.setText(patient_data.get("geburtsdatum", "") if patient_data else "")
        layout.addWidget(self.date_input)

        button_layout = QHBoxLayout()

        save_btn = QPushButton("Speichern")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn= QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_patient_data(self):
        """Validiert und gibt aktualisierte Patientendaten zurück (wie CreatePatientDialog)"""
        name = self.name_input.text().strip()
        nachname = self.nachname_input.text().strip()
        geburtsdatum = self.date_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Fehler", "Vorname ist erforderlich!")
            return None

        if not nachname:
            QMessageBox.warning(self, "Fehler", "Nachname ist erforderlich!")
            return None

        if not geburtsdatum:
            QMessageBox.warning(self, "Fehler", "Geburtsdatum ist erforderlich!")
            return None

        try:
            parts = geburtsdatum.split(".")
            if len(parts) != 3 or len(parts[0]) != 2 or len(parts[1]) != 2 or len(parts[2]) != 4:
                raise ValueError("Falsches Format")

            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                raise ValueError("Ungültige Werte")

        except (ValueError, IndexError):
            QMessageBox.warning(self, "Fehler", "Ungültiges Datumsformat!\nBitte verwenden Sie: dd.mm.yyyy\n\nBeispiel: 15.03.1990")
            return None

        return {
            "name": name,
            "nachname": nachname,
            "geburtsdatum": geburtsdatum
        } 


class DeleteConfirmDialog(QDialog):
    """
    Iteration 3.3: DeleteConfirmDialog – Bestätigungs-Dialog zum Löschen eines Patienten
    
    Ich stelle eine einfache Ja/Nein-Abfrage mit klarer Formulierung bereit.
    Dependencies:
    - QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
    """
    def __init__(self, parent=None, patient_name: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Löschen bestätigen")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout()

        # Frage-Text: optional mit Patientennamen?
        text = "Patienten wirklich löschen?"
        if patient_name:
            text = f"Patient '{patient_name}' wirklich löschen?"
        label = QLabel(text)
        layout.addWidget(label)

        # Buttons: Ja / Nein
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
        """Ich öffne den Dialog modal und gebe True bei 'Ja', sonst False zurück."""
        return self.exec() == QDialog.Accepted
