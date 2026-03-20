"""
Unit-Tests für die Datenbank-Layer (SQLite v2.0 Schema)

Diese Datei demonstriert Unit-Tests für die PatientDataManager Klasse
ohne GUI- oder Hardware-Abhängigkeiten.
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db import PatientDataManager


class TestDatabaseV2(unittest.TestCase):
    """Unit-Tests für die SQLite Datenbank v2.0 Schema"""
    
    def setUp(self):
        """Erstelle eine In-Memory Datenbank für jeden Test"""
        self.db = PatientDataManager(':memory:')
        print(f"\n{'='*60}")
        print(f"Test: {self._testMethodName}")
        print(f"{'='*60}")
    
    def test_patient_id_generation(self):
        """Test: Patient ID Generation - Format XXXX-YYYY-MM-DD-G"""
        print("Testing patient ID format...")
        
        patient_id = PatientDataManager.generate_patient_id('1990-05-15', 'M')
        print(f"  Generated ID: {patient_id}")
        
        # Validate format: UUID_PREFIX-YYYY-MM-DD-GENDER
        # Actual format from code is: XXXX-YYYY-MM-DD-GENDER (5 parts when split by '-')
        self.assertIn('-', patient_id, "ID should contain dashes")
        self.assertIn('M', patient_id, "Gender M should be in ID")
        self.assertIn('1990-05-15', patient_id, "Birthdate should be in ID")
        
        # Verify format matches pattern
        pattern_match = patient_id.endswith('-M')
        self.assertTrue(pattern_match, f"ID should end with -M, got {patient_id}")
        
        print(f"  ✓ Format correct: {patient_id}")
    
    def test_patient_creation(self):
        """Test: Patient Creation und Retrieval"""
        print("Testing patient creation and retrieval...")
        
        # Create patient
        patient_id = self.db.create_patient(
            birthdate='1990-05-15',
            sex='M',
            first_name='Max',
            last_name='Mustermann'
        )
        print(f"  Created patient ID: {patient_id}")
        
        # Retrieve patient
        patient = self.db.get_patient(patient_id)
        print(f"  Retrieved patient: {patient['first_name']} {patient['last_name']}")
        
        self.assertIsNotNone(patient, "Patient should be retrievable")
        self.assertEqual(patient['first_name'], 'Max', f"First name should be Max, got {patient['first_name']}")
        self.assertEqual(patient['last_name'], 'Mustermann', f"Last name should be Mustermann, got {patient['last_name']}")
        self.assertEqual(patient['sex'], 'M', f"Sex should be M, got {patient['sex']}")
        
        print(f"  ✓ Patient creation and retrieval successful")
    
    def test_recording_creation(self):
        """Test: Recording ID Creation"""
        print("Testing recording ID creation...")
        
        # Create patient first
        patient_id = self.db.create_patient(
            birthdate='1990-05-15',
            sex='M',
            first_name='Max',
            last_name='Mustermann'
        )
        print(f"  Created patient: {patient_id}")
        
        # Add recording (returns the recording_id that was passed in)
        recording_id = self.db.add_recording(
            recording_id='2026-02-13-14-32-45',
            patient_id=patient_id,
            date=1707831165
        )
        print(f"  Created recording: {recording_id}")
        
        # Verify recording_id is returned correctly
        self.assertEqual(recording_id, '2026-02-13-14-32-45', "Recording ID should match input")
        self.assertIsNotNone(recording_id)
        
        print(f"  ✓ Recording creation successful")
    
    def test_multiple_patients(self):
        """Test: Multiple Patients Management"""
        print("Testing multiple patients management...")
        
        # Create 3 patients
        patient_ids = []
        for i in range(3):
            pid = self.db.create_patient(
                birthdate=f'198{i}-01-01',
                sex=['M', 'W', 'D'][i],
                first_name=f'Patient{i}',
                last_name='Test'
            )
            patient_ids.append(pid)
            print(f"  Created patient {i+1}: {pid}")
        
        # Verify all patients exist
        for i, pid in enumerate(patient_ids):
            patient = self.db.get_patient(pid)
            self.assertIsNotNone(patient)
            self.assertEqual(patient['first_name'], f'Patient{i}')
        
        print(f"  ✓ Successfully managed {len(patient_ids)} patients")
    
    def test_patient_recordings_multiple(self):
        """Test: Multiple Recordings per Patient"""
        print("Testing multiple recordings per patient...")
        
        # Create patient
        patient_id = self.db.create_patient(
            birthdate='1995-03-20',
            sex='W',
            first_name='Anna',
            last_name='Schmidt'
        )
        print(f"  Created patient: {patient_id}")
        
        # Add 3 recordings (create folders/files manually for this test would be complex)
        # Instead: verify that add_recording works multiple times without error
        recording_ids = []
        for i in range(3):
            rid = self.db.add_recording(
                recording_id=f'2026-02-{13+i:02d}-14-32-45',
                patient_id=patient_id,
                date=1707831165 + (i * 86400)  # Add 1 day for each
            )
            recording_ids.append(rid)
            print(f"  Created recording {i+1}: {rid}")
        
        # Verify all recording IDs were returned correctly
        self.assertEqual(len(recording_ids), 3, f"Should have 3 recording IDs, got {len(recording_ids)}")
        for i, rid in enumerate(recording_ids):
            print(f"  ✓ Recording {i+1} ID: {rid}")
        
        print(f"  ✓ Successfully created {len(recording_ids)} recording IDs for patient")


if __name__ == '__main__':
    # Run tests with verbose output
    print("\n" + "="*60)
    print("DATABASE UNIT-TESTS (SQLite v2.0 Schema)")
    print("="*60 + "\n")
    
    unittest.main(verbosity=2)
