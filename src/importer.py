"""
TBI_Headset Database Importer

Handles ZIP import workflow:
1. Open ZIP file dialog
2. Extract ZIP to temporary directory
3. Import patient_database.db to EyeCon database
4. Clean up temporary files
"""

import zipfile
import tempfile
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

from PySide6.QtWidgets import QFileDialog, QMessageBox
from src.db import PatientDataManager
from src.patients_dialog import DuplicatePatientDialog

# Setup logging
logger = logging.getLogger(__name__)
class TBIHeadsetImporter:
    """Import patient data from TBI_Headset database exports (ZIP format)."""

    def __init__(self, eyecon_db_manager: PatientDataManager, parent_widget=None):
        """
        Initialize importer.
        
        Args:
            eyecon_db_manager: PatientDataManager instance for target database
            parent_widget: Parent widget for dialogs (e.g., main window)
        """
        self.db_manager = eyecon_db_manager
        self.parent_widget = parent_widget
        self.temp_dir = None

    def show_file_dialog(self, parent=None) -> str | None:
        """
        Open file dialog for ZIP selection.
        
        Returns:
            Path to selected ZIP file, or None if cancelled
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select TBI_Headset Export ZIP",
            "",
            "ZIP Files (*.zip);;All Files (*)"
        )
        return file_path if file_path else None

    def extract_zip(self, zip_path: str) -> str | None:
        """
        Extract ZIP file to temporary directory.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Path to temporary extraction directory, or None on error
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="eyecon_import_")
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            return self.temp_dir
            
        except zipfile.BadZipFile:
            return None
        except Exception as e:
            print(f"Error extracting ZIP: {e}")
            return None

    def find_patient_database(self, temp_dir: str) -> str | None:
        """
        Find patient_database.db in extracted directory.
        
        Searches recursively for 'patient_database.db' in the extraction directory.
        
        Args:
            temp_dir: Path to extraction directory
            
        Returns:
            Path to patient_database.db, or None if not found
        """
        temp_path = Path(temp_dir)
        
        # Search for database file recursively
        for db_file in temp_path.rglob('patient_database.db'):
            return str(db_file)
        
        return None

    def copy_recordings_to_project(self, temp_dir: str) -> Tuple[Dict[str, str], list]:
        """
        Copy video files from TBI export to project recordings folder with patient-based organization.
        
        Workflow:
        1. Find patient_database.db and read recording→patient mappings
        2. For each video in recordings/ folder:
           - Find patient_id from recording table
           - Extract video timestamp from metada or creation time
           - Rename to {timestamp}_scan_X.mp4 format
           - Copy to data/recordings/{patient_id}/
        3. Detect collisions: same timestamp → overwrite (same video re-imported)
        
        Returns:
            Tuple (mapping: dict of recording_id→(patient_id, local_path), errors: list)
        """
        mapping = {}
        errors = []
        
        try:
            # Create base recordings directory
            recordings_dir = Path("data/recordings")
            recordings_dir.mkdir(parents=True, exist_ok=True)
            
            # Find TBI recordings directory in extracted ZIP
            tbi_recordings_dir = Path(temp_dir) / "recordings"
            if not tbi_recordings_dir.exists():
                errors.append(f"No 'recordings' directory found in ZIP at {tbi_recordings_dir}")
                return mapping, errors
            
            # Step 1: Read TBI database to get recording→patient mappings
            db_path = self.find_patient_database(temp_dir)
            if not db_path:
                errors.append("patient_database.db not found - cannot determine patient-video mappings")
                return mapping, errors
            
            # Open TBI database to read recordings and patient associations
            import sqlite3
            tbi_conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
            tbi_conn.row_factory = sqlite3.Row
            tbi_cur = tbi_conn.cursor()
            
            # Map: video_filename → (patient_id, baseline_flag)
            video_patient_map = {}
            
            try:
                # Read recordings from TBI database
                tbi_cur.execute("SELECT * FROM recording")
                tbi_recordings = tbi_cur.fetchall()
                
                for tbi_rec in tbi_recordings:
                    rec_dict = dict(tbi_rec)
                    video_id = rec_dict.get('id')  # Usually filename like "scan_001.mp4"
                    patient_id = rec_dict.get('patientId')
                    baseline = rec_dict.get('baseline', 0)
                    
                    if video_id and patient_id:
                        video_patient_map[video_id] = (str(patient_id), int(baseline))
                
            except Exception as e:
                errors.append(f"Error reading TBI recording table: {str(e)}")
            finally:
                tbi_conn.close()
            
            # Step 2: Copy videos with timestamp-based naming to patient folders
            scan_counters = {}  # Track scan numbers per patient
            
            for video_file in tbi_recordings_dir.rglob("*"):
                if video_file.is_file() and video_file.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv"]:
                    try:
                        video_filename = video_file.name
                        
                        # Get patient_id and baseline flag from database
                        patient_id, is_baseline = video_patient_map.get(video_filename, (None, 0))
                        
                        if not patient_id:
                            errors.append(f"Video {video_filename} not found in TBI recording table, skipping")
                            continue
                        
                        # Create patient-specific directory
                        patient_recordings_dir = recordings_dir / str(patient_id)
                        patient_recordings_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Extract timestamp from file creation time (Unix timestamp)
                        # Use current time if metadata not available
                        unix_timestamp = int(video_file.stat().st_mtime)
                        
                        # Generate new filename with timestamp
                        if is_baseline:
                            # Baseline: {timestamp}_baseline.mp4
                            new_filename = f"{unix_timestamp}_baseline.mp4"
                        else:
                            # Normal scan: {timestamp}_scan_{counter}.mp4
                            if patient_id not in scan_counters:
                                scan_counters[patient_id] = 1
                            else:
                                scan_counters[patient_id] += 1
                            
                            new_filename = f"{unix_timestamp}_scan_{scan_counters[patient_id]}.mp4"
                        
                        local_path = patient_recordings_dir / new_filename
                        
                        # Copy file (overwrites if same timestamp)
                        shutil.copy2(video_file, local_path)
                        
                        # Store mapping: original_id → (patient_id, local_path)
                        mapping[str(video_filename)] = (str(patient_id), str(local_path))
                        
                        logger.info(f"Copied {video_filename} → {patient_id}/{new_filename}")
                        
                    except Exception as e:
                        errors.append(f"Failed to copy {video_file.name}: {str(e)}")
            
            if not mapping:
                errors.append("No video files found in recordings/ directory")
            
        except Exception as e:
            errors.append(f"Error copying recordings: {str(e)}")
            logger.error(f"Error in copy_recordings_to_project: {e}")
        
        return mapping, errors

    def handle_duplicate_patient(self, existing_patient: dict, tbi_patient: dict) -> str:
        """
        Handle duplicate patient detection during import.
        
        Shows DuplicatePatientDialog and returns user's decision.
        
        Args:
            existing_patient: Patient record already in our system
            tbi_patient: Patient record from TBI import
            
        Returns:
            'merge': Use existing patient, add recordings from TBI
            'create_new': Create new patient with our standard ID format + TBI data
            'skip': Don't import this patient
        """
        try:
            dialog = DuplicatePatientDialog(existing_patient, tbi_patient, parent=self.parent_widget)
            dialog.exec()
            decision = dialog.get_decision()
            return decision if decision else 'skip'
        except Exception as e:
            print(f"Error in duplicate patient dialog: {e}")
            return 'skip'

    def import_from_zip(self, zip_path: str, parent=None) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete import workflow: extract ZIP, copy videos, import database, cleanup.
        
        Workflow:
        1. Extract ZIP to temporary directory
        2. Copy videos from recordings/ to data/recordings/
        3. Find patient_database.db in extraction
        4. Import data to EyeCon database (with callback for duplicate handling)
        5. Clean up temporary files
        6. Show result dialog
        
        Args:
            zip_path: Path to ZIP file
            parent: Parent widget for dialogs
            
        Returns:
            Tuple (success: bool, result: dict with import statistics)
        """
        # Store parent for use in callbacks
        if parent:
            self.parent_widget = parent
            
        result = {
            'imported_patients': 0,
            'imported_recordings': 0,
            'duplicate_handled': 0,
            'errors': []
        }

        try:
            # Step 1: Extract ZIP
            temp_dir = self.extract_zip(zip_path)
            if not temp_dir:
                result['errors'].append("Failed to extract ZIP file")
                return False, result
            
            # Step 2: Copy videos to project
            video_mapping, copy_errors = self.copy_recordings_to_project(temp_dir)
            result['errors'].extend(copy_errors)
            
            # Step 3: Find database in extracted files
            db_path = self.find_patient_database(temp_dir)
            if not db_path:
                result['errors'].append("patient_database.db not found in ZIP")
                self.cleanup()
                return False, result
            
            # Step 4: Import database with duplicate callback handler
            import_result = self.db_manager.import_from_tbi_headset(
                db_path, 
                video_mapping,
                on_duplicate_callback=self.handle_duplicate_patient
            )
            result['imported_patients'] = import_result['imported_patients']
            result['imported_recordings'] = import_result['imported_recordings']
            result['duplicate_handled'] = import_result.get('duplicate_handled', 0)
            result['errors'].extend(import_result['errors'])
            
            return True, result
            
        except Exception as e:
            result['errors'].append(f"Unexpected error during import: {str(e)}")
            return False, result
            
        finally:
            # Step 5: Clean up temporary files
            self.cleanup()

    def cleanup(self):
        """Remove temporary extraction directory."""
        if self.temp_dir and Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not delete temporary directory: {e}")

    def show_result_dialog(self, parent, success: bool, result: Dict[str, Any]):
        """
        Show import result dialog with statistics and errors.
        
        Args:
            parent: Parent widget for dialog
            success: Whether import was successful
            result: Dictionary with import statistics
        """
        if success:
            message = f"""
Import successful!

Patients imported: {result['imported_patients']}
Recordings imported: {result['imported_recordings']}
"""
            if result['errors']:
                message += f"\nWarnings ({len(result['errors'])}):\n"
                for error in result['errors'][:5]:  # Show max 5 errors
                    message += f"- {error}\n"
                if len(result['errors']) > 5:
                    message += f"... and {len(result['errors']) - 5} more"
                
                QMessageBox.warning(parent, "Import Completed with Warnings", message)
            else:
                QMessageBox.information(parent, "Import Successful", message)
        else:
            error_message = f"Import failed!\n\nErrors:\n"
            for error in result['errors']:
                error_message += f"- {error}\n"
            
            QMessageBox.critical(parent, "Import Failed", error_message)
