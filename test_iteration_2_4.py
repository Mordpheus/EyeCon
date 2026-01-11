"""Test-Skript für Iteration 2.4: PatientListWidget"""
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from patient_widgets import PatientListWidget

print("=== Iteration 2.4: PatientListWidget Test ===\n")

app = QApplication(sys.argv)

# Test-Patienten
test_patients = [
    {'id': 1, 'name': 'Max', 'nachname': 'Mustermann', 'geburtsdatum': '15.03.1990', 'ext_id': None},
    {'id': 2, 'name': 'Anna', 'nachname': 'Schmidt', 'geburtsdatum': '22.07.1985', 'ext_id': 'SMH-2024-001'},
    {'id': 3, 'name': 'Peter', 'nachname': 'Fischer', 'geburtsdatum': '08.11.1992', 'ext_id': None},
]

window = QWidget()
window.setWindowTitle("Iteration 2.4: PatientListWidget Test")
main_layout = QVBoxLayout()

# Info-Label
info_label = QLabel("Warte auf Auswahl...")
info_label.setStyleSheet("background-color: #1e3a8a; color: white; padding: 10px; border-radius: 5px; font-weight: bold;")
main_layout.addWidget(info_label)

# PatientListWidget
patient_list = PatientListWidget()

print("✓ PatientListWidget erstellt")

# Füge Test-Patienten hinzu
print("\nFüge Patienten hinzu:")
for patient_data in test_patients:
    patient_list.add_patient(patient_data)
    print(f"  ✓ Patient {patient_data['id']}: {patient_data['nachname']}, {patient_data['name']}")

# === ITERATION 2.4: Signal-Handler ===
# Dependency: Signal.connect()
# Verbinde patient_selected Signal mit Handler-Funktion
def on_patient_selected(patient_id: int):
    """Handler wenn Patient aus Liste ausgewählt wird"""
    patient = None
    for p in test_patients:
        if p['id'] == patient_id:
            patient = p
            break
    
    if patient:
        message = f"✓ Patient ausgewählt: {patient['nachname']}, {patient['name']} (ID: {patient_id})"
        print(f"  → {message}")
        info_label.setText(message)

patient_list.patient_selected.connect(on_patient_selected)
print("\n✓ Signal-Verbindung eingerichtet: patient_selected.connect(on_patient_selected)")

# Button-Layout zum Testen der remove_patient Funktion
button_layout = QHBoxLayout()

remove_btn = QPushButton("Patient 2 entfernen")
def remove_patient_2():
    patient_list.remove_patient(2)
    remove_btn.setEnabled(False)
    info_label.setText("Patient 2 wurde entfernt")
    print("  → Patient 2 wurde entfernt")

remove_btn.clicked.connect(remove_patient_2)
button_layout.addWidget(remove_btn)

clear_btn = QPushButton("Alle löschen")
def clear_all():
    patient_list.clear_patients()
    clear_btn.setEnabled(False)
    remove_btn.setEnabled(False)
    info_label.setText("Alle Patienten wurden gelöscht")
    print("  → Alle Patienten wurden gelöscht")

clear_btn.clicked.connect(clear_all)
button_layout.addWidget(clear_btn)

main_layout.addLayout(button_layout)
main_layout.addWidget(patient_list)

window.setLayout(main_layout)
window.resize(400, 500)
window.show()

print("\n✓ Fenster angezeigt.")
print("  - Klicke auf einen Patient um zu selektieren")
print("  - Buttons oben zum Entfernen testen\n")

sys.exit(app.exec())
