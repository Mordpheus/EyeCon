# EyeCon - Schema Refactoring: measurement → recording (Session 20.01.2026 - Part 2)

## ✅ COMPLETED: Database Schema Refactoring

### Change Summary
Umbenannt von `measurement` Tabelle zu `recording` mit direkter SQLite-Kompatibilität zur TBI_Headset Datenbank-Struktur.

**Rationale:** Weniger Komplexität durch direkte Speicherung in SQLite, nicht JSON-Wrapper.

### Architecture
```
User clicks Import Button
    ↓ (LeftArea.btn_import.clicked signal)
AppLayout._on_import_clicked()
    ↓ (show file dialog)
CenterArea.importer.show_file_dialog()
    ↓ (user selects ZIP file)
CenterArea.importer.import_from_zip(zip_path)
    → extract_zip() → finds patient_database.db
    → PatientDataManager.import_from_tbi_headset(db_path)
    → ID mapping (TBI id → external_id)
    → Return success/result dict
    ↓ (show statistics)
CenterArea.importer.show_result_dialog()
    ↓ (refresh list)
CenterArea.patient_list.refresh with new patients
```

### Files Modified

#### 1. **src/db.py** (Complete Refactoring)
**measurement → recording Umwandlung:**

**ALTER TABLE:**
```sql
-- OLD: measurement (id INT, patient_id INT, recorded_at TIMESTAMP, is_baseline BOOL, data TEXT)
-- NEW: recording (id TEXT PK, patientId INT, date INT, baseline INT)
CREATE TABLE IF NOT EXISTS recording (
    id TEXT PRIMARY KEY,
    patientId INTEGER NOT NULL,
    date INTEGER,
    baseline INTEGER DEFAULT 0,
    FOREIGN KEY (patientId) REFERENCES patient(id) ON DELETE CASCADE
)
```

**Method Renames:**
- `add_measurement(patient_id, data, is_baseline)` → `add_recording(recording_id, patient_id, date, baseline)`
  - Parameter: recording_id (TEXT), patient_id (INT), date (INT), baseline (INT)
  - Speichert direkt in SQLite, keine JSON-Wrapper
- `get_measurements(patient_id)` → `get_recordings(patient_id)`
  - Query: `SELECT * FROM recording WHERE patientId = ? ORDER BY date DESC`
- `get_baseline_measurement(patient_id)` → `get_baseline_recording(patient_id)`
  - Query: `SELECT * FROM recording WHERE patientId = ? AND baseline = 1`

**Import Logic Update:**
- `import_from_tbi_headset()`: TBI Recording → EyeCon recording direct mapping
  - TBI Recording.id (TEXT) → EyeCon recording.id (PK)
  - TBI Recording.patientId → EyeCon recording.patientId (via id_mapping)
  - TBI Recording.date → EyeCon recording.date
  - TBI Recording.baseline → EyeCon recording.baseline
  - Kein JSON, keine Wrapper - direkte SQLite Speicherung
  - Result: `skipped_recordings` Counter hinzugefügt

#### 2. **test_data.py** (Updated Tests)
- Test 5: `add_measurement()` → `add_recording(recording_id, patient_id, date, baseline)`
- Test 6: `get_measurements()` → `get_recordings(patient_id)`
- Output angepasst auf neue Spalten (date, baseline statt recorded_at, is_baseline)

### Mapping Strategy (UPDATED)

#### Recording Import (formerly Measurement)
```
TBI_Headset.Recording.id         → EyeCon.recording.id    (TEXT PK - directly!)
TBI_Headset.Recording.patientId  → EyeCon.recording.patientId (via id_mapping lookup)
TBI_Headset.Recording.date       → EyeCon.recording.date  (INTEGER)
TBI_Headset.Recording.baseline   → EyeCon.recording.baseline (INTEGER: 0/1)
```

**Import Logic:**
```python
# For each TBI Recording:
self.add_recording(
    recording_id=str(tbi_recording['id']),           # Use TBI id directly
    patient_id=id_mapping[tbi_patient_id],           # Lookup EyeCon patient
    date=int(tbi_recording['date']) if date else 0,  # Unix timestamp
    baseline=int(tbi_recording['baseline']) if baseline else 0  # 0 or 1
)
```

**No JSON wrapper needed!** Direct SQLite storage.

### Error Handling
- ZIP-Datei existiert nicht → FileNotFoundError
- ZIP ist korrupt → BadZipFile
- patient_database.db nicht gefunden → FileNotFoundError mit Details
- Datenbank-Fehler beim Import → detailed error tracking
- Temp-Directory-Cleanup im `finally` Block

### Testing Completed
- ✅ Python Syntax validation (all files)
- ✅ Import statements resolved
- ✅ Class instantiation checks
- ✅ Signal connection registered

### Usage Example
```python
# User clicks Import button in LeftArea
# → AppLayout._on_import_clicked() called
# → File dialog opens (user selects ZIP)
# → importer.import_from_zip(zip_path) executed
#   - Extract ZIP to temp dir
#   - Find patient_database.db
#   - PatientDataManager.import_from_tbi_headset(db_path)
#   - Return success + statistics
# → Result dialog shows: "5 patients, 23 recordings imported"
# → Patient list auto-refreshes

# If errors:
# → Result dialog shows error messages
# → Partial imports kept (transaction per patient)
```

### Schema Reference (UPDATED)

**EyeCon Database (NEW)**
```sql
-- Patient table (unchanged)
CREATE TABLE patient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    sex TEXT,
    birthdate TEXT,
    first_name TEXT,
    last_name TEXT
);

-- Recording table (CHANGED FROM measurement!)
CREATE TABLE recording (
    id TEXT PRIMARY KEY,           -- TBI recording_id directly
    patientId INTEGER,              -- EyeCon patient.id (via id_mapping)
    date INTEGER,                   -- TBI Recording.date (Unix timestamp)
    baseline INTEGER DEFAULT 0,     -- TBI Recording.baseline (0=normal, 1=baseline)
    FOREIGN KEY(patientId) REFERENCES patient(id) ON DELETE CASCADE
);
```

**Comparison: OLD vs NEW**
```sql
-- OLD measurement:
-- id (INT PK), patient_id (INT), recorded_at (TIMESTAMP), is_baseline (BOOL), data (TEXT JSON)

-- NEW recording:
-- id (TEXT PK), patientId (INT), date (INT), baseline (INT)
```

**Benefits of NEW Structure:**
✅ Direct SQLite compatibility (no JSON parsing needed)
✅ TBI_Headset schema-aligned (easier future integrations)
✅ Simpler queries (no JSON extraction)
✅ Smaller storage footprint
✅ Faster lookups on date/baseline fields

### Code Documentation Details (in src/db.py)

**1. Recording Tabelle (Lines 52-75):**
- Erklärt dass es die alte `measurement` Tabelle ersetzt
- Dokumentiert jede Spalte: `id`, `patientId`, `date`, `baseline`
- Merkt an: keine JSON-Wrapper mehr, nur direkte SQLite Speicherung

**2. add_recording() Methode (Lines 157-173):**
- Erklärt was die Methode macht: INSERT in recording-Tabelle
- Parameterbeschreibung
- Notiert: COMMIT persistiert in SQLite

**3. get_recordings() Methode (Lines 175-199):**
- Erklärt SELECT Query mit WHERE/ORDER BY
- Beispiel-Output mit echten Daten-Strukturen
- Dokumentiert Konvertierung von sqlite3.Row zu Dict

**4. get_baseline_recording() Methode (Lines 201-217):**
- Erklärt Baseline-Lookup mit baseline=1 Filter
- Notiert: LIMIT 1 für maximale Performance
- Erklärung was Baseline-Aufnahmen sind

**5. import_from_tbi_headset() Methode (Lines 219-253):**
- **4-Phase WORKFLOW** dokumentiert
- **SCHEMA-MAPPING** mit allen Feldmappings
- Result Dictionary erklärt

**6. Import-Details im Code (Lines 260-340):**
- **PHASE 1**: Erklärung Patienten-Import mit id_mapping
- **PHASE 2**: Erklärung Recordings-Import mit Lookup
- Inline-Kommentare beim INSERT/UPDATE zeigen DB-Operationen

**Alle Kommentare:**
- ✅ Auf Deutsch
- ✅ Erklären was die Funktion in der DB macht
- ✅ Dokumentieren Spalten und deren Verwendung
- ✅ Zeigen ID-Mapping Logik
- ✅ Begründen warum diese Struktur besser ist als JSON

### Next Steps (Optional)
- [ ] Duplicate detection: existing external_id skip/update logic
- [ ] Batch import progress indicator (for large ZIPs)
- [ ] Rollback on critical errors (currently partial import)
- [ ] Export patient data function (reverse operation)

### Session End - Part 2
- Schema Refactoring: **measurement → recording COMPLETE**
- All files syntax-checked ✅
- Ready for user testing with new direct SQLite storage
