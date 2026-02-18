from data_manager import PatientDataManager
from pathlib import Path

db = PatientDataManager(Path("data/eyecon.db"))
patients = db.get_all_patients()

# Test mit Peter Pan (hat deleted recordings)
for patient in patients:
    if patient.get('first_name') == 'Peter':
        patient_id = patient.get('id')
        print(f"\n=== Testing Peter Pan (ID: {patient_id}) ===")
        
        recordings = db.get_recordings(patient_id)
        print(f"Total recordings from DB: {len(recordings)}")
        
        # Simulate _refresh_recordings_list() logic
        valid_recordings = []
        for rec in recordings:
            rec_path = rec.get('id', '')
            print(f"  Checking: {rec_path}")
            if rec_path and Path(rec_path).exists():
                print(f"    -> VALID, adding to list")
                valid_recordings.append(rec)
            else:
                print(f"    -> INVALID, SKIPPING")
        
        print(f"\nAfter filtering: {len(valid_recordings)} valid recordings")
        print(f"These would appear in the list:")
        for i, rec in enumerate(valid_recordings):
            print(f"  Item {i}: {rec.get('id')}")
