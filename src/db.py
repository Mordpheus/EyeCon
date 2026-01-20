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

        # === RECORDING TABELLE ===
        # Speichert Messdaten/Aufnahmen direkt in SQLite (kompatibel mit TBI_Headset)
        # NICHT mehr wie früher measurement mit JSON-Wrapper!
        # 
        # Spalten:
        #   id (TEXT PK)      - Eindeutige ID der Aufnahme (kommt von TBI_Headset)
        #   patientId (INT)   - Fremdschlüssel zu patient.id (Mit Cascade Delete)
        #   date (INT)        - Unix Timestamp wann die Aufnahme gemacht wurde
        #   baseline (INT)    - Flag: 0=normale Messung, 1=Baseline-Messung
        #
        # WICHTIG: Keine JSON-Daten mehr! Alles ist direkt in SQLite gespeichert.
        #          Das macht Queries einfacher und schneller.
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
        Speichert eine neue Aufnahme/Messung in der Datenbank.
        
        Diese Methode schreibt direkt in die recording-Tabelle (nicht mehr measurement!)
        Eine Aufnahme besteht aus:
        - recording_id: Eindeutige Text-ID (z.B. von TBI_Headset import)
        - patient_id: Welcher Patient diese Aufnahme gemacht hat
        - date: Unix Timestamp (Sekunden seit 1970) wann aufgenommen
        - baseline: 1=Baseline (Referenzmessung), 0=normale Messung
        
        Datenbankoperation: INSERT INTO recording
        Rückgabe: Die gespeicherte recording_id
        """
        cur = self.conn.cursor()
        # INSERT: Neue Zeile in recording-Tabelle mit allen 4 Spalten
        cur.execute(
            "INSERT INTO recording (id, patientId, date, baseline) VALUES (?, ?, ?, ?)",
            (recording_id, patient_id, date, baseline)
        )
        # COMMIT: Persistiert die Änderung in SQLite
        self.conn.commit()
        return recording_id

    def get_recordings(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Liest alle Aufnahmen eines Patienten aus der Datenbank.
        
        Datenbankoperation: SELECT * FROM recording WHERE patientId = ?
        - Filtert nach patient_id
        - Sortiert nach date DESC (neueste zuerst)
        - Rückgabe: Liste von Dicts mit allen recording-Spalten
        
        Beispiel Rückgabe:
        [
          {'id': 'REC001', 'patientId': 5, 'date': 1704067200, 'baseline': 1},
          {'id': 'REC002', 'patientId': 5, 'date': 1704153600, 'baseline': 0},
        ]
        """
        cur = self.conn.cursor()
        # SELECT: Alle Spalten (id, patientId, date, baseline) für diesen Patient
        cur.execute("SELECT * FROM recording WHERE patientId = ? ORDER BY date DESC", (patient_id,))
        # FETCH: Holt alle passenden Zeilen
        rows = cur.fetchall()
        # CONVERT: sqlite3.Row Objekte zu Python Dicts
        return [dict(row) for row in rows]

    def get_baseline_recording(self, patient_id: int) -> Dict[str, Any] | None:
        """
        Liest die Baseline-Aufnahme eines Patienten.
        
        Datenbankoperation: SELECT * FROM recording WHERE patientId = ? AND baseline = 1
        - Filtert nach patient_id UND baseline=1
        - LIMIT 1: Gibt höchstens eine Zeile zurück
        - Rückgabe: Ein Dict oder None wenn keine gefunden
        
        Baseline-Aufnahmen sind Referenzmessungen für Vergleiche.
        """
        cur = self.conn.cursor()
        # SELECT: Suche baseline-Aufnahme für diesen Patient
        cur.execute("SELECT * FROM recording WHERE patientId = ? AND baseline = 1 LIMIT 1", (patient_id,))
        # FETCH ONE: Holt maximal eine Zeile
        row = cur.fetchone()
        # CONVERT: sqlite3.Row zu Dict, oder None wenn nicht gefunden
        return dict(row) if row else None

    def import_from_tbi_headset(self, tbi_db_path: str) -> Dict[str, Any]:
        """
        Importiert Patientendaten und Aufnahmen aus einer TBI_Headset Datenbank-ZIP.
        
        WORKFLOW:
        1. Öffnet TBI_Headset Datenbank (read-only)
        2. Liest alle Patienten und speichert sie in EyeCon (mit ID-Mapping)
        3. Liest alle Aufnahmen und mapped sie zu den neuen Patienten
        4. Gibt Statistik zurück (wie viele importiert, Fehler)
        
        SCHEMA-MAPPING:
        TBI_Headset.Patient.id          → EyeCon.patient.external_id
        TBI_Headset.Patient.sex         → EyeCon.patient.sex
        TBI_Headset.Patient.birthdate   → EyeCon.patient.birthdate
        
        TBI_Headset.Recording.id        → EyeCon.recording.id (direkt!)
        TBI_Headset.Recording.patientId → EyeCon.recording.patientId (via Lookup)
        TBI_Headset.Recording.date      → EyeCon.recording.date
        TBI_Headset.Recording.baseline  → EyeCon.recording.baseline
        
        WICHTIG: Das ist ein IMPORT von außen, NICHT modifiziert von EyeCon!
        
        Args:
            tbi_db_path: Pfad zur TBI_Headset patient_database.db Datei
            
        Returns:
            Dictionary mit Import-Ergebnissen:
            - imported_patients: Anzahl erfolgreich importierter Patienten
            - imported_recordings: Anzahl erfolgreich importierter Aufnahmen
            - skipped_recordings: Anzahl übersprungener Aufnahmen (Fehler)
            - errors: Liste mit Error-Messages
        """
        import sqlite3
        
        # === RESULT DICT FÜR STATISTIK ===
        # Wird am Ende zurückgegeben um dem Benutzer zu zeigen was passiert ist
        result = {
            'imported_patients': 0,      # Wie viele Patienten erfolgreich eingefügt
            'imported_recordings': 0,    # Wie viele Aufnahmen erfolgreich eingefügt
            'skipped_recordings': 0,     # Wie viele Aufnahmen übersprungen (Fehler/Patient nicht gefunden)
            'errors': []                 # Liste mit Error-Messages
        }
        
        try:
            # === DATENBANKVERBINDUNG ZUR TBI_HEADSET DATENBANK ===
            # Wichtig: mode=ro (read-only) - wir verändern TBI Datenbank NICHT!
            # Das ist ein reiner Import/Lesezugriff
            tbi_conn = sqlite3.connect(f'file:{tbi_db_path}?mode=ro', uri=True)
            tbi_conn.row_factory = sqlite3.Row
            tbi_cur = tbi_conn.cursor()
            
            # === PHASE 1: PATIENTEN IMPORTIEREN ===
            # Liest ALLE Patienten aus TBI_Headset Datenbank
            # Speichert sie in EyeCon patient-Tabelle
            # Erstellt id_mapping Dict zum späteren Lookup von Aufnahmen
            try:
                # SELECT: Alle Patienten aus TBI Datenbank
                tbi_cur.execute("SELECT id, sex, birthdate FROM Patient")
                tbi_patients = tbi_cur.fetchall()
                
                # WICHTIG: id_mapping verbindet TBI patient_ids mit EyeCon patient_ids
                # Wird später verwendet um Aufnahmen dem richtigen Patienten zuzuordnen
                # Beispiel: id_mapping['TBI_P001'] = 5  (EyeCon patient.id)
                id_mapping = {}
                
                for tbi_patient in tbi_patients:
                    tbi_id = tbi_patient['id']
                    sex = tbi_patient['sex'] or 'Unknown'
                    birthdate = tbi_patient['birthdate'] or '01.01.1990'
                    
                    # Default first_name/last_name from TBI external_id
                    first_name = f"Patient_{tbi_id[:10]}"  # Extract from ID
                    last_name = "TBI_Import"
                    
                    try:
                        # DATENBANKOPERATION: INSERT in EyeCon patient-Tabelle
                        # external_id = TBI patient_id (für Nachverfolgung/Auditing)
                        eyecon_id = self.create_patient(
                            first_name=first_name,
                            last_name=last_name,
                            birthdate=birthdate,
                            external_id=tbi_id  # ← Wichtig: Speichert Original TBI ID
                        )
                        
                        # MAPPING SPEICHERN: TBI ID → EyeCon ID
                        # Wird nachher für Recording-Import benötigt
                        id_mapping[tbi_id] = eyecon_id
                        
                        # DATENBANKOPERATION: UPDATE für sex-Feld
                        # (create_patient() setzt sex nicht, darum separate UPDATE)
                        cur = self.conn.cursor()
                        cur.execute("UPDATE patient SET sex = ? WHERE id = ?", (sex, eyecon_id))
                        self.conn.commit()  # ← Persistiert Update in SQLite
                        
                        result['imported_patients'] += 1
                        
                    except Exception as e:
                        error_msg = f"Error importing patient {tbi_id}: {str(e)}"
                        result['errors'].append(error_msg)
                
            except Exception as e:
                result['errors'].append(f"Error reading TBI patients: {str(e)}")
            
            # === PHASE 2: AUFNAHMEN/RECORDINGS IMPORTIEREN ===
            # Liest ALLE Aufnahmen aus TBI_Headset Datenbank
            # Mapped patient_id via id_mapping Dictionary
            # Speichert sie in EyeCon recording-Tabelle
            try:
                # SELECT: Alle Aufnahmen mit ihren Metadaten
                tbi_cur.execute("SELECT id, patientId, date, baseline FROM Recording")
                tbi_recordings = tbi_cur.fetchall()
                
                for tbi_recording in tbi_recordings:
                    tbi_recording_id = tbi_recording['id']
                    tbi_patient_id = tbi_recording['patientId']
                    date = tbi_recording['date']
                    baseline = tbi_recording['baseline']
                    
                    # WICHTIG: Lookup EyeCon patient_id via id_mapping
                    # Wenn Patient nicht in Import vorhanden → Fehler und überspringen
                    if tbi_patient_id not in id_mapping:
                        result['errors'].append(f"Recording {tbi_recording_id}: Patient {tbi_patient_id} not found in import")
                        result['skipped_recordings'] += 1
                        continue  # → Nächste Aufnahme
                    
                    # MAPPING: TBI patient_id → EyeCon patient_id (via Lookup)
                    eyecon_patient_id = id_mapping[tbi_patient_id]
                    
                    try:
                        # DATENBANKOPERATION: INSERT in EyeCon recording-Tabelle
                        # recording_id: Von TBI direkt übernommen (TEXT Primary Key)
                        # patient_id: Über id_mapping gemappter EyeCon patient
                        # date: Unix Timestamp von TBI
                        # baseline: Flag ob Baseline-Messung oder nicht
                        self.add_recording(
                            recording_id=str(tbi_recording_id),  # TBI ID als PK
                            patient_id=eyecon_patient_id,        # Gemappter EyeCon ID
                            date=int(date) if date else 0,       # Unix timestamp
                            baseline=int(baseline) if baseline else 0  # 0 oder 1
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
