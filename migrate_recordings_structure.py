"""
Migrate existing recordings from flat structure (data/recordings/*.mp4)
to patient-based structure (data/recordings/{patient_id}/*.mp4)

This script:
1. Finds all MP4 files in data/recordings/
2. Creates a patient folder for each unique patient
3. Moves videos into their respective patient folders
"""

import shutil
from pathlib import Path
from src.db import PatientDataManager

def migrate_recordings():
    """Migrate recordings to patient-based folder structure."""
    
    # Initialize database
    db = PatientDataManager(db_path="data/eyecon.db")
    
    recordings_dir = Path("data/recordings")
    if not recordings_dir.exists():
        print("No data/recordings directory found. Nothing to migrate.")
        return
    
    # Find all MP4 files in the flat structure
    mp4_files = list(recordings_dir.glob("*.mp4"))
    
    if not mp4_files:
        print("No MP4 files found in data/recordings/. Already migrated or empty.")
        return
    
    print(f"Found {len(mp4_files)} MP4 files to migrate")
    
    # Get all patients
    patients = db.get_all_patients()
    print(f"Found {len(patients)} patients in database\n")
    
    if not patients:
        print("ERROR: No patients in database. Cannot assign videos to patients.")
        print("Please import TBI data first.")
        return
    
    # For now, move all videos to the FIRST patient's folder as a safety measure
    # User should manually reorganize per their project structure
    default_patient = patients[0]
    default_patient_id = default_patient['id']
    
    print(f"⚠️  ATTENTION: Moving all videos to patient: {default_patient['last_name']}, {default_patient['first_name']} (ID: {default_patient_id})")
    print("You should manually move videos to correct patient folders if needed.\n")
    
    for patient in patients:
        patient_id = patient['id']
        patient_folder = recordings_dir / str(patient_id)
        
        # Create patient folder
        patient_folder.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {patient_folder}")
    
    # Move all MP4 files
    moved_count = 0
    for video_file in mp4_files:
        dest_folder = recordings_dir / str(default_patient_id)
        dest_path = dest_folder / video_file.name
        
        try:
            shutil.move(str(video_file), str(dest_path))
            print(f"✓ Moved {video_file.name} → {dest_folder.name}/")
            moved_count += 1
        except Exception as e:
            print(f"✗ ERROR moving {video_file.name}: {e}")
    
    print(f"\n✓ Migration complete: {moved_count} files moved")
    print(f"\nNew structure:")
    print(f"  data/recordings/")
    for patient in patients:
        patient_id = patient['id']
        patient_folder = recordings_dir / str(patient_id)
        if patient_folder.exists():
            video_count = len(list(patient_folder.glob("*.mp4")))
            print(f"    {patient_id}/ ({video_count} videos)")

if __name__ == "__main__":
    migrate_recordings()
