"""Test-Skript für Iteration 2.5: CreatePatientDialog"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from patient_widgets import CreatePatientDialog

print("=== Iteration 2.5: CreatePatientDialog Test ===\n")

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("Iteration 2.5: CreatePatientDialog Test")
layout = QVBoxLayout()

# Info-Label
info_label = QLabel("Klicke auf 'Dialog öffnen' um CreatePatientDialog zu testen")
info_label.setStyleSheet("background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
layout.addWidget(info_label)

# Result-Label
result_label = QLabel("")
result_label.setStyleSheet("background-color: #1f2937; color: white; padding: 10px; border-radius: 5px; min-height: 80px;")
layout.addWidget(result_label)

# === ITERATION 2.5: Dialog Button ===
# Dependency: QPushButton.clicked.connect()
def open_dialog():
    """Handler für Dialog öffnen"""
    print("\n✓ CreatePatientDialog wird geöffnet...")
    
    # Erstelle Dialog (modal)
    dialog = CreatePatientDialog(window)
    
    # Zeige Dialog und warte auf Ergebnis
    # exec() blockiert bis Dialog geschlossen wird
    dialog_result = dialog.exec()
    
    if dialog_result == CreatePatientDialog.Accepted:
        print("  → Dialog: Nutzer hat 'Erstellen' geklickt")
        
        # === ITERATION 2.5: Daten-Validierung ===
        # Dependency: get_patient_data() Methode
        # Führt Validierung durch, gibt Dict oder None zurück
        patient_data = dialog.get_patient_data()
        
        if patient_data:
            print("  → Validierung erfolgreich!")
            result_text = f"""✓ Patient erstellt:
Name: {patient_data['name']}
Nachname: {patient_data['nachname']}
Geburtsdatum: {patient_data['geburtsdatum']}

Diese Daten würden jetzt in die Datenbank gespeichert."""
            result_label.setText(result_text)
            print(f"  → {result_text.replace(chr(10), ' | ')}")
        else:
            print("  → Validierung fehlgeschlagen!")
            result_label.setText("✗ Validierung fehlgeschlagen (siehe Fehlerdialog)")
    else:
        print("  → Dialog: Nutzer hat 'Abbrechen' geklickt")
        result_label.setText("Dialog wurde abgebrochen")

open_btn = QPushButton("Dialog öffnen")
open_btn.clicked.connect(open_dialog)
layout.addWidget(open_btn)

# === Test-Hinweise ===
hints = QLabel("""Test-Anleitung:
1. Klicke 'Dialog öffnen'
2. Teste Validierung:
   - Leere Felder → Fehlermeldung
   - Falsches Datumsformat (z.B. '15-03-1990') → Fehlermeldung
   - Richtiges Format (z.B. '15.03.1990') → Erfolgreich
3. Beispiel-Daten:
   Name: Max
   Nachname: Mustermann
   Geburtsdatum: 15.03.1990
""")
hints.setStyleSheet("background-color: #e8f5e9; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 9pt;")
layout.addWidget(hints)

window.setLayout(layout)
window.resize(500, 450)
window.show()

print("✓ Fenster angezeigt. Dialog-Tests verfügbar.\n")

sys.exit(app.exec())
