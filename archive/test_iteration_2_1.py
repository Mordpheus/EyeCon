"""Test-Skript für Iteration 2.1 & 2.2 & 2.3: PatientButton Basics + Styling + Signals"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from patient_widgets import PatientButton

print("=== Iteration 2.1 & 2.2 & 2.3: PatientButton Struktur + Styling + Signals-Test ===\n")

app = QApplication(sys.argv)

# Test: Erstelle zwei PatientButtons
test_patients = [
    {
        'id': 1,
        'name': 'Max',
        'nachname': 'Mustermann',
        'geburtsdatum': '15.03.1990',
        'ext_id': None
    },
    {
        'id': 2,
        'name': 'Anna',
        'nachname': 'Schmidt',
        'geburtsdatum': '22.07.1985',
        'ext_id': 'SMH-2024-001'
    }
]

window = QWidget()
window.setWindowTitle("Iteration 2.3: PatientButton Signals Test")
layout = QVBoxLayout()

# Label für Signal-Ausgaben
signal_label = QLabel("Warte auf Klicks...")
signal_label.setStyleSheet("background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
layout.addWidget(signal_label)

buttons = []
for patient_data in test_patients:
    btn = PatientButton(patient_data)
    buttons.append(btn)
    layout.addWidget(btn)
    print(f"✓ PatientButton erstellt für: {patient_data['nachname']}, {patient_data['name']}")

print("\n--- Styling Test ---")
print("✓ Button 1 (Mustermann): Standard (nicht selektiert) = Grau")
buttons[0].set_selected(False)

print("✓ Button 2 (Schmidt): Selektiert = Grün")
buttons[1].set_selected(True)

print("\n--- Signal Test ---")
print("✓ Signal-Verbindungen eingerichtet")

# === ITERATION 2.3: Signal-Handler Setup ===
# Dependency: Signal-Verbindung (connect)
# Verbinde patient_clicked Signals mit Test-Handler
def on_button_clicked(patient_id: int):
    """Handler wenn ein PatientButton geklickt wird"""
    message = f"Signal empfangen: Patient-ID {patient_id} geklickt!"
    print(f"  → {message}")
    signal_label.setText(message)

for btn in buttons:
    # === ITERATION 2.3: Signal-Listener ===
    # Dependency: Signal.connect() Methode
    # Verbinde Custom Signal patient_clicked mit Handler
    btn.patient_clicked.connect(on_button_clicked)
    print(f"  ✓ patient_clicked Signal für Patient {btn.patient_id} verbunden")

print("\n✓ Fenster wird angezeigt mit Styling und Signals.")
print("  - Klicke auf einen Button um das Signal zu testen")
print("  - Die Signal-Ausgabe wird im Label oben angezeigt\n")

window.setLayout(layout)
window.resize(400, 350)
window.show()

sys.exit(app.exec())
