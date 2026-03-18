from data_manager import PatientDataManager
from pathlib import Path

db = PatientDataManager(Path("data/eyecon.db"))
patients = db.get_patients()
print(f"Total patients: {len(patients)}")

if patients:
    patient = patients[0]
    print(f"\nFirst patient: id={patient.get('id')}, name={patient.get('name')}")
    
    recordings = db.get_recordings(patient.get('id'))
    print(f"\nRecordings in database (count={len(recordings)}):")
    for i, rec in enumerate(recordings):
        print(f"  [{i}] id={rec.get('id')}")
        print(f"      date={rec.get('date')}")
        print(f"      baseline={rec.get('baseline')}")
