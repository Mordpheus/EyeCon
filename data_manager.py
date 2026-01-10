"""
Datenmanagement für Patienten und Messdaten
Speichert Patienten und Messdaten in JSON-Dateien
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class PatientDataManager:
    """Verwaltet Patienten und deren Messdaten in JSON"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialisiert den Datenmanager
        
        Args:
            data_dir: Verzeichnis für Datenspeicherung
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.patients_file = self.data_dir / "patients.json"
        self.measurements_dir = self.data_dir / "measurements"
        self.measurements_dir.mkdir(exist_ok=True)
        
        self._load_patients()
    
    def _load_patients(self) -> None:
        """Lädt Patientenliste aus JSON"""
        if self.patients_file.exists():
            try:
                with open(self.patients_file, 'r', encoding='utf-8') as f:
                    self.patients = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.patients = []
        else:
            self.patients = []
    
    def _save_patients(self) -> None:
        """Speichert Patientenliste in JSON"""
        with open(self.patients_file, 'w', encoding='utf-8') as f:
            json.dump(self.patients, f, indent=2, ensure_ascii=False)
    
    def _get_next_patient_id(self) -> int:
        """Generiert nächste fortlaufende Patient-ID"""
        if not self.patients:
            return 1
        return max(p.get("id", 0) for p in self.patients) + 1
    
    def create_patient(
        self,
        name: str,
        nachname: str,
        geburtsdatum: str,  # dd.mm.yyyy
        ext_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Erstellt einen neuen Patienten
        
        Args:
            name: Vorname
            nachname: Nachname
            geburtsdatum: Geburtsdatum (dd.mm.yyyy)
            ext_id: Externe ID (Smartphone-App)
        
        Returns:
            Patient-Dictionary
        """
        patient_id = self._get_next_patient_id()
        
        patient = {
            "id": patient_id,
            "name": name,
            "nachname": nachname,
            "geburtsdatum": geburtsdatum,
            "ext_id": ext_id,
            "erstellt_am": datetime.now().isoformat(),
            "messungen": []  # Liste von Messung-IDs
        }
        
        self.patients.append(patient)
        self._save_patients()
        
        return patient
    
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Gibt alle Patienten zurück"""
        return self.patients
    
    def get_patient(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """Gibt einen Patienten nach ID zurück"""
        for patient in self.patients:
            if patient["id"] == patient_id:
                return patient
        return None
    
    def update_patient(self, patient_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Aktualisiert Patientendaten"""
        patient = self.get_patient(patient_id)
        if patient:
            patient.update(kwargs)
            self._save_patients()
            return patient
        return None
    
    def delete_patient(self, patient_id: int) -> bool:
        """Löscht einen Patienten und seine Messdaten"""
        self.patients = [p for p in self.patients if p["id"] != patient_id]
        self._save_patients()
        
        # Lösche Messdaten-Datei
        measurements_file = self.measurements_dir / f"patient_{patient_id}_measurements.json"
        if measurements_file.exists():
            measurements_file.unlink()
        
        return True
    
    def add_measurement(
        self,
        patient_id: int,
        measurement_type: str,  # "baseline" oder "normal"
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Speichert eine neue Messung für einen Patienten
        
        Args:
            patient_id: Patient-ID
            measurement_type: "baseline" oder "normal"
            data: Messdaten
        
        Returns:
            Messung-Dictionary oder None
        """
        patient = self.get_patient(patient_id)
        if not patient:
            return None
        
        measurements_file = self.measurements_dir / f"patient_{patient_id}_measurements.json"
        
        # Lade existierende Messungen
        if measurements_file.exists():
            with open(measurements_file, 'r', encoding='utf-8') as f:
                measurements = json.load(f)
        else:
            measurements = []
        
        # Neue Messung
        measurement_id = len(measurements) + 1
        measurement = {
            "id": measurement_id,
            "type": measurement_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        measurements.append(measurement)
        
        # Speichere Messungen
        with open(measurements_file, 'w', encoding='utf-8') as f:
            json.dump(measurements, f, indent=2, ensure_ascii=False)
        
        # Aktualisiere Patient-Referenz
        if "messungen" not in patient:
            patient["messungen"] = []
        patient["messungen"].append(measurement_id)
        self._save_patients()
        
        return measurement
    
    def get_measurements(self, patient_id: int) -> List[Dict[str, Any]]:
        """Gibt alle Messungen eines Patienten zurück"""
        measurements_file = self.measurements_dir / f"patient_{patient_id}_measurements.json"
        
        if measurements_file.exists():
            with open(measurements_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def get_baseline_measurement(self, patient_id: int) -> Optional[Dict[str, Any]]:
        """Gibt die aktuelle Baseline-Messung zurück"""
        measurements = self.get_measurements(patient_id)
        
        # Gib die letzte Baseline zurück (oder None)
        baselines = [m for m in measurements if m["type"] == "baseline"]
        if baselines:
            return baselines[-1]
        return None
