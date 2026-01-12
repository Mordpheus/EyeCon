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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                birthdate TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Create measurement table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS measurement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_baseline BOOLEAN DEFAULT 0,
                data TEXT,
                FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE
            )
            """
        )

        self.conn.commit()

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

            # Add sample baseline measurement for first patient
            cur.execute(
                "INSERT INTO measurement (patient_id, is_baseline, data) VALUES (?, ?, ?)",
                (patient_id_1, 1, '{"pupil_size": 5.2, "timestamp": 0}')
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
        """Delete patient and all associated measurements."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM patient WHERE id = ?", (patient_id,))
        self.conn.commit()

    def add_measurement(self, patient_id: int, data: str, is_baseline: bool = False) -> int:
        """Add new measurement for patient."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO measurement (patient_id, is_baseline, data) VALUES (?, ?, ?)",
            (patient_id, is_baseline, data)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_measurements(self, patient_id: int) -> List[Dict[str, Any]]:
        """Get all measurements for a patient."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM measurement WHERE patient_id = ? ORDER BY recorded_at DESC", (patient_id,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    def get_baseline_measurement(self, patient_id: int) -> Dict[str, Any] | None:
        """Get baseline measurement for patient."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM measurement WHERE patient_id = ? AND is_baseline = 1 LIMIT 1", (patient_id,))
        row = cur.fetchone()
        return dict(row) if row else None
