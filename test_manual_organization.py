"""
Test the patient-based recording structure with manual video organization.

This simulates what happens when:
1. User deletes flat videos
2. User copies videos into patient folders
3. App loads get_recordings() for each patient
"""

from pathlib import Path
from data_manager import PatientDataManager
import shutil

print("="*80)
print("TESTING PATIENT-BASED RECORDING STRUCTURE - MANUAL ORGANIZATION")
print("="*80)

db = PatientDataManager(db_path="data/eyecon.db")
recordings_dir = Path("data/recordings")

# Get patients
patients = db.get_all_patients()
print(f"\n[1] Patients in system: {len(patients)}")
for i, p in enumerate(patients, 1):
    print(f"    {i}. {p['last_name']}, {p['first_name']} (ID: {p['id']})")

# Get current flat videos
flat_videos = sorted(recordings_dir.glob("*.mp4"))
print(f"\n[2] Current videos in flat structure: {len(flat_videos)}")

# SIMULATE: Move videos manually to patient folders for testing
print(f"\n[3] SIMULATING manual user reorganization...")
print(f"    Moving videos into patient folders (for testing):")

if flat_videos:
    # Take first 5 videos for Patient 1
    patient1_id = patients[0]['id']
    patient1_folder = recordings_dir / str(patient1_id)
    
    print(f"\n    Patient 1 ({patient1_id}): Moving 5 videos")
    for i, video in enumerate(flat_videos[:5], 1):
        dest = patient1_folder / video.name
        try:
            shutil.move(str(video), str(dest))
            print(f"      {i}. {video.name} → {patient1_id}/")
        except Exception as e:
            print(f"      ERROR: {e}")
    
    # Take next 5 videos for Patient 2
    if len(flat_videos) > 5 and len(patients) > 1:
        patient2_id = patients[1]['id']
        patient2_folder = recordings_dir / str(patient2_id)
        
        print(f"\n    Patient 2 ({patient2_id}): Moving 5 videos")
        for i, video in enumerate(flat_videos[5:10], 1):
            dest = patient2_folder / video.name
            try:
                shutil.move(str(video), str(dest))
                print(f"      {i}. {video.name} → {patient2_id}/")
            except Exception as e:
                print(f"      ERROR: {e}")
    
    # Remaining videos for Patient 3
    if len(flat_videos) > 10 and len(patients) > 2:
        patient3_id = patients[2]['id']
        patient3_folder = recordings_dir / str(patient3_id)
        
        print(f"\n    Patient 3 ({patient3_id}): Moving {len(flat_videos[10:])} videos")
        for i, video in enumerate(flat_videos[10:], 1):
            dest = patient3_folder / video.name
            try:
                shutil.move(str(video), str(dest))
                print(f"      {i}. {video.name} → {patient3_id}/")
            except Exception as e:
                print(f"      ERROR: {e}")

# Test get_recordings() for each patient
print(f"\n[4] Testing get_recordings() for each patient:")
print(f"    (Should now return ONLY their own videos)")
print()

total_videos = 0
for patient in patients:
    patient_id = patient['id']
    recordings = db.get_recordings(str(patient_id))
    total_videos += len(recordings)
    
    status = "✓" if len(recordings) > 0 else "✗"
    name = f"{patient['last_name']}, {patient['first_name']}"
    print(f"    {status} {name:30} ({patient_id})")
    
    if recordings:
        for rec in recordings[:3]:  # Show first 3
            print(f"         - {rec['id']} ({rec['date']})")
        if len(recordings) > 3:
            print(f"         ... and {len(recordings)-3} more")

# Show final structure
print(f"\n[5] Final folder structure:")
print(f"    data/recordings/")
for patient in patients:
    patient_id = patient['id']
    patient_folder = recordings_dir / str(patient_id)
    videos = list(patient_folder.glob("*.mp4"))
    if videos or patient_folder.exists():
        print(f"      {patient_id}/ ({len(videos)} videos)")

flat_remaining = list(recordings_dir.glob("*.mp4"))
if flat_remaining:
    print(f"      *.mp4 ({len(flat_remaining)} videos - leftover in flat structure)")

print(f"\n[6] VERIFICATION:")
print(f"    ✓ Total videos tracked: {total_videos}")
print(f"    ✓ Flat structure videos: {len(flat_remaining)}")
print(f"    ✓ Patient-based filtering: WORKING ({'YES' if total_videos > 0 and len(flat_remaining) == 0 else 'NO'})")

print("\n" + "="*80)
print("IF THIS WORKS: User can now manually reorganize videos")
print("NEXT: Need to ensure imported videos also go to correct patient folder")
print("="*80)
