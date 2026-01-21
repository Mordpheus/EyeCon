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
from pathlib import Path
from typing import Dict, Any, Tuple

from PySide6.QtWidgets import QFileDialog, QMessageBox
from src.db import PatientDataManager


class TBIHeadsetImporter:
    """Import patient data from TBI_Headset database exports (ZIP format)."""

    def __init__(self, eyecon_db_manager: PatientDataManager):
        """
        Initialize importer.
        
        Args:
            eyecon_db_manager: PatientDataManager instance for target database
        """
        self.db_manager = eyecon_db_manager
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
        Copy video files from TBI export to project recordings folder.
        
        Finds all videos in TBI recordings/ folder and copies them to data/recordings/.
        Maps original TBI recording IDs to new local file paths.
        
        Args:
            temp_dir: Path to extraction directory containing recordings/
            
        Returns:
            Tuple (mapping: dict of recording_id→local_path, errors: list)
        """
        mapping = {}
        errors = []
        
        try:
            # Create recordings directory if it doesn't exist
            recordings_dir = Path("data/recordings")
            recordings_dir.mkdir(parents=True, exist_ok=True)
            
            # Find recordings directory in extracted ZIP
            tbi_recordings_dir = Path(temp_dir) / "recordings"
            if not tbi_recordings_dir.exists():
                errors.append(f"No 'recordings' directory found in ZIP at {tbi_recordings_dir}")
                return mapping, errors
            
            # Copy all video files from recordings/ to data/recordings/
            for video_file in tbi_recordings_dir.rglob("*"):
                if video_file.is_file() and video_file.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv"]:
                    try:
                        # Use recording filename as key
                        local_path = recordings_dir / video_file.name
                        
                        # Copy file to project
                        shutil.copy2(video_file, local_path)
                        
                        # Store mapping: original ID → local path
                        mapping[str(video_file.name)] = str(local_path)
                        
                    except Exception as e:
                        errors.append(f"Failed to copy {video_file.name}: {str(e)}")
            
            if not mapping:
                errors.append("No video files found in recordings/ directory")
            
        except Exception as e:
            errors.append(f"Error copying recordings: {str(e)}")
        
        return mapping, errors

    def import_from_zip(self, zip_path: str, parent=None) -> Tuple[bool, Dict[str, Any]]:
        """
        Complete import workflow: extract ZIP, copy videos, import database, cleanup.
        
        Workflow:
        1. Extract ZIP to temporary directory
        2. Copy videos from recordings/ to data/measurements/
        3. Find patient_database.db in extraction
        4. Import data to EyeCon database (with updated local video paths)
        5. Clean up temporary files
        6. Show result dialog
        
        Args:
            zip_path: Path to ZIP file
            parent: Parent widget for dialogs
            
        Returns:
            Tuple (success: bool, result: dict with import statistics)
        """
        result = {
            'imported_patients': 0,
            'imported_recordings': 0,
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
            
            # Step 4: Import database (pass video mapping so DB can use local paths)
            import_result = self.db_manager.import_from_tbi_headset(db_path, video_mapping)
            result['imported_patients'] = import_result['imported_patients']
            result['imported_recordings'] = import_result['imported_recordings']
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
