from data_manager import PatientDataManager
from pathlib import Path

db = PatientDataManager(Path("data/eyecon.db"))
patients = db.get_all_patients()

for patient in patients:
    patient_id = patient.get('id')
    print(f"\nPatient: {patient.get('first_name')} {patient.get('last_name')} (ID: {patient_id})")
    
    recordings = db.get_recordings(patient_id)
    print(f"  Recordings in DB: {len(recordings)}")
    
    valid_count = 0
    invalid_count = 0
    
    for rec in recordings:
        rec_id = rec.get('id')
        exists = Path(rec_id).exists()
        status = "✓ EXISTS" if exists else "✗ MISSING"
        print(f"    {rec_id}: {status}")
        
        if exists:
            valid_count += 1
        else:
            invalid_count += 1
    
    print(f"  Valid: {valid_count}, Missing/Deleted: {invalid_count}")
