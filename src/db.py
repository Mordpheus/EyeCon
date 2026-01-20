from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

"""
SQLite Database Layer for EyeCon Application

Provides PatientDataManager class for persistent storage of patient data
and measurements using SQLite with proper schema and relationships.
"""


class PatientDataManager:
    """Database manager for EyeCon patient data using SQLite."""

    def __init__(self, db_path: Path | str) -> None:
        """Initialize database manager with path to SQLite database file."""
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self.init()

    def init(self) -> None:
        """Initialize database and create tables if needed."""
        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        first_time = not self.db_path.exists()

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()

        # Create patient table
        # NOTE: sex column added for TBI_Headset import compatibility
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birthdate TEXT NOT NULL,
                sex TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # === RECORDING TABLE ===
        # Stores measurement/recording data directly in SQLite (compatible with TBI_Headset)
        # NO MORE JSON wrapper like the old measurement table!
        # 
        # Columns:
        #   id (TEXT PK)      - Unique recording ID (from TBI_Headset)
        #   patientId (INT)   - Foreign key to patient.id (with Cascade Delete)
        #   date (INT)        - Unix timestamp when recording was made
        #   baseline (INT)    - Flag: 0=normal recording, 1=baseline recording
        #
        # IMPORTANT: No more JSON data! Everything stored directly in SQLite.
        #            This makes queries simpler and faster.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recording (
                id TEXT PRIMARY KEY,
                patientId INTEGER NOT NULL,
                date INTEGER,
                baseline INTEGER DEFAULT 0,
                FOREIGN KEY (patientId) REFERENCES patient(id) ON DELETE CASCADE
            )
            """
        )

        self.conn.commit()

        # === DATABASE MIGRATION ===
        # If old measurement table exists, migrate to new recording table
        if not first_time:
            migration_result = self.migrate_measurement_to_recording()
            if migration_result['migrated'] > 0:
                print(f"✅ Database migration: {migration_result['migrated']} records migrated")
            if migration_result['errors']:
                print(f"⚠️  Migration warnings: {migration_result['errors']}")

        # Insert sample data if database was just created
        if first_time:
            cur.execute(
                "INSERT INTO patient (external_id, first_name, last_name, birthdate) VALUES (?, ?, ?, ?)",
                ("EXT001", "Max", "Mustermann", "01.03.1990")
            )
            patient_id_1 = cur.lastrowid

            cur.execute(
                "INSERT INTO patient (external_id, first_name, last_name, birthdate) VALUES (?, ?, ?, ?)",
                ("EXT002", "Anna", "Schmidt", "15.07.1985")
            )
            patient_id_2 = cur.lastrowid

            # Add sample baseline recording for first patient
            cur.execute(
                "INSERT INTO recording (id, patientId, date, baseline) VALUES (?, ?, ?, ?)",
                ('REC001', patient_id_1, 1704067200, 1)
            )

            self.conn.commit()

    def create_patient(self, first_name: str, last_name: str, birthdate: str, external_id: str | None = None) -> int:
        """Create new patient record and return patient ID."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO patient (external_id, first_name, last_name, birthdate) VALUES (?, ?, ?, ?)",
            (external_id, first_name, last_name, birthdate)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Retrieve all patients from database."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM patient ORDER BY id DESC")
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_patient(self, patient_id: int) -> Dict[str, Any] | None:
        """Retrieve single patient by ID."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM patient WHERE id = ?", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_patient(self, patient_id: int, first_name: str | None = None, last_name: str | None = None, birthdate: str | None = None) -> None:
        """Update patient record."""
        updates = []
        params = []

        if first_name is not None:
            updates.append("first_name = ?")
            params.append(first_name)
        if last_name is not None:
            updates.append("last_name = ?")
            params.append(last_name)
        if birthdate is not None:
            updates.append("birthdate = ?")
            params.append(birthdate)

        if not updates:
            return

        params.append(patient_id)
        query = f"UPDATE patient SET {', '.join(updates)} WHERE id = ?"
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()

    def delete_patient(self, patient_id: int) -> None:
        """Delete patient and all associated recordings."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM patient WHERE id = ?", (patient_id,))
        self.conn.commit()

    def add_recording(self, recording_id: str, patient_id: int, date: int, baseline: int = 0) -> str:
        """
        Store a new recording/measurement in the database.
        
        This method writes directly to the recording table (not measurement!)
        A recording consists of:
        - recording_id: Unique text ID (e.g. from TBI_Headset import)
        - patient_id: Which patient made this recording
        - date: Unix timestamp (seconds since 1970) when recorded
        - baseline: 1=baseline (reference measurement), 0=normal recording
        
        Database operation: INSERT INTO recording
        Returns: The stored recording_id
        """
        cur = self.conn.cursor()
        # INSERT: New row in recording table with all 4 columns
        cur.execute(
            "INSERT INTO recording (id, patientId, date, baseline) VALUES (?, ?, ?, ?)",
            (recording_id, patient_id, date, baseline)
        )
        # COMMIT: Persist change to SQLite
        self.conn.commit()
        return recording_id

    def get_recordings(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve all recordings of a patient from the database.
        
        Database operation: SELECT * FROM recording WHERE patientId = ?
        - Filters by patient_id
        - Sorts by date DESC (newest first)
        - Returns: List of dicts with all recording columns
        
        Example return:
        [
          {'id': 'REC001', 'patientId': 5, 'date': 1704067200, 'baseline': 1},
          {'id': 'REC002', 'patientId': 5, 'date': 1704153600, 'baseline': 0},
        ]
        """
        cur = self.conn.cursor()
        # SELECT: All columns (id, patientId, date, baseline) for this patient
        cur.execute("SELECT * FROM recording WHERE patientId = ? ORDER BY date DESC", (patient_id,))
        # FETCH: Get all matching rows
        rows = cur.fetchall()
        # CONVERT: sqlite3.Row objects to Python dicts
        return [dict(row) for row in rows]

    def get_baseline_recording(self, patient_id: int) -> Dict[str, Any] | None:
        """
        Retrieve the baseline recording of a patient.
        
        Database operation: SELECT * FROM recording WHERE patientId = ? AND baseline = 1
        - Filters by patient_id AND baseline=1
        - LIMIT 1: Returns at most one row
        - Returns: A dict or None if not found
        
        Baseline recordings are reference measurements for comparisons.
        """
        cur = self.conn.cursor()
        # SELECT: Find baseline recording for this patient
        cur.execute("SELECT * FROM recording WHERE patientId = ? AND baseline = 1 LIMIT 1", (patient_id,))
        # FETCH ONE: Get at most one row
        row = cur.fetchone()
        # CONVERT: sqlite3.Row to dict, or None if not found
        return dict(row) if row else None

    def migrate_measurement_to_recording(self) -> Dict[str, Any]:
        """
        Migrate data from old measurement table to new recording table.
        
        Called during database initialization if old table exists.
        Converts measurement records to recording format:
        - Generate recording_id from measurement id
        - Map patient_id to patientId
        - Extract date from recorded_at (use default if null)
        - Use is_baseline as baseline flag
        
        Returns:
            Dictionary with migration results
        """
        result = {
            'migrated': 0,
            'skipped': 0,
            'errors': []
        }
        
        cur = self.conn.cursor()
        
        try:
            # Check if old measurement table exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='measurement'")
            if not cur.fetchone():
                # No old table, migration not needed
                return result
            
            # Check if new recording table is empty (safety check)
            cur.execute("SELECT COUNT(*) FROM recording")
            if cur.fetchone()[0] > 0:
                result['errors'].append("Recording table already has data - skipping migration")
                return result
            
            # Get all measurement records
            cur.execute("SELECT id, patient_id, recorded_at, is_baseline, data FROM measurement")
            measurements = cur.fetchall()
            
            for measurement in measurements:
                try:
                    m_id = measurement[0]
                    patient_id = measurement[1]
                    recorded_at = measurement[2]
                    is_baseline = measurement[3]
                    data = measurement[4]
                    
                    # Generate recording_id (migration from measurement)
                    recording_id = f"MIGRATED_M{m_id}"
                    
                    # Convert recorded_at to unix timestamp (if possible)
                    date = 0
                    if recorded_at:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(recorded_at)
                            date = int(dt.timestamp())
                        except:
                            date = 0
                    
                    # Convert is_baseline to baseline (0 or 1)
                    baseline = 1 if is_baseline else 0
                    
                    # Insert into recording table
                    cur.execute(
                        "INSERT INTO recording (id, patientId, date, baseline) VALUES (?, ?, ?, ?)",
                        (recording_id, patient_id, date, baseline)
                    )
                    result['migrated'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"Error migrating measurement {m_id}: {str(e)}")
                    result['skipped'] += 1
            
            self.conn.commit()
            
        except Exception as e:
            result['errors'].append(f"Migration failed: {str(e)}")
        
        return result
        """
        Import patient data and recordings from a TBI_Headset database ZIP.
        
        WORKFLOW:
        1. Open TBI_Headset database (read-only)
        2. Read all patients and store them in EyeCon (with ID mapping)
        3. Read all recordings and map them to new patients
        4. Return statistics (how many imported, errors)
        
        SCHEMA-MAPPING:
        TBI_Headset.Patient.id          → EyeCon.patient.external_id
        TBI_Headset.Patient.sex         → EyeCon.patient.sex
        TBI_Headset.Patient.birthdate   → EyeCon.patient.birthdate
        
        TBI_Headset.Recording.id        → EyeCon.recording.id (directly!)
        TBI_Headset.Recording.patientId → EyeCon.recording.patientId (via lookup)
        TBI_Headset.Recording.date      → EyeCon.recording.date
        TBI_Headset.Recording.baseline  → EyeCon.recording.baseline
        
        IMPORTANT: This is an IMPORT from outside, NOT modified by EyeCon!
        
        Args:
            tbi_db_path: Path to TBI_Headset patient_database.db file
            
        Returns:
            Dictionary with import results:
            - imported_patients: Count of successfully imported patients
            - imported_recordings: Count of successfully imported recordings
            - skipped_recordings: Count of skipped recordings (errors)
            - errors: List with error messages
        """
        import sqlite3
        
        # === RESULT DICT FOR STATISTICS ===
        # Returned at the end to show the user what happened
        result = {
            'imported_patients': 0,      # How many patients successfully inserted
            'imported_recordings': 0,    # How many recordings successfully inserted
            'skipped_recordings': 0,     # How many recordings skipped (errors/patient not found)
            'errors': []                 # List with error messages
        }
        
        try:
            # === DATABASE CONNECTION TO TBI_HEADSET DATABASE ===
            # Important: mode=ro (read-only) - we do NOT modify TBI database!
            # This is pure read-only import access
            tbi_conn = sqlite3.connect(f'file:{tbi_db_path}?mode=ro', uri=True)
            tbi_conn.row_factory = sqlite3.Row
            tbi_cur = tbi_conn.cursor()
            
            # === PHASE 1: IMPORT PATIENTS ===
            # Read ALL patients from TBI_Headset database
            # Store them in EyeCon patient table
            # Create id_mapping dict for later recording lookup
            try:
                # SELECT: All patients from TBI database
                tbi_cur.execute("SELECT id, sex, birthdate FROM Patient")
                tbi_patients = tbi_cur.fetchall()
                
                # IMPORTANT: id_mapping links TBI patient_ids with EyeCon patient_ids
                # Used later to map recordings to the correct patient
                # Example: id_mapping['TBI_P001'] = 5  (EyeCon patient.id)
                id_mapping = {}
                
                for tbi_patient in tbi_patients:
                    tbi_id = tbi_patient['id']
                    sex = tbi_patient['sex'] or 'Unknown'
                    birthdate = tbi_patient['birthdate'] or '01.01.1990'
                    
                    # Default first_name/last_name from TBI external_id
                    first_name = f"Patient_{tbi_id[:10]}"  # Extract from ID
                    last_name = "TBI_Import"
                    
                    try:
                        # DATABASE OPERATION: INSERT into EyeCon patient table
                        # external_id = TBI patient_id (for tracking/auditing)
                        eyecon_id = self.create_patient(
                            first_name=first_name,
                            last_name=last_name,
                            birthdate=birthdate,
                            external_id=tbi_id  # ← Important: Store original TBI ID
                        )
                        
                        # SAVE MAPPING: TBI ID → EyeCon ID
                        # Needed later for recording import
                        id_mapping[tbi_id] = eyecon_id
                        
                        # DATABASE OPERATION: UPDATE sex field
                        # (create_patient() doesn't set sex, so separate UPDATE)
                        cur = self.conn.cursor()
                        cur.execute("UPDATE patient SET sex = ? WHERE id = ?", (sex, eyecon_id))
                        self.conn.commit()  # ← Persist update to SQLite
                        
                        result['imported_patients'] += 1
                        
                    except Exception as e:
                        error_msg = f"Error importing patient {tbi_id}: {str(e)}"
                        result['errors'].append(error_msg)
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI patients: {str(e)}")
            
            # === PHASE 2: IMPORT RECORDINGS ===
            # Read ALL recordings from TBI_Headset database
            # Map patient_id via id_mapping dictionary
            # Store them in EyeCon recording table
            try:
                # SELECT: All recordings with their metadata
                tbi_cur.execute("SELECT id, patientId, date, baseline FROM Recording")
                tbi_recordings = tbi_cur.fetchall()
                
                for tbi_recording in tbi_recordings:
                    tbi_recording_id = tbi_recording['id']
                    tbi_patient_id = tbi_recording['patientId']
                    date = tbi_recording['date']
                    baseline = tbi_recording['baseline']
                    
                    # IMPORTANT: Lookup EyeCon patient_id via id_mapping
                    # If patient not in import → error and skip
                    if tbi_patient_id not in id_mapping:
                        result['errors'].append(f"Recording {tbi_recording_id}: Patient {tbi_patient_id} not found in import")
                        result['skipped_recordings'] += 1
                        continue  # → Next recording
                    
                    # MAPPING: TBI patient_id → EyeCon patient_id (via lookup)
                    eyecon_patient_id = id_mapping[tbi_patient_id]
                    
                    try:
                        # DATABASE OPERATION: INSERT into EyeCon recording table
                        # recording_id: Taken directly from TBI (TEXT Primary Key)
                        # patient_id: EyeCon patient mapped via id_mapping
                        # date: Unix timestamp from TBI
                        # baseline: Flag if baseline measurement or not
                        self.add_recording(
                            recording_id=str(tbi_recording_id),  # TBI ID as PK
                            patient_id=eyecon_patient_id,        # Mapped EyeCon ID
                            date=int(date) if date else 0,       # Unix timestamp
                            baseline=int(baseline) if baseline else 0  # 0 or 1
                        )
                        
                        result['imported_recordings'] += 1
                        
                    except Exception as e:
                        error_msg = f"Error importing recording {tbi_recording_id}: {str(e)}"
                        result['errors'].append(error_msg)
                        result['skipped_recordings'] += 1
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI recordings: {str(e)}")
            
            tbi_conn.close()
            
        except Exception as e:
            result['errors'].append(f"Failed to open TBI database: {str(e)}")
        
        return result
