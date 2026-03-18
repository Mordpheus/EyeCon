"""
Data management for patients

This module provides a simple wrapper around the SQLite database
for patient and measurement data management.
"""
from pathlib import Path
from src.db import PatientDataManager as DBPatientDataManager


# For backward compatibility, we expose the DB wrapper as PatientDataManager
# The actual implementation is in src.db
PatientDataManager = DBPatientDataManager

