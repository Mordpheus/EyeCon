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
        """Initialize database and create tables according to SCHEMA v2.0."""
        # Create parent directories if they don't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        first_time = not self.db_path.exists()

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()

        # === SCHEMA v2.0: Patient Table ===
        # Patient ID: TEXT format XXXX-YYYY-MM-DD-G (UUID prefix + Birthdate + Gender)
        # Stores: first_name, last_name (required), birthdate, sex
        # NOTE: Names are NOT used in ID generation but are REQUIRED fields
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birthdate TEXT NOT NULL,
                sex TEXT NOT NULL,
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
        
        # === NEW: Pupil Frame Data Table ===
        # Stores per-frame pupil detection results from YOLO
        # One row per analyzed frame in a video
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pupil_frame (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT NOT NULL,
                frame_number INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                diameter_px REAL NOT NULL,
                position_x REAL NOT NULL,
                position_y REAL NOT NULL,
                confidence REAL NOT NULL,
                eye_area_px INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES recording(id) ON DELETE CASCADE,
                UNIQUE(recording_id, frame_number)
            )
            """
        )
        
        # === NEW: PLR Metrics Table ===
        # Stores calculated PLR (Pupil Light Reflex) biomarkers for each recording
        # One row per analyzed recording (after stimulus detection)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plr_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT NOT NULL UNIQUE,
                
                -- Baseline parameters
                baseline_mean REAL NOT NULL,
                baseline_max REAL NOT NULL,
                baseline_min REAL NOT NULL,
                
                -- Latency (Bergamin-Kardon method)
                latency REAL,
                latency_frame_idx INTEGER,
                
                -- Constriction phase
                peak_constriction_velocity REAL,
                peak_constriction_velocity_frame INTEGER,
                average_constriction_velocity REAL,
                
                -- Minimum diameter and amplitude
                minimum_diameter REAL,
                minimum_diameter_frame INTEGER,
                amplitude REAL,
                
                -- Dilation phase
                peak_dilation_velocity REAL,
                peak_dilation_velocity_frame INTEGER,
                average_dilation_velocity REAL,
                
                -- Pupil Recovery Time
                prt_50 REAL,
                prt_63 REAL,
                prt_75 REAL,
                
                -- Metadata
                light_stimulus_start_frame INTEGER,
                light_stimulus_end_frame INTEGER,
                analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (recording_id) REFERENCES recording(id) ON DELETE CASCADE
            )
            """
        )
        
        # === NEW: Analysis Session Table ===
        # Tracks analysis runs (for history and debugging)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id TEXT NOT NULL,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                frame_count INTEGER,
                analyzed_frame_count INTEGER,
                error_message TEXT,
                FOREIGN KEY (recording_id) REFERENCES recording(id) ON DELETE CASCADE
            )
            """
        )

        self.conn.commit()

        # Delete old test data if exists (user requested deletion)
        # This removes the 11 test recordings and their patients
        # ONLY on first run when setting up fresh database
        if first_time:
            try:
                cur.execute("DELETE FROM recording")
                cur.execute("DELETE FROM patient")
                self.conn.commit()
            except Exception as e:
                print(f"Could not clear old test data: {e}")

    def create_patient(self, birthdate: str, sex: str, first_name: str = "", last_name: str = "", patient_id: str = None) -> str:
        """
        Create new patient record.
        
        Names are stored separately and not used in ID generation.
        Patient ID is either generated from birthdate + sex, or provided directly.
        When patient_id is provided (TBI import), birthdate and sex may be empty.
        
        Args:
            birthdate: Patient birthdate in format YYYY-MM-DD or DD.MM.YYYY (can be empty)
            sex: Single character gender: M (male), W (female), D (diverse) (can be empty)
            first_name: Patient first name
            last_name: Patient last name
            patient_id: Optional. If provided, use this ID directly (for TBI imports).
                       If None, generate standard XXXX-YYYY-MM-DD-G format.
        
        Returns:
            Patient ID (either generated or provided as parameter)
            
        Raises:
            ValueError: If patient_id is None and first_name or last_name is empty
        """
        # Generate or use provided patient ID
        if patient_id is None:
            # For generated IDs, names and birthdate are required
            if not first_name or not first_name.strip():
                raise ValueError("First name is required and cannot be empty")
            if not last_name or not last_name.strip():
                raise ValueError("Last name is required and cannot be empty")
            patient_id = self.generate_patient_id(birthdate, sex)
        # else: use provided ID directly (TBI import — fields may be incomplete)
        
        # Normalize birthdate to YYYY-MM-DD format if needed
        if birthdate and '.' in birthdate:
            parts = birthdate.split('.')
            if len(parts) == 3:
                birthdate = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        # Insert into database
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO patient (id, first_name, last_name, sex, birthdate) 
               VALUES (?, ?, ?, ?, ?)""",
            (patient_id, (first_name or '').strip(), (last_name or '').strip(), sex or '', birthdate or '')
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
        """
        Retrieve single patient by ID.
        
        Returns all patient data including: id, first_name, last_name, birthdate, sex, created_at
        """
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM patient WHERE id = ?", (patient_id,))
        row = cur.fetchone()
        if row:
            patient_dict = dict(row)
            # Ensure 'id' field is present (primary key)
            if 'id' not in patient_dict:
                patient_dict['id'] = patient_id
            return patient_dict
        return None

    def update_patient(self, patient_id: str, first_name: str = None, last_name: str = None, 
                      birthdate: str = None, sex: str = None) -> bool:
        """
        Update patient data.
        
        Patient ID is immutable (contains birthdate and gender).
        Only first_name, last_name, birthdate, and sex can be updated.
        
        Args:
            patient_id: Patient ID (not changeable)
            first_name: New first name (optional, if None then not updated)
            last_name: New last name (optional, if None then not updated)
            birthdate: New birthdate (optional, if None then not updated)
            sex: New gender (optional, if None then not updated)
        
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ValueError: If trying to update with empty names
        """
        # Validate non-empty fields
        if first_name is not None and not first_name.strip():
            raise ValueError("First name cannot be empty")
        if last_name is not None and not last_name.strip():
            raise ValueError("Last name cannot be empty")
        
        # Build dynamic UPDATE query based on what's being updated
        update_fields = []
        values = []
        
        if first_name is not None:
            update_fields.append("first_name = ?")
            values.append(first_name.strip())
        
        if last_name is not None:
            update_fields.append("last_name = ?")
            values.append(last_name.strip())
        
        if birthdate is not None:
            # Normalize birthdate to YYYY-MM-DD format
            if '.' in birthdate:
                parts = birthdate.split('.')
                if len(parts) == 3:
                    birthdate = f"{parts[2]}-{parts[1]}-{parts[0]}"
            update_fields.append("birthdate = ?")
            values.append(birthdate)
        
        if sex is not None:
            if sex not in ['M', 'W', 'D']:
                sex = 'D'
            update_fields.append("sex = ?")
            values.append(sex)
        
        # If no fields to update, return early
        if not update_fields:
            return True
        
        # Add patient ID to values for WHERE clause
        values.append(patient_id)
        
        # Execute update
        try:
            cur = self.conn.cursor()
            query = f"UPDATE patient SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(query, values)
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            print(f"Error updating patient: {e}")
            return False

    def patient_exists(self, patient_id: str) -> bool:
        """Check if patient with given ID exists."""
        return self.get_patient(patient_id) is not None

    def find_patient_by_name(self, first_name: str, last_name: str) -> Dict[str, Any] | None:
        """
        Find an existing patient by first and last name (case-insensitive).
        
        Args:
            first_name: Patient first name
            last_name: Patient last name
            
        Returns:
            Patient dict if found, None otherwise
        """
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM patient WHERE LOWER(first_name) = LOWER(?) AND LOWER(last_name) = LOWER(?)",
            (first_name.strip(), last_name.strip())
        )
        row = cur.fetchone()
        return dict(row) if row else None

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
        Retrieve all recordings for a specific patient from data/recordings/{patient_id}/.
        
        Each patient has their own folder containing only their video files.
        This ensures recordings are properly isolated per patient.
        
        Scans physical files directly to ensure only actual videos are returned,
        avoiding orphaned database entries.
        
        Returns recordings sorted by modification time (newest first).
        
        Args:
            patient_id: The patient ID (folder name under data/recordings/)
            
        Returns:
            List of recording dicts with keys: id, patientId, date, baseline, file_path
        """
        from pathlib import Path
        
        # Each patient has their own folder
        patient_recordings_dir = Path("data/recordings") / str(patient_id)
        recordings = []
        
        # Build a lookup of baseline flags from the database
        baseline_lookup = {}
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, baseline FROM recording WHERE patientId = ?", (patient_id,))
            for row in cur.fetchall():
                baseline_lookup[row['id']] = row['baseline']
        except Exception:
            pass

        # Scan only this patient's recording folder
        if patient_recordings_dir.exists():
            for video_file in sorted(patient_recordings_dir.glob("*.mp4"), reverse=True):
                file_path = str(video_file)  # Full path to the file
                file_mtime = int(video_file.stat().st_mtime)
                
                # Read baseline flag from database (not from filename)
                is_baseline = baseline_lookup.get(file_path, 0)
                
                recording = {
                    'id': file_path,
                    'patientId': patient_id,
                    'date': file_mtime,
                    'baseline': is_baseline,
                    'file_path': file_path
                }
                recordings.append(recording)
        
        return recordings

    def get_baseline_recording(self, patient_id: str) -> Dict[str, Any] | None:
        """
        Retrieve the baseline recording of a patient.
        
        Baseline recordings are reference measurements for comparisons.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM recording WHERE patientId = ? AND baseline = 1 LIMIT 1", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_baseline_recording(self, patient_id: str, new_baseline_path: str) -> bool:
        """
        Set a recording as the new baseline for a patient.

        Only updates the baseline flag in the database.
        Files are NOT renamed — baseline status is stored exclusively in the DB.

        Args:
            patient_id: Patient ID
            new_baseline_path: Full file path of the recording to promote

        Returns:
            True on success, False on error
        """
        try:
            cur = self.conn.cursor()

            # Demote all current baselines for this patient
            cur.execute(
                "UPDATE recording SET baseline = 0 WHERE patientId = ? AND baseline = 1",
                (patient_id,)
            )

            # Promote the selected recording
            cur.execute(
                "UPDATE recording SET baseline = 1 WHERE id = ? AND patientId = ?",
                (new_baseline_path, patient_id)
            )

            self.conn.commit()
            print(f"[DB] Baseline set: {new_baseline_path}")
            return True

        except Exception as e:
            print(f"[DB] Error setting baseline: {e}")
            self.conn.rollback()
            return False

    def import_from_tbi_headset(
        self, 
        tbi_db_path: str, 
        video_mapping: dict = None,
        on_duplicate_callback: callable = None
    ) -> Dict[str, Any]:
        """
        Import patient data and recordings from TBI_Headset database.
        
        WORKFLOW:
        Phase 1: Read all TBI patients, parse names from TBI ID, check for
                 duplicates by name. Collect user decisions (merge/skip/cancel)
                 before writing anything to the database.
        Phase 2: Create new patients and build id_mapping (TBI ID -> EyeCon ID).
        Phase 3: Import recordings with timestamp-based duplicate detection.
        
        TBI uses the patient name as its ID field (e.g. "Marcel Schepelmann").
        We parse this into first_name/last_name and generate our own UUID-based
        patient ID (XXXX-YYYY-MM-DD-G format).
        
        Args:
            tbi_db_path: Path to TBI Patient database (SQLite)
            video_mapping: Dict mapping video filenames to (patient_id, local_path)
            on_duplicate_callback: Function called on duplicate detection
                                 Signature: callback(existing_patient, tbi_patient)
                                 Returns: 'merge' | 'skip' | 'cancel'
        
        Returns:
            Dict with import statistics and id_mapping for folder management
        """
        if video_mapping is None:
            video_mapping = {}
        
        result = {
            'imported_patients': 0,
            'imported_recordings': 0,
            'skipped_recordings': 0,
            'duplicate_handled': 0,
            'cancelled': False,
            'id_mapping': {},
            'errors': []
        }
        
        try:
            # Open TBI database in read-only mode
            tbi_conn = sqlite3.connect(f'file:{tbi_db_path}?mode=ro', uri=True)
            tbi_conn.row_factory = sqlite3.Row
            tbi_cur = tbi_conn.cursor()
            
            # === PHASE 1: COLLECT PATIENT DECISIONS (no DB writes) ===
            # decisions: list of (tbi_id, decision, patient_dict, existing_patient)
            decisions = []
            
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
                        
                        # TBI uses patient name as ID — parse into first/last name
                        name_parts = str(tbi_id).strip().split(' ', 1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else name_parts[0]
                        
                        # Store parsed names in dict for later use
                        patient_dict['_parsed_first_name'] = first_name
                        patient_dict['_parsed_last_name'] = last_name
                        
                        birthdate = patient_dict.get('birthdate') or ''
                        sex = patient_dict.get('sex') or ''
                        
                        # Normalize sex to M/W/D
                        sex_map = {
                            'M': 'M', 'W': 'W', 'D': 'D',
                            'MALE': 'M', 'FEMALE': 'W', 'DIVERSE': 'D'
                        }
                        sex = sex_map.get(str(sex).upper(), '') if sex else ''
                        patient_dict['_normalized_sex'] = sex
                        patient_dict['_normalized_birthdate'] = birthdate
                        
                        # Check for existing patient: first by TBI ID (same ID from
                        # previous import), then by name match
                        existing_patient = None
                        if self.patient_exists(tbi_id):
                            existing_patient = self.get_patient(tbi_id)
                        else:
                            existing_patient = self.find_patient_by_name(first_name, last_name)
                        
                        if existing_patient:
                            # Duplicate detected — ask user
                            if on_duplicate_callback:
                                decision = on_duplicate_callback(existing_patient, patient_dict)
                            else:
                                decision = 'skip'
                            
                            if decision == 'cancel':
                                result['cancelled'] = True
                                tbi_conn.close()
                                return result
                            
                            decisions.append((tbi_id, decision, patient_dict, existing_patient))
                        else:
                            # New patient — will be created in Phase 2
                            decisions.append((tbi_id, 'new', patient_dict, None))
                        
                    except Exception as e:
                        result['errors'].append(f"Error processing patient {patient_dict.get('id', '?')}: {str(e)}")
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI patients: {str(e)}")
            
            # === PHASE 2: CREATE PATIENTS AND BUILD ID MAPPING ===
            # id_mapping: TBI patient_id -> EyeCon patient_id
            id_mapping = {}
            
            for tbi_id, decision, patient_dict, existing_patient in decisions:
                try:
                    first_name = patient_dict['_parsed_first_name']
                    last_name = patient_dict['_parsed_last_name']
                    birthdate = patient_dict['_normalized_birthdate']
                    sex = patient_dict['_normalized_sex']
                    
                    if decision == 'merge':
                        # Reuse existing patient — only add new recordings later
                        id_mapping[tbi_id] = existing_patient['id']
                        result['duplicate_handled'] += 1
                        
                    elif decision == 'new':
                        # Use TBI ID directly as patient ID in our system
                        self.create_patient(
                            birthdate=birthdate,
                            sex=sex,
                            first_name=first_name,
                            last_name=last_name,
                            patient_id=tbi_id  # Keep TBI ID as-is
                        )
                        id_mapping[tbi_id] = tbi_id
                        result['imported_patients'] += 1
                        
                    else:
                        # Skip — do not add to id_mapping
                        continue
                        
                except Exception as e:
                    result['errors'].append(f"Error creating patient {tbi_id}: {str(e)}")
            
            result['id_mapping'] = id_mapping
            
            # === PHASE 3: IMPORT RECORDINGS (with timestamp dedup) ===
            try:
                tbi_cur.execute("SELECT * FROM Recording")
                tbi_recordings = tbi_cur.fetchall()
                
                for tbi_recording in tbi_recordings:
                    try:
                        recording_dict = dict(tbi_recording)
                        
                        tbi_recording_id = recording_dict.get('id')
                        tbi_patient_id = recording_dict.get('patientId')
                        date = recording_dict.get('date') or 0
                        baseline = recording_dict.get('baseline') or 0
                        
                        # Skip recordings for patients not in id_mapping (skipped patients)
                        if tbi_patient_id not in id_mapping:
                            result['skipped_recordings'] += 1
                            continue
                        
                        eyecon_patient_id = id_mapping[tbi_patient_id]
                        
                        # TBI stores dates in milliseconds — convert to seconds
                        date_seconds = int(date)
                        if date_seconds > 9999999999:
                            date_seconds = date_seconds // 1000
                        
                        # Convert Android file path to local filename
                        tbi_filename = str(tbi_recording_id).split("/")[-1]
                        
                        # Only import recordings that have a physical video file
                        if tbi_filename not in video_mapping:
                            result['skipped_recordings'] += 1
                            continue
                        
                        tbi_video_patient_id, local_recording_id = video_mapping[tbi_filename]
                        
                        # Skip if recording ID already exists in database
                        existing_rec = self.conn.execute(
                            "SELECT COUNT(*) FROM recording WHERE id = ?",
                            (local_recording_id,)
                        ).fetchone()[0]
                        if existing_rec > 0:
                            result['skipped_recordings'] += 1
                            continue
                        
                        # Timestamp-based duplicate check: skip if recording with
                        # same date already exists for this patient
                        if date_seconds > 0:
                            existing_count = self.conn.execute(
                                "SELECT COUNT(*) FROM recording WHERE patientId = ? AND date = ?",
                                (eyecon_patient_id, date_seconds)
                            ).fetchone()[0]
                            if existing_count > 0:
                                result['skipped_recordings'] += 1
                                continue
                        
                        # Insert recording into our database
                        self.add_recording(
                            recording_id=local_recording_id,
                            patient_id=eyecon_patient_id,
                            date=date_seconds,
                            baseline=1 if baseline else 0
                        )
                        
                        result['imported_recordings'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Error importing recording: {str(e)}")
                        result['skipped_recordings'] += 1
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI recordings: {str(e)}")
            
            tbi_conn.close()
            
        except Exception as e:
            result['errors'].append(f"Failed to open TBI database: {str(e)}")
        
        return result
    
    # ========== NEW: Pupil Analysis Methods ==========
    
    def save_pupil_frames(self, recording_id: str, pupil_frames: List[Dict[str, Any]]) -> int:
        """
        Save pupil detection results (per-frame) to database.
        
        Args:
            recording_id: Recording ID to associate frames with
            pupil_frames: List of frame dicts with keys:
                         {frame_number, timestamp, diameter_px, position_x, position_y, confidence, eye_area_px}
        
        Returns:
            Number of frames successfully saved
        """
        if not self.conn:
            return 0
        
        cursor = self.conn.cursor()
        saved_count = 0
        
        try:
            for frame_data in pupil_frames:
                cursor.execute("""
                    INSERT OR REPLACE INTO pupil_frame
                    (recording_id, frame_number, timestamp, diameter_px, position_x, position_y, confidence, eye_area_px)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recording_id,
                    frame_data.get('frame_number'),
                    frame_data.get('timestamp'),
                    frame_data.get('diameter_px'),
                    frame_data.get('position_x'),
                    frame_data.get('position_y'),
                    frame_data.get('confidence'),
                    frame_data.get('eye_area_px')
                ))
                saved_count += 1
            
            self.conn.commit()
        except Exception as e:
            print(f"Error saving pupil frames: {e}")
            self.conn.rollback()
        
        return saved_count
    
    def save_plr_metrics(
        self,
        recording_id: str,
        metrics: Dict[str, Any],
        light_stimulus_start_frame: int,
        light_stimulus_end_frame: int
    ) -> bool:
        """
        Save calculated PLR biomarkers to database.
        
        Args:
            recording_id: Recording ID
            metrics: Dict with PLR parameters (from PLRMetrics dataclass)
            light_stimulus_start_frame: Frame index of stimulus start
            light_stimulus_end_frame: Frame index of stimulus end
        
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO plr_metrics (
                    recording_id,
                    baseline_mean, baseline_max, baseline_min,
                    latency, latency_frame_idx,
                    peak_constriction_velocity, peak_constriction_velocity_frame,
                    average_constriction_velocity,
                    minimum_diameter, minimum_diameter_frame, amplitude,
                    peak_dilation_velocity, peak_dilation_velocity_frame,
                    average_dilation_velocity,
                    prt_50, prt_63, prt_75,
                    light_stimulus_start_frame, light_stimulus_end_frame
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recording_id,
                metrics.get('baseline_mean'),
                metrics.get('baseline_max'),
                metrics.get('baseline_min'),
                metrics.get('latency'),
                metrics.get('latency_frame_idx'),
                metrics.get('peak_constriction_velocity'),
                metrics.get('peak_constriction_velocity_frame'),
                metrics.get('average_constriction_velocity'),
                metrics.get('minimum_diameter'),
                metrics.get('minimum_diameter_frame'),
                metrics.get('amplitude'),
                metrics.get('peak_dilation_velocity'),
                metrics.get('peak_dilation_velocity_frame'),
                metrics.get('average_dilation_velocity'),
                metrics.get('prt_50'),
                metrics.get('prt_63'),
                metrics.get('prt_75'),
                light_stimulus_start_frame,
                light_stimulus_end_frame
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving PLR metrics: {e}")
            self.conn.rollback()
            return False
    
    def get_pupil_frames(self, recording_id: str) -> List[Dict[str, Any]]:
        """Retrieve all pupil frames for a recording."""
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT frame_number, timestamp, diameter_px, position_x, position_y, confidence, eye_area_px
            FROM pupil_frame
            WHERE recording_id = ?
            ORDER BY frame_number ASC
        """, (recording_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_plr_metrics(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve PLR metrics for a recording."""
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM plr_metrics WHERE recording_id = ?
        """, (recording_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def create_analysis_session(
        self,
        recording_id: str,
        frame_count: int,
        analyzed_frame_count: int,
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> int:
        """Create analysis session record for tracking."""
        if not self.conn:
            return -1
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO analysis_session
                (recording_id, frame_count, analyzed_frame_count, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (recording_id, frame_count, analyzed_frame_count, status, error_message))
            
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creating analysis session: {e}")
            self.conn.rollback()
            return -1

