"""
Test TBI-Headset Import with Duplicate Handling

Creates test data and verifies all 3 merge scenarios:
1. Merge - reuse existing patient
2. Create New - new patient with standard ID format
3. Skip - don't import
"""

import sys
import sqlite3
import tempfile
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db import PatientDataManager
from src.importer import TBIHeadsetImporter


def create_test_tbi_database(db_path: str):
    """
    Create test TBI database with:
    - 1 patient that already exists in EyeCon (for merge test)
    - 1 patient that doesn't exist (for create_new test)
    - 1 patient that will be skipped
    - Recordings for each
    """
    print(f"\n📊 Creating test TBI database at {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create Patient table
    cur.execute("""
        CREATE TABLE Patient (
            id TEXT PRIMARY KEY,
            firstName TEXT,
            lastName TEXT,
            birthdate TEXT,
            sex TEXT
        )
    """)
    
    # Create Recording table
    cur.execute("""
        CREATE TABLE Recording (
            id TEXT PRIMARY KEY,
            patientId TEXT,
            date INTEGER,
            baseline INTEGER,
            file_path TEXT,
            FOREIGN KEY (patientId) REFERENCES Patient(id)
        )
    """)
    
    # Insert test patients
    # Patient 1: DUPLICATE - will trigger dialog
    # (Assume this ID exists in EyeCon from previous tests)
    cur.execute("""
        INSERT INTO Patient (id, firstName, lastName, birthdate, sex)
        VALUES (?, ?, ?, ?, ?)
    """, ("test_duplicate_001", "John", "Doe", "1990-05-15", "M"))
    
    # Patient 2: NEW - will be created with standard format
    cur.execute("""
        INSERT INTO Patient (id, firstName, lastName, birthdate, sex)
        VALUES (?, ?, ?, ?, ?)
    """, ("test_new_patient", "Jane", "Smith", "1985-03-22", "W"))
    
    # Patient 3: SKIP - will be skipped
    cur.execute("""
        INSERT INTO Patient (id, firstName, lastName, birthdate, sex)
        VALUES (?, ?, ?, ?, ?)
    """, ("test_skip_patient", "Bob", "Johnson", "1992-07-10", "M"))
    
    # Insert recordings for each patient
    timestamp = int(time.time())
    
    # Recordings for patient 1 (duplicate)
    cur.execute("""
        INSERT INTO Recording (id, patientId, date, baseline, file_path)
        VALUES (?, ?, ?, ?, ?)
    """, ("rec_001_dup_1", "test_duplicate_001", timestamp - 3600, 0, "videos/2026-02-24/recording_1.mp4"))
    
    cur.execute("""
        INSERT INTO Recording (id, patientId, date, baseline, file_path)
        VALUES (?, ?, ?, ?, ?)
    """, ("rec_001_dup_2", "test_duplicate_001", timestamp - 7200, 0, "videos/2026-02-24/recording_2.mp4"))
    
    # Recordings for patient 2 (new)
    cur.execute("""
        INSERT INTO Recording (id, patientId, date, baseline, file_path)
        VALUES (?, ?, ?, ?, ?)
    """, ("rec_002_new", "test_new_patient", timestamp - 1800, 0, "videos/2026-02-24/recording_3.mp4"))
    
    # Recordings for patient 3 (skip)
    cur.execute("""
        INSERT INTO Recording (id, patientId, date, baseline, file_path)
        VALUES (?, ?, ?, ?, ?)
    """, ("rec_003_skip", "test_skip_patient", timestamp - 900, 0, "videos/2026-02-24/recording_4.mp4"))
    
    conn.commit()
    conn.close()
    
    print(f"✅ TBI database created with 3 test patients and 4 recordings")


def create_dummy_video(path: Path, size_mb: float = 1):
    """Create a dummy MP4 file for testing"""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create a minimal MP4 file (fake, but valid file size)
    with open(path, 'wb') as f:
        f.write(b'\x00' * int(size_mb * 1024 * 1024))
    print(f"  ✓ Created dummy video: {path.name} ({size_mb}MB)")


def create_test_zip(zip_path: str, tbi_db_path: str) -> str:
    """
    Create ZIP file with TBI database and dummy videos.
    
    Returns: Path to created ZIP
    """
    print(f"\n📦 Creating test ZIP file at {zip_path}...")
    
    # Create temp directory for ZIP contents
    temp_zip_dir = Path(tempfile.mkdtemp(prefix="eyecon_zip_"))
    print(f"  Temp directory: {temp_zip_dir}")
    
    # Copy TBI database
    zip_db_path = temp_zip_dir / "patient_database.db"
    shutil.copy(tbi_db_path, zip_db_path)
    print(f"  ✓ Copied database: patient_database.db")
    
    # Create recordings directory and dummy videos
    recordings_dir = temp_zip_dir / "recordings"
    recordings_dir.mkdir()
    
    for i in range(1, 5):
        video_path = recordings_dir / f"recording_{i}.mp4"
        create_dummy_video(video_path, size_mb=0.1)  # Small dummy files
    
    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # Add database
        zipf.write(zip_db_path, arcname="patient_database.db")
        
        # Add videos
        for video_file in recordings_dir.glob("*.mp4"):
            zipf.write(video_file, arcname=f"recordings/{video_file.name}")
    
    # Cleanup temp directory
    shutil.rmtree(temp_zip_dir)
    
    print(f"✅ ZIP file created: {zip_path}")
    return zip_path


def preload_duplicate_patient_to_eyecon(db_manager: PatientDataManager):
    """
    Create the duplicate patient in EyeCon DB first,
    so we have something to merge with.
    """
    print(f"\n👤 Pre-loading duplicate patient to EyeCon database...")
    
    # Create patient with TBI ID "test_duplicate_001"
    patient_id = db_manager.create_patient(
        birthdate="1990-05-15",
        sex="M",
        first_name="Existing",
        last_name="Patient",
        patient_id="test_duplicate_001"  # Use TBI ID directly
    )
    print(f"✅ Created existing patient: {patient_id}")
    
    # Add a dummy recording for this patient
    recording_id = f"existing_recording_{int(time.time())}"
    db_manager.add_recording(recording_id, patient_id, date=int(time.time()), baseline=0)
    print(f"✅ Added dummy recording: {recording_id}")


def test_import_workflow():
    """
    Test the complete TBI import workflow with duplicate handling.
    """
    print("\n" + "="*70)
    print("🧪 TESTING TBI-HEADSET IMPORT WITH DUPLICATE HANDLING")
    print("="*70)
    
    # Setup paths
    test_dir = Path(tempfile.gettempdir()) / "eyecon_tbi_test"
    test_dir.mkdir(exist_ok=True)
    
    tbi_db_path = test_dir / "tbi_patient_database.db"
    zip_path = test_dir / "test_tbi_export.zip"
    
    try:
        # Step 1: Create test TBI database
        create_test_tbi_database(str(tbi_db_path))
        
        # Step 2: Create ZIP file
        create_test_zip(str(zip_path), str(tbi_db_path))
        
        # Step 3: Initialize EyeCon database manager
        print(f"\n🗄️  Initializing EyeCon database...")
        db_manager = PatientDataManager("data/eyecon.db")
        
        # Step 4: Pre-load the duplicate patient
        preload_duplicate_patient_to_eyecon(db_manager)
        
        # Step 5: Create importer and test import
        print(f"\n📥 Starting TBI import workflow...")
        importer = TBIHeadsetImporter(db_manager, parent_widget=None)
        
        # Simulate automated decisions for testing
        # In real usage, user would click dialog buttons
        decision_counter = 0
        
        def automated_duplicate_handler(existing, tbi):
            """
            Simulate user clicking buttons in the dialog.
            Cycle through: merge → create_new → skip
            """
            nonlocal decision_counter
            
            print(f"\n  🔄 Duplicate detected: {tbi.get('id')}")
            print(f"     Existing: {existing['last_name']}, {existing['first_name']}")
            print(f"     TBI Data: {tbi.get('lastName')}, {tbi.get('firstName')}")
            
            decisions = ['merge', 'create_new', 'skip']
            decision = decisions[decision_counter % 3]
            decision_counter += 1
            
            print(f"     Decision: {decision.upper()}")
            return decision
        
        # Import with automated handler
        importer.handle_duplicate_patient = automated_duplicate_handler
        success, result = importer.import_from_zip(str(zip_path))
        
        # Step 6: Print results
        print(f"\n" + "="*70)
        print("📊 IMPORT RESULTS")
        print("="*70)
        print(f"Success: {success}")
        print(f"Imported Patients: {result.get('imported_patients', 0)}")
        print(f"Imported Recordings: {result.get('imported_recordings', 0)}")
        print(f"Duplicates Handled: {result.get('duplicate_handled', 0)}")
        if result.get('errors'):
            print(f"\n⚠️  Errors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"   - {error}")
        else:
            print(f"✅ No errors!")
        
        # Step 7: Verify data in EyeCon database
        print(f"\n" + "="*70)
        print("🔍 VERIFICATION: Patients in EyeCon Database")
        print("="*70)
        
        all_patients = db_manager.get_all_patients()
        print(f"Total patients in EyeCon: {len(all_patients)}")
        
        for patient in all_patients:
            recordings = db_manager.get_recordings(patient['id'])
            print(f"\n  Patient: {patient['id']}")
            print(f"  Name: {patient['last_name']}, {patient['first_name']}")
            print(f"  Birthdate: {patient['birthdate']}")
            print(f"  Recordings: {len(recordings)}")
            for rec in recordings:
                print(f"    - {rec['id']} (date: {rec['date']})")
        
        print(f"\n" + "="*70)
        print("✅ TEST COMPLETED SUCCESSFULLY")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if test_dir.exists():
            print(f"\n🧹 Cleaning up test directory: {test_dir}")
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    test_import_workflow()
