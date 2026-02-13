"""
Integration test for v2.0 database schema refactoring.

Tests:
1. Patient creation with new schema (birthdate + sex only)
2. Patient ID format validation (XXXX-YYYY-MM-DD-G)
3. Recording ID format validation (YYYY-MM-DD-HH-MM-SS)
4. Patient retrieval and display
5. Recording association
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from db import PatientDataManager


def test_patient_creation():
    """Test creating a patient with new v2.0 schema."""
    print("\n" + "="*60)
    print("TEST 1: Patient Creation with v2.0 Schema")
    print("="*60)
    
    # Create test database
    db_path = Path("data/eyecon_integration_test.db")
    db_path.parent.mkdir(exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    
    db = PatientDataManager(str(db_path))
    
    # Test case 1: Create male patient
    p1_id = db.create_patient("1990-05-15", "M")
    print(f"✓ Created male patient: {p1_id}")
    
    # Validate format: XXXX-YYYY-MM-DD-G
    parts = p1_id.split("-")
    assert len(parts) == 5, f"Expected 5 parts, got {len(parts)}"
    assert len(parts[0]) == 4, f"UUID part should be 4 chars, got {len(parts[0])}"
    assert parts[1] == "1990", f"Year mismatch: {parts[1]}"
    assert parts[2] == "05", f"Month mismatch: {parts[2]}"
    assert parts[3] == "15", f"Day mismatch: {parts[3]}"
    assert parts[4] == "M", f"Gender should be M, got {parts[4]}"
    print(f"✓ ID format valid: XXXX-YYYY-MM-DD-G")
    
    # Test case 2: Create female patient
    p2_id = db.create_patient("1985-12-25", "W")
    print(f"✓ Created female patient: {p2_id}")
    assert p2_id.endswith("-W"), f"Should end with gender W"
    
    # Test case 3: Create diverse patient
    p3_id = db.create_patient("2000-06-10", "D")
    print(f"✓ Created diverse patient: {p3_id}")
    assert p3_id.endswith("-D"), f"Should end with gender D"
    
    print("\n✅ TEST 1 PASSED: Patient creation works correctly")
    return db, [p1_id, p2_id, p3_id]


def test_patient_retrieval(db, patient_ids):
    """Test retrieving patient data."""
    print("\n" + "="*60)
    print("TEST 2: Patient Retrieval and Data Integrity")
    print("="*60)
    
    for patient_id in patient_ids:
        patient = db.get_patient(patient_id)
        assert patient is not None, f"Patient {patient_id} not found"
        assert patient['id'] == patient_id, "ID mismatch"
        assert 'birthdate' in patient, "Missing birthdate"
        assert 'sex' in patient, "Missing sex"
        
        print(f"✓ Retrieved {patient_id}:")
        print(f"  - Birthdate: {patient['birthdate']}")
        print(f"  - Gender: {patient['sex']}")
    
    print("\n✅ TEST 2 PASSED: Patient retrieval works correctly")


def test_recording_creation(db, patient_ids):
    """Test creating recordings with new ID format."""
    print("\n" + "="*60)
    print("TEST 3: Recording Creation with Timestamp Format")
    print("="*60)
    
    # Generate recording IDs (timestamps)
    base_time = datetime.now()
    rec_ids = []
    
    for i, patient_id in enumerate(patient_ids):
        # Create recording ID from timestamp
        rec_time = base_time + timedelta(hours=i)
        rec_id = db.generate_recording_id(rec_time.timestamp())
        rec_ids.append(rec_id)
        
        # Validate format: YYYY-MM-DD-HH-MM-SS
        parts = rec_id.split("-")
        assert len(parts) == 6, f"Expected 6 parts, got {len(parts)}"
        assert parts[0].isdigit() and len(parts[0]) == 4, "Year invalid"
        assert parts[1].isdigit() and len(parts[1]) == 2, "Month invalid"
        assert parts[2].isdigit() and len(parts[2]) == 2, "Day invalid"
        assert parts[3].isdigit() and len(parts[3]) == 2, "Hour invalid"
        assert parts[4].isdigit() and len(parts[4]) == 2, "Minute invalid"
        assert parts[5].isdigit() and len(parts[5]) == 2, "Second invalid"
        
        # Add recording to database
        date_int = int(rec_time.timestamp())
        db.add_recording(rec_id, patient_id, date_int, baseline=0)
        print(f"✓ Created recording {rec_id} for {patient_id}")
    
    print("\n✅ TEST 3 PASSED: Recording creation works correctly")
    return rec_ids


def test_recording_retrieval(db, patient_ids, rec_ids):
    """Test retrieving recordings."""
    print("\n" + "="*60)
    print("TEST 4: Recording Retrieval and Association")
    print("="*60)
    
    for patient_id, rec_id in zip(patient_ids, rec_ids):
        recordings = db.get_recordings(patient_id)
        
        # Check if recording is associated
        rec_ids_in_db = [r['id'] for r in recordings]
        assert rec_id in rec_ids_in_db, f"Recording {rec_id} not found for {patient_id}"
        print(f"✓ Recording {rec_id} correctly associated with {patient_id}")
    
    print("\n✅ TEST 4 PASSED: Recording retrieval works correctly")


def test_patient_exists_check(db, patient_ids):
    """Test patient existence checking."""
    print("\n" + "="*60)
    print("TEST 5: Patient Existence Checking")
    print("="*60)
    
    for patient_id in patient_ids:
        exists = db.patient_exists(patient_id)
        assert exists, f"Patient {patient_id} should exist"
        print(f"✓ Patient {patient_id} exists check: OK")
    
    # Check non-existent patient
    fake_id = "9999-2000-01-01-M"
    exists = db.patient_exists(fake_id)
    assert not exists, f"Fake patient {fake_id} should not exist"
    print(f"✓ Non-existent patient check: OK")
    
    print("\n✅ TEST 5 PASSED: Patient existence checking works correctly")


def test_database_schema():
    """Verify v2.0 schema structure."""
    print("\n" + "="*60)
    print("TEST 6: Database Schema Validation")
    print("="*60)
    
    db_path = "data/eyecon_integration_test.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check patient table schema
    cur.execute("PRAGMA table_info(Patient)")
    patient_cols = {row[1]: row[2] for row in cur.fetchall()}
    
    assert 'id' in patient_cols, "Missing 'id' column"
    assert patient_cols['id'] == 'TEXT', "ID should be TEXT type"
    assert 'birthdate' in patient_cols, "Missing 'birthdate' column"
    assert 'sex' in patient_cols, "Missing 'sex' column"
    assert 'first_name' not in patient_cols, "Old 'first_name' should be removed"
    assert 'last_name' not in patient_cols, "Old 'last_name' should be removed"
    assert 'external_id' not in patient_cols, "Old 'external_id' should be removed"
    
    print("✓ Patient table schema correct:")
    print(f"  - id: TEXT")
    print(f"  - birthdate: TEXT")
    print(f"  - sex: TEXT")
    
    # Check recording table schema
    cur.execute("PRAGMA table_info(Recording)")
    rec_cols = {row[1]: row[2] for row in cur.fetchall()}
    
    assert 'id' in rec_cols, "Missing 'id' column"
    assert rec_cols['id'] == 'TEXT', "ID should be TEXT type"
    assert 'patientId' in rec_cols, "Missing 'patientId' column"
    
    print("✓ Recording table schema correct:")
    print(f"  - id: TEXT")
    print(f"  - patientId: TEXT (FK)")
    
    conn.close()
    print("\n✅ TEST 6 PASSED: Database schema validation successful")


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("🔍 INTEGRATION TEST SUITE: v2.0 Database Refactoring")
    print("="*60)
    
    try:
        # Run tests in sequence
        db, patient_ids = test_patient_creation()
        test_patient_retrieval(db, patient_ids)
        rec_ids = test_recording_creation(db, patient_ids)
        test_recording_retrieval(db, patient_ids, rec_ids)
        test_patient_exists_check(db, patient_ids)
        test_database_schema()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nSummary:")
        print(f"  - Created {len(patient_ids)} patients")
        print(f"  - Created {len(rec_ids)} recordings")
        print(f"  - Verified ID formats (XXXX-YYYY-MM-DD-G)")
        print(f"  - Verified database schema")
        print("="*60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
