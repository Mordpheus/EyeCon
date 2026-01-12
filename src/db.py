from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birthdate TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS measurement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    recorded_at TEXT DEFAULT (datetime('now')),
    is_baseline INTEGER DEFAULT 0,
    data TEXT,
    FOREIGN KEY(patient_id) REFERENCES patient(id)
);
"""


class PatientDataManager:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path.as_posix())
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        # Initialize database and create schema tables
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def create_patient(
        self,
        first_name: str,
        last_name: str,
        birthdate: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> int:
        # Create new patient and return ID
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO patient (first_name, last_name, birthdate, external_id) VALUES (?, ?, ?, ?)",
                (first_name, last_name, birthdate, external_id)
            )
            conn.commit()
            return cur.lastrowid

    def get_all_patients(self) -> list[dict]:
        # Fetch all patients, sorted by last name then first name
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, first_name, last_name, birthdate, external_id, created_at FROM patient ORDER BY last_name, first_name"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_patient(self, patient_id: int) -> dict | None:
        # Fetch single patient by ID
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, first_name, last_name, birthdate, external_id, created_at FROM patient WHERE id = ?",
                (patient_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_patient(
        self,
        patient_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        birthdate: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> bool:
        # Update patient data
        with self.connect() as conn:
            updates = []
            values = []

            if first_name is not None:
                updates.append("first_name = ?")
                values.append(first_name)
            if last_name is not None:
                updates.append("last_name = ?")
                values.append(last_name)
            if birthdate is not None:
                updates.append("birthdate = ?")
                values.append(birthdate)
            if external_id is not None:
                updates.append("external_id = ?")
                values.append(external_id)

            if not updates:
                return False

            values.append(patient_id)
            sql = f"UPDATE patient SET {', '.join(updates)} WHERE id = ?"
            cur = conn.execute(sql, tuple(values))
            conn.commit()
            return cur.rowcount > 0

    def delete_patient(self, patient_id: int) -> bool:
        # Delete patient and associated measurements
        with self.connect() as conn:
            conn.execute("DELETE FROM measurement WHERE patient_id = ?", (patient_id,))
            cur = conn.execute("DELETE FROM patient WHERE id = ?", (patient_id,))
            conn.commit()
            return cur.rowcount > 0

    def add_measurement(
        self,
        patient_id: int,
        data: str,
        is_baseline: bool = False
    ) -> int:
        # Add new measurement for patient
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO measurement (patient_id, data, is_baseline) VALUES (?, ?, ?)",
                (patient_id, data, 1 if is_baseline else 0)
            )
            conn.commit()
            return cur.lastrowid

    def get_measurements(self, patient_id: int) -> list[dict]:
        # Fetch all measurements for patient, newest first
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, patient_id, recorded_at, is_baseline, data FROM measurement WHERE patient_id = ? ORDER BY recorded_at DESC",
                (patient_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_baseline_measurement(self, patient_id: int) -> dict | None:
        # Fetch most recent baseline measurement for patient
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, patient_id, recorded_at, is_baseline, data FROM measurement WHERE patient_id = ? AND is_baseline = 1 ORDER BY recorded_at DESC LIMIT 1",
                (patient_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
