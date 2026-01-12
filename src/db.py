from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    name TEXT NOT NULL,
    nachname TEXT NOT NULL,
    geburtsdatum TEXT,
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
        # Datenbank initialisieren und Tabellen erstellen
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def create_patient(
        self,
        name: str,
        nachname: str,
        geburtsdatum: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> int:
        # Neuen Patienten anlegen und ID zurückgeben
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO patient (name, nachname, geburtsdatum, external_id) VALUES (?, ?, ?, ?)",
                (name, nachname, geburtsdatum, external_id)
            )
            conn.commit()
            return cur.lastrowid

    def get_all_patients(self) -> list[dict]:
        # Alle Patienten auflisten, sortiert nach Nachname, dann Name
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, name, nachname, geburtsdatum, external_id, created_at FROM patient ORDER BY nachname, name"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_patient(self, patient_id: int) -> dict | None:
        # Einzelnen Patienten auslesen
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, name, nachname, geburtsdatum, external_id, created_at FROM patient WHERE id = ?",
                (patient_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_patient(
        self,
        patient_id: int,
        name: Optional[str] = None,
        nachname: Optional[str] = None,
        geburtsdatum: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> bool:
        # Patientendaten aktualisieren
        with self.connect() as conn:
            updates = []
            values = []

            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if nachname is not None:
                updates.append("nachname = ?")
                values.append(nachname)
            if geburtsdatum is not None:
                updates.append("geburtsdatum = ?")
                values.append(geburtsdatum)
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
        # Patient und seine Messungen löschen
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
        # Neue Messung hinzufügen
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO measurement (patient_id, data, is_baseline) VALUES (?, ?, ?)",
                (patient_id, data, 1 if is_baseline else 0)
            )
            conn.commit()
            return cur.lastrowid

    def get_measurements(self, patient_id: int) -> list[dict]:
        # Alle Messungen eines Patienten auslesen
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, patient_id, recorded_at, is_baseline, data FROM measurement WHERE patient_id = ? ORDER BY recorded_at DESC",
                (patient_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_baseline_measurement(self, patient_id: int) -> dict | None:
        # Neueste Baseline-Messung eines Patienten
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id, patient_id, recorded_at, is_baseline, data FROM measurement WHERE patient_id = ? AND is_baseline = 1 ORDER BY recorded_at DESC LIMIT 1",
                (patient_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
