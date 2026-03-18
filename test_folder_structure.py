"""
Test the new patient-based recording folder structure.

This script:
1. Lists all patients
2. Creates patient folders in data/recordings/
3. Tests that get_recordings() returns only patient-specific videos
4. Verifies the structure works correctly
"""

from pathlib import Path
from data_manager import PatientDataManager

# Initialize database
db = PatientDataManager(db_path="data/eyecon.db")

print("="*70)
print("TESTING NEW PATIENT-BASED RECORDING FOLDER STRUCTURE")
print("="*70)

# Get all patients
patients = db.get_all_patients()
print(f"\n[1] Found {len(patients)} patients in database:")
for p in patients:
    print(f"    - ID: {p['id']:3} | {p['last_name']}, {p['first_name']}")

# Create patient folders
print(f"\n[2] Creating patient folders in data/recordings/...")
recordings_dir = Path("data/recordings")
recordings_dir.mkdir(exist_ok=True)

for patient in patients:
    patient_id = patient['id']
    patient_folder = recordings_dir / str(patient_id)
    patient_folder.mkdir(exist_ok=True)
    print(f"    ✓ {patient_folder}")

# Check current flat structure videos
print(f"\n[3] Current videos in flat structure (data/recordings/*.mp4):")
flat_videos = list(recordings_dir.glob("*.mp4"))
print(f"    Found {len(flat_videos)} videos:")
for vid in sorted(flat_videos):
    print(f"    - {vid.name}")

# Now test the get_recordings() method with patient folders
print(f"\n[4] Testing get_recordings() for each patient (folders empty so far):")
for patient in patients:
    patient_id = patient['id']
    recordings = db.get_recordings(str(patient_id))
    status = f"{len(recordings)} videos" if len(recordings) == 0 else f"{len(recordings)} videos (should be 0)"
    print(f"    Patient {patient_id}: {status}")

# Show folder structure
print(f"\n[5] Current folder structure:")
print(f"    data/recordings/")
for patient in patients:
    patient_id = patient['id']
    patient_folder = recordings_dir / str(patient_id)
    video_count = len(list(patient_folder.glob("*.mp4")))
    print(f"      {patient_id}/ ({video_count} videos)")
print(f"      *.mp4 ({len(flat_videos)} videos in flat structure - TO REORGANIZE)")

print("\n" + "="*70)
print("NEXT STEPS (User should do on their side):")
print("="*70)
print("""
1. Delete videos from data/recordings/*.mp4
2. Import new videos for Patient 1 → they go to data/recordings/{patient1_id}/
3. Create/add new videos for other patients → data/recordings/{patient_id}/
4. Then I'll test that get_recordings() returns only per-patient videos
5. Test import functionality to ensure videos land in correct patient folders
""")

print("\n✓ Folder structure is ready for testing!")
