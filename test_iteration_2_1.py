"""Test-Skript für Iteration 2.1 & 2.2: PatientButton Basics + Styling"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from patient_widgets import PatientButton

print("=== Iteration 2.1 & 2.2: PatientButton Struktur + Styling-Test ===\n")

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
window.setWindowTitle("Iteration 2.2: PatientButton Styling Test")
layout = QVBoxLayout()

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

print("\n✓ Fenster wird angezeigt mit Styling.")
print("  - Graue Button = nicht selektiert")
print("  - Grüne Button = selektiert")
print("  - Hover-Effekt beim Überfahren mit Maus\n")

window.setLayout(layout)
window.show()

sys.exit(app.exec())
