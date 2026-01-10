"""Test-Skript für Iteration 2.1: PatientButton Grundstruktur"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from patient_widgets import PatientButton

print("=== Iteration 2.1: PatientButton Grundstruktur-Test ===\n")

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
window.setWindowTitle("Iteration 2.1: PatientButton Test")
layout = QVBoxLayout()

for patient_data in test_patients:
    btn = PatientButton(patient_data)
    layout.addWidget(btn)
    print(f"✓ PatientButton erstellt für: {patient_data['nachname']}, {patient_data['name']}")

window.setLayout(layout)
window.show()

print("\n✓ Fenster angezeigt. (Zum Schließen Fenster schließen)")
sys.exit(app.exec())
