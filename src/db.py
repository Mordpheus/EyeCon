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
                print(f"⚠️  Could not clear old test data: {e}")

    def create_patient(self, birthdate: str, sex: str, first_name: str = "", last_name: str = "", patient_id: str = None) -> str:
        """
        Create new patient record.
        
        IMPORTANT: first_name and last_name are REQUIRED (not optional)
        Names are stored separately and not used in ID generation.
        Patient ID is either generated from birthdate + sex, or provided directly.
        
        Args:
            birthdate: Patient birthdate in format YYYY-MM-DD or DD.MM.YYYY
            sex: Single character gender: M (male), W (female), D (diverse)
            first_name: Patient first name (REQUIRED - must not be empty)
            last_name: Patient last name (REQUIRED - must not be empty)
            patient_id: Optional. If provided, use this ID directly (for TBI imports).
                       If None, generate standard XXXX-YYYY-MM-DD-G format.
        
        Returns:
            Patient ID (either generated or provided as parameter)
            
        Raises:
            ValueError: If first_name or last_name is empty
        """
        # Validate that names are provided (not empty)
        if not first_name or not first_name.strip():
            raise ValueError("First name is required and cannot be empty")
        if not last_name or not last_name.strip():
            raise ValueError("Last name is required and cannot be empty")
        
        # Generate or use provided patient ID
        if patient_id is None:
            patient_id = self.generate_patient_id(birthdate, sex)
        # else: use TBI ID directly as-is (no format validation)
        
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
            (patient_id, first_name.strip(), last_name.strip(), sex, birthdate)
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
        
        # Scan only this patient's recording folder
        if patient_recordings_dir.exists():
            for video_file in sorted(patient_recordings_dir.glob("*.mp4"), reverse=True):
                # Create recording info from file
                rec_id = video_file.stem  # Filename without .mp4
                file_path = str(video_file)  # Full path to the file
                file_mtime = int(video_file.stat().st_mtime)
                
                # Determine if baseline based on filename pattern
                is_baseline = 1 if "baseline" in rec_id else 0
                
                recording = {
                    'id': file_path,  # CRITICAL: Use full file path, not just filename!
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
        2. Use TBI patient ID directly (no format conversion)
        3. Check for duplicates (patient with same TBI ID already exists):
           - If found: Call on_duplicate_callback(existing_patient, tbi_patient)
           - Callback returns: 'merge' (combine recordings), 'create_new' (new patient with our ID format),
             or 'skip' (don't import)
        4. Read all recordings and map to patients
        5. Convert Android paths to local recording IDs (YYYY-MM-DD-HH-MM-SS format)
        6. Insert all data into database
        
        Args:
            tbi_db_path: Path to TBI Patient database (SQLite)
            video_mapping: Dict mapping Android filenames to local paths (optional)
            on_duplicate_callback: Function called on duplicate detection
                                 Signature: on_duplicate_callback(existing_patient, tbi_patient) 
                                 Returns: 'merge'|'create_new'|'skip'
        
        Returns:
            Dict with import statistics:
                - imported_patients: New patients created
                - imported_recordings: Recordings added
                - skipped_recordings: Recordings not imported
                - duplicate_handled: Existing patients with merged recordings
                - errors: List of error messages
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
            # id_mapping: TBI patient_id → EyeCon patient_id (stored patient ID in our system)
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
                        
                        # Extract names and metadata from TBI patient
                        first_name = patient_dict.get('firstName') or patient_dict.get('first_name') or 'Unknown'
                        last_name = patient_dict.get('lastName') or patient_dict.get('last_name') or 'Unknown'
                        birthdate = patient_dict.get('birthdate') or '1990-01-01'
                        sex = patient_dict.get('sex') or 'D'
                        
                        # Normalize sex to M/W/D
                        sex_map = {'M': 'M', 'W': 'W', 'D': 'D', 'male': 'M', 'female': 'W', 'diverse': 'D'}
                        sex = sex_map.get(str(sex).upper(), 'D')
                        
                        # Check if patient already exists with this TBI ID
                        if self.patient_exists(tbi_id):
                            # Patient with this TBI ID already exists in our system
                            existing_patient = self.get_patient(tbi_id)
                            
                            if on_duplicate_callback:
                                decision = on_duplicate_callback(existing_patient, patient_dict)
                            else:
                                # Default: skip if no callback provided
                                decision = 'skip'
                            
                            if decision == 'merge':
                                # Reuse existing patient ID - add new recordings to them
                                id_mapping[tbi_id] = tbi_id
                                result['duplicate_handled'] += 1
                            elif decision == 'create_new':
                                # Create new patient with OUR standard ID format (XXXX-YYYY-MM-DD-G)
                                # Use TBI data but our ID generation
                                new_patient_id = self.create_patient(
                                    birthdate=birthdate,
                                    sex=sex,
                                    first_name=first_name,
                                    last_name=last_name,
                                    patient_id=None  # Generate standard format ID
                                )
                                id_mapping[tbi_id] = new_patient_id
                                result['imported_patients'] += 1
                            else:
                                # Skip this patient
                                result['errors'].append(f"TBI patient {tbi_id}: User chose to skip import")
                                continue
                        else:
                            # New patient (no TBI ID collision) - create with TBI ID directly
                            self.create_patient(
                                birthdate=birthdate,
                                sex=sex,
                                first_name=first_name,
                                last_name=last_name,
                                patient_id=tbi_id  # Use TBI ID as-is, no format conversion
                            )
                            id_mapping[tbi_id] = tbi_id
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
                        
                        # === CONVERT RECORDING ID: Android path → Local schema ===
                        # TBI recording_id often contains Android file path (e.g., /sdcard/video.mp4)
                        # Extract filename and convert to our schema YYYY-MM-DD-HH-MM-SS
                        
                        tbi_filename = str(tbi_recording_id).split("/")[-1]  # Get filename only
                        
                        if tbi_filename in video_mapping:
                            # NEW: Use new mapping format (patient_id, local_path)
                            tbi_video_patient_id, local_recording_id = video_mapping[tbi_filename]
                            # Verify mapping patient matches recording patient
                            if tbi_video_patient_id != tbi_patient_id:
                                result['errors'].append(f"Recording {tbi_recording_id}: Patient mismatch in video mapping")
                                result['skipped_recordings'] += 1
                                continue
                        else:
                            # Generate recording ID from timestamp if not mapped
                            local_recording_id = self.generate_recording_id(date if date > 0 else None)
                        
                        # Insert recording into our system
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

