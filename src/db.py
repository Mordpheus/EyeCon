from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

"""
SQLite Database Layer for EyeCon Application - REFACTORED v2.0

NEW SCHEMA (Feb 13, 2026):
- Patient ID: TEXT format XXXX-YYYY-MM-DD-G (UUID prefix-Birthdate-Gender)
- Recording ID: TEXT format YYYY-MM-DD-HH-MM-SS (timestamp-based filename)
- Removed: external_id, first_name, last_name columns
- Added: Merge dialog for duplicate patient detection on import

Provides PatientDataManager class for persistent storage of patient data
and measurements using SQLite with proper schema and relationships.
"""


class PatientDataManager:
    """Database manager for EyeCon patient data using SQLite - v2.0 Schema."""

    def __init__(self, db_path: Path | str) -> None:
        """Initialize database manager with path to SQLite database file."""
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self.init()

    @staticmethod
    def generate_patient_id(birthdate: str, sex: str) -> str:
        """
        Generate patient ID in format: XXXX-YYYY-MM-DD-G
        
        Args:
            birthdate: Date string in format YYYY-MM-DD
            sex: Gender as single char: M (male), W (female), D (diverse)
            
        Returns:
            New patient ID string, e.g. "7F2A-1990-05-15-M"
        """
        # Generate UUID and take first 4 hex digits
        uuid_prefix = str(uuid.uuid4()).split('-')[0][:4].upper()
        
        # Ensure birthdate is in YYYY-MM-DD format
        if isinstance(birthdate, str) and len(birthdate) > 0:
            # Handle DD.MM.YYYY format (convert to YYYY-MM-DD)
            if '.' in birthdate:
                parts = birthdate.split('.')
                if len(parts) == 3:
                    birthdate = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        # Validate gender
        if sex not in ['M', 'W', 'D']:
            sex = 'D'  # Default to diverse if invalid
        
        return f"{uuid_prefix}-{birthdate}-{sex}"

    @staticmethod
    def generate_recording_id(timestamp: int | None = None) -> str:
        """
        Generate recording ID in format: YYYY-MM-DD-HH-MM-SS
        
        This ID is also used as the filename for the video file.
        
        Args:
            timestamp: Unix timestamp (seconds). If None, uses current time.
            
        Returns:
            Recording ID string, e.g. "2026-02-13-14-32-45"
        """
        if timestamp is None or timestamp == 0:
            dt = datetime.now()
        else:
            dt = datetime.fromtimestamp(timestamp)
        
        return dt.strftime("%Y-%m-%d-%H-%M-%S")

    def init(self) -> None:
        """Initialize database and create tables according to NEW SCHEMA v2.0."""
        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        first_time = not self.db_path.exists()

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()

        # === NEW SCHEMA v2.0: Patient Table ===
        # Changed from INTEGER id to TEXT id with format: XXXX-YYYY-MM-DD-G
        # Removed: external_id, first_name, last_name
        # These were redundant - now everything is in the ID and metadata columns
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id TEXT PRIMARY KEY,
                sex TEXT NOT NULL,
                birthdate TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # === Recording Table ===
        # Recording ID format: YYYY-MM-DD-HH-MM-SS (also the filename)
        # This allows direct mapping: recording.id → filename in data/recordings/
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recording (
                id TEXT PRIMARY KEY,
                patientId TEXT NOT NULL,
                date INTEGER,
                baseline INTEGER DEFAULT 0,
                FOREIGN KEY (patientId) REFERENCES patient(id) ON DELETE CASCADE
            )
            """
        )

        self.conn.commit()

        # Delete old test data if exists (user requested deletion)
        # This removes the 11 test recordings and their patients
        if not first_time:
            try:
                cur.execute("DELETE FROM recording")
                cur.execute("DELETE FROM patient")
                self.conn.commit()
            except Exception as e:
                print(f"⚠️  Could not clear old test data: {e}")

    def create_patient(self, birthdate: str, sex: str) -> str:
        """
        Create new patient record with auto-generated ID.
        
        Args:
            birthdate: Patient birthdate in format YYYY-MM-DD or DD.MM.YYYY
            sex: Single character gender: M (male), W (female), D (diverse)
        
        Returns:
            Generated patient ID in format XXXX-YYYY-MM-DD-G
        """
        # Generate patient ID
        patient_id = self.generate_patient_id(birthdate, sex)
        
        # Normalize birthdate to YYYY-MM-DD format
        if '.' in birthdate:
            parts = birthdate.split('.')
            if len(parts) == 3:
                birthdate = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        # Insert into database
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO patient (id, sex, birthdate) VALUES (?, ?, ?)",
            (patient_id, sex, birthdate)
        )
        self.conn.commit()
        return patient_id

    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Retrieve all patients from database, ordered by creation time."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM patient ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_patient(self, patient_id: str) -> Dict[str, Any] | None:
        """Retrieve single patient by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM patient WHERE id = ?", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def patient_exists(self, patient_id: str) -> bool:
        """Check if patient with given ID exists."""
        return self.get_patient(patient_id) is not None

    def delete_patient(self, patient_id: str) -> None:
        """Delete patient and all associated recordings (CASCADE)."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM patient WHERE id = ?", (patient_id,))
        self.conn.commit()

    def add_recording(self, recording_id: str, patient_id: str, date: int, baseline: int = 0) -> str:
        """
        Store a new recording in the database.
        
        Recording ID must be in format: YYYY-MM-DD-HH-MM-SS
        This ID corresponds to the video filename on disk.
        
        Args:
            recording_id: Unique recording ID (e.g. "2026-02-13-14-32-45")
            patient_id: Patient ID who made this recording
            date: Unix timestamp when recording was made
            baseline: 1=baseline (reference), 0=normal recording
        
        Returns:
            The stored recording_id
        """
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO recording (id, patientId, date, baseline) VALUES (?, ?, ?, ?)",
            (recording_id, patient_id, date, baseline)
        )
        self.conn.commit()
        return recording_id

    def get_recordings(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all recordings of a patient from the database.
        
        Returns recordings sorted by date in descending order (newest first).
        """
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM recording WHERE patientId = ? ORDER BY date DESC", (patient_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_baseline_recording(self, patient_id: str) -> Dict[str, Any] | None:
        """
        Retrieve the baseline recording of a patient.
        
        Baseline recordings are reference measurements for comparisons.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM recording WHERE patientId = ? AND baseline = 1 LIMIT 1", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def import_from_tbi_headset(
        self, 
        tbi_db_path: str, 
        video_mapping: dict = None,
        on_duplicate_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Import patient data and recordings from TBI_Headset database.
        
        WORKFLOW:
        1. Read all patients from TBI database
        2. Calculate EyeCon patient IDs (XXXX-YYYY-MM-DD-G format)
        3. Check for duplicates (same calculated ID):
           - If found: Call on_duplicate_callback(eyecon_patient, tbi_patient)
           - Callback returns: 'merge' (combine recordings) or 'skip' (don't import)
        4. Read all recordings and map to patients
        5. Convert Android paths to local paths using video_mapping
        6. Insert all data into database
        
        Args:
            tbi_db_path: Path to TBI Patient database (SQLite)
            video_mapping: Dict mapping filenames to local paths (optional)
            on_duplicate_callback: Function called on duplicate detection
                                 Signature: on_duplicate_callback(eyecon_id, tbi_data) -> 'merge'|'skip'
        
        Returns:
            Dict with import statistics and errors
        """
        if video_mapping is None:
            video_mapping = {}
        
        result = {
            'imported_patients': 0,
            'imported_recordings': 0,
            'skipped_recordings': 0,
            'duplicate_handled': 0,
            'errors': []
        }
        
        try:
            # Open TBI database in read-only mode
            tbi_conn = sqlite3.connect(f'file:{tbi_db_path}?mode=ro', uri=True)
            tbi_conn.row_factory = sqlite3.Row
            tbi_cur = tbi_conn.cursor()
            
            # === PHASE 1: IMPORT PATIENTS ===
            # id_mapping: TBI patient_id → EyeCon patient_id
            id_mapping = {}
            
            try:
                tbi_cur.execute("SELECT * FROM Patient")
                tbi_patients = tbi_cur.fetchall()
                
                for tbi_patient in tbi_patients:
                    try:
                        patient_dict = dict(tbi_patient)
                        tbi_id = patient_dict.get('id')
                        
                        if not tbi_id:
                            result['errors'].append("TBI patient has no ID, skipping")
                            continue
                        
                        # Extract data from TBI patient
                        birthdate = patient_dict.get('birthdate') or '1990-01-01'
                        sex = patient_dict.get('sex') or 'D'
                        
                        # Normalize sex to M/W/D
                        sex_map = {'M': 'M', 'W': 'W', 'D': 'D', 'male': 'M', 'female': 'W', 'diverse': 'D'}
                        sex = sex_map.get(str(sex).upper(), 'D')
                        
                        # Calculate EyeCon patient ID
                        calculated_id = self.generate_patient_id(birthdate, sex)
                        
                        # Check for duplicate
                        if self.patient_exists(calculated_id):
                            # Patient with this ID already exists!
                            existing_patient = self.get_patient(calculated_id)
                            
                            if on_duplicate_callback:
                                decision = on_duplicate_callback(existing_patient, patient_dict)
                            else:
                                # Default: skip if no callback provided
                                decision = 'skip'
                            
                            if decision == 'merge':
                                # Reuse existing patient ID
                                id_mapping[tbi_id] = calculated_id
                                result['duplicate_handled'] += 1
                            else:
                                # Skip this patient
                                result['errors'].append(f"TBI patient {tbi_id}: Duplicate {calculated_id} skipped (user choice)")
                                continue
                        else:
                            # New patient - create it
                            new_patient_id = self.create_patient(birthdate, sex)
                            id_mapping[tbi_id] = new_patient_id
                            result['imported_patients'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Error importing patient {tbi_patient.get('id')}: {str(e)}")
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI patients: {str(e)}")
            
            # === PHASE 2: IMPORT RECORDINGS ===
            try:
                tbi_cur.execute("SELECT * FROM Recording")
                tbi_recordings = tbi_cur.fetchall()
                
                for tbi_recording in tbi_recordings:
                    try:
                        recording_dict = dict(tbi_recording)
                        
                        # Extract TBI recording data
                        tbi_recording_id = recording_dict.get('id')
                        tbi_patient_id = recording_dict.get('patientId')
                        date = recording_dict.get('date') or 0
                        baseline = recording_dict.get('baseline') or 0
                        
                        # Validate foreign key
                        if tbi_patient_id not in id_mapping:
                            result['errors'].append(f"Recording {tbi_recording_id}: Patient {tbi_patient_id} not found")
                            result['skipped_recordings'] += 1
                            continue
                        
                        eyecon_patient_id = id_mapping[tbi_patient_id]
                        
                        # === CONVERT PATH: Android → Local ===
                        # TBI recording_id often contains Android file path
                        # Extract filename and look up local path
                        filename = str(tbi_recording_id).split("/")[-1]
                        
                        if filename in video_mapping:
                            local_recording_id = video_mapping[filename]
                        else:
                            # No video mapping available - use generated ID from timestamp
                            local_recording_id = self.generate_recording_id(date if date > 0 else None)
                        
                        # Insert recording
                        self.add_recording(
                            recording_id=local_recording_id,
                            patient_id=eyecon_patient_id,
                            date=int(date) if date > 0 else 0,
                            baseline=1 if baseline else 0
                        )
                        
                        result['imported_recordings'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Error importing recording {tbi_recording.get('id')}: {str(e)}")
                        result['skipped_recordings'] += 1
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI recordings: {str(e)}")
            
            tbi_conn.close()
            
        except Exception as e:
            result['errors'].append(f"Failed to open TBI database: {str(e)}")
        
        return result
