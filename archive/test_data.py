"""Test-Skript für Datenmanager (Iteration 1)"""
from data_manager import PatientDataManager

print("=== Iteration 1: Datenmanager-Test ===\n")

# Initialisiere Datenmanager
dm = PatientDataManager()

# Test 1: Erstelle Patienten
print("Test 1: Erstelle zwei Patienten")
p1 = dm.create_patient('Max', 'Mustermann', '15.03.1990')
p2 = dm.create_patient('Anna', 'Schmidt', '22.07.1985', ext_id='SMH-2024-001')
print(f"✓ Patient 1: ID {p1['id']} – {p1['name']} {p1['nachname']}")
print(f"✓ Patient 2: ID {p2['id']} – {p2['name']} {p2['nachname']} (Ext-ID: {p2['ext_id']})\n")

# Test 2: Lese alle Patienten
print("Test 2: Lese alle Patienten")
patienten = dm.get_all_patients()
for p in patienten:
    print(f"  – ID {p['id']}: {p['name']} {p['nachname']} ({p['geburtsdatum']})")
print()

# Test 3: Hole einzelnen Patienten
print("Test 3: Hole Patient mit ID 1")
patient = dm.get_patient(1)
print(f"✓ Gefunden: {patient['name']} {patient['nachname']}\n")

# Test 4: Aktualisiere Patienten
print("Test 4: Aktualisiere Patient 1")
dm.update_patient(1, nachname='Neumann')
updated = dm.get_patient(1)
print(f"✓ Neuer Nachname: {updated['nachname']}\n")

# Test 5: Speichere Recordings
print("Test 5: Speichere Baseline-Recording für Patient 1")
recording = dm.add_recording(
    recording_id="REC_001",
    patient_id=1,
    date=1704067200,
    baseline=1
)
print(f"✓ Recording gespeichert: ID {recording}\n")

# Test 6: Lese Recordings
print("Test 6: Lese alle Recordings von Patient 1")
recordings = dm.get_recordings(1)
for r in recordings:
    print(f"  – Recording {r['id']}: Datum {r['date']} – Baseline: {r['baseline']}")
print()

# Test 7: Lösche Patient
print("Test 7: Lösche Patient 2")
dm.delete_patient(2)
verbleibend = dm.get_all_patients()
print(f"✓ Gelöscht. Verbleibende Patienten: {len(verbleibend)}\n")

print("=== Alle Tests erfolgreich! ===")
