# EyeCon Recording Function Implementation - Zusammenfassung

## Was wurde implementiert

### 1. **Camera Controller** (`src/camera_controller.py`)

#### Neue Methoden:
- **`start_recording_with_pupillometry(duration=8.0, led_on_delay=1.0, output_video=None)`**
  - Hauptmethode für 8-Sekunden-Aufnahmen
  - LED-Stimulus bei 1.0-1.5s automatisch gesteuert
  - Speichert Frames im Speicher (Recording Frames Buffer)
  - Gibt Pfad der gespeicherten MP4-Datei zurück

- **`_recording_thread(duration, led_on_delay, led_on_duration, fps, width, height)`**
  - Läuft in separatem Thread für Non-Blocking GUI
  - Erfasst Frames bei 30 FPS
  - Steuert LED-Stimulus nach Protokoll
  - Überwacht Stop-Flags

- **`_save_recording_to_file(output_file=None) -> Optional[str]`**
  - Konvertiert erfasste Frames (RGB numpy array) zu MP4
  - Nutzt OpenCV VideoWriter mit H.264 Codec ('mp4v')
  - Speichert in `data/recordings/recording_YYYY-MM-DD_HH-MM-SS.mp4`
  - Rückgabe: Vollständiger Pfad zur Datei oder None

- **`stop_recording() -> bool`**
  - Setzt Stop-Flag für Record-Thread
  - Wartet max 1s bis Thread anhält
  - Rückgabe: True wenn erfolgreich

- **`get_recorded_duration() -> float`**
  - Gibt bisherige Recording-Länge in Sekunden zurück
  - Verwendet letzte Frame-Zeit aus Buffer

- **`get_recorded_frame_count() -> int`**
  - Gibt Anzahl erfasster Frames zurück

- **`delete_temp_recording() -> bool`**
  - Löscht temporäre Frames aus Buffer
  - Wird aufgerufen wenn Benutzer verwerfen auswählt

- **`save_manual_recording(output_file: str) -> Optional[str]`**
  - Speichert manuell gestoppte Aufnahme
  - Nutzt benutzerdefinierten Pfad aus File-Dialog

#### Neue Attribute:
```python
self.is_recording = False           # True während Recording läuft
self.recording_frames = []          # Buffer: List[(numpy_rgb_frame, elapsed_time)]
self.recording_start_time = None    # Zeitstempel für 8s-Zähler
self.stop_recording_requested = False # Stop-Flag vom UI
self.manual_stop = False            # True wenn manuell gestoppt
self.video_writer = None            # OpenCV VideoWriter Objekt
```

#### LED Stimulus Protokoll:
```
0.0s ---- 1.0s ---- 1.5s ---------- 8.0s
  |        |         |               |
[OFF] --> [ON] --> [OFF] ---------- [OFF]
```

### 2. **App Layout** (`app_layout.py`)

#### RecordingWorker Thread-Klasse:
```python
class RecordingWorker(QThread):
    recording_finished = Signal(str)  # "success:<filepath>" oder "manual_stop"
    recording_progress = Signal(float, int)  # (elapsed, frame_count)
```
- Läuft Recording in separatem Thread
- Emittiert Signale für GUI-Updates
- Verhindert GUI-Blockierung

#### Neue Handler-Funktionen in RecordingPlayerScreen:
- **`_on_start_recording()`**
  - Startet RecordingWorker Thread
  - Deaktiviert Start-Button, aktiviert Stop-Button
  - Zeigt Status: "🔴 RECORDING: 8-Sekunden-Protokoll läuft..."

- **`_on_stop_recording()`**
  - Stoppt Recording via Flag
  - Überprüft ob <8s (unvollständig)
  - Ruft Dialog auf bei unvollständigem Recording

- **`_show_incomplete_recording_dialog(elapsed, frame_count)`**
  - Zeigt Warnung: "Recording ist nur {elapsed}s lang"
  - Buttons: "💾 Speichern" oder "🗑️ Verwerfen"
  - Ja: öffnet File-Save-Dialog
  - Nein: löscht temporäre Frames

- **`_show_save_dialog()`**
  - Öffnet Windows Explorer-Dialog
  - Standard-Pfad: `data/recordings/`
  - Filter: MP4 Video (*.mp4)
  - Speichert mit benutzerdefinniertem Dateinamen

- **`_complete_recording()`**
  - Wird aufgerufen bei Auto-Stop nach 8s
  - Zeigt Erfolgsmeldung mit Dateigröße
  - Aktiviert Start-Button wieder

- **`_on_recording_finished(result)`**
  - Wird vom RecordingWorker Signal aufgerufen
  - result: "success:<filepath>" oder "manual_stop"

### 3. **Directory Struktur**
```
c:\Uni\EyeCon\
├── data/
│   ├── patients.json
│   ├── measurements/
│   └── recordings/          ← NEU: Hier werden MP4-Dateien gespeichert
│       ├── recording_2026-02-02_14-30-45.mp4
│       └── recording_2026-02-02_14-32-10.mp4
```

## Workflow - 8 Sekunden Protokoll

### Szenario 1: Normales Recording (8 Sekunden)
```
[Benutzer] START REC
    ↓
[App] Startet RecordingWorker Thread
    ↓
[Camera] Erfasst Frames @ 30 FPS
    ↓
[LED] 0-1s OFF → 1-1.5s ON (Kontraktion) → 1.5-8s OFF
    ↓
[Timer] Nach 8s automatisch gestoppt
    ↓
[Camera] _save_recording_to_file() - speichert MP4
    ↓
[UI] Zeigt: "✓ Recording erfolgreich gespeichert"
```

### Szenario 2: Manueller Stop vor 8 Sekunden
```
[Benutzer] START REC
    ↓
[App] Recording läuft...
    ↓
[Benutzer] STOP REC (z.B. nach 3s)
    ↓
[App] Zeigt Dialog:
      "Recording ist nur 3.0 Sekunden lang.
       Das Protokoll erfordert 8 Sekunden für gültige Messungen.
       Möchten Sie diese Datei speichern oder verwerfen?"
    ↓
[IF] Benutzer: "🗑️ Verwerfen"
    ↓
[App] delete_temp_recording() - Frames gelöscht
      Zeigt: "🗑️ Recording gelöscht"
    ↓
    
[IF] Benutzer: "💾 Speichern"
    ↓
[App] Öffnet Explorer-Save-Dialog
    ↓
[Benutzer] Wählt Dateiname + Speicherort
    ↓
[App] save_manual_recording(filepath)
    ↓
[App] Zeigt: "✓ Recording gespeichert: filename.mp4"
```

## Technische Details

### Video-Encoding (MP4)
```python
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 Codec
fps = 20  # Recording Frame Rate
width, height = 640, 480  # From camera
out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
```

### Frame-Buffer
```python
self.recording_frames = [
    (numpy_array_rgb_frame_1, 0.033),  # Frame 1 @ 33ms
    (numpy_array_rgb_frame_2, 0.066),  # Frame 2 @ 66ms
    ...
]
# Später: Konvertiere RGB → BGR für OpenCV VideoWriter
```

### Thread-Sicherheit
- Recording läuft in separatem QThread
- GUI bleibt responsiv @ 30 FPS
- Signal/Slot Kommunikation für Thread-sichere Updates

## Benutzer-Interaktion

### START REC Button
- Button wird grün/aktiv
- Zeigt Status: "🔴 RECORDING: 8-Sekunden-Protokoll läuft..."
- Stop-Button wird aktiviert
- Kann nur während Recording aktiv sein

### STOP REC Button
- Button wird rot (aktiv) während Recording
- Benutzer kann jederzeit klicken
- Dialog bei <8s Recording-Länge
- Button wird grau (inaktiv) wenn nicht recording

### Dialog-Optionen bei <8s
1. **"💾 Speichern"** - Explorer-Dialog
   - Standardpfad: data/recordings/
   - Benutzer wählt Dateinamen
   - MP4 Datei wird mit gewähltem Namen gespeichert

2. **"🗑️ Verwerfen"** - Datei löschen
   - Frames aus Buffer gelöscht
   - Keine Datei auf Disk geschrieben
   - Status: "🗑️ Recording gelöscht"

## Testing-Checkliste

- [x] ✓ start_recording_with_pupillometry() in camera_controller.py
- [x] ✓ _save_recording_to_file() mit MP4 Encoding
- [x] ✓ RecordingWorker QThread in app_layout.py
- [x] ✓ Dialog-System für <8s Recording
- [x] ✓ File-Save-Dialog mit Explorer
- [x] ✓ LED-Stimulus bei 1.0-1.5s
- [x] ✓ Auto-Stop nach 8s
- [x] ✓ Alle Methoden Syntax-geprüft
- [ ] Testing: 8s Auto-Stop + Speichern
- [ ] Testing: Manueller Stop + Verwerfen
- [ ] Testing: Manueller Stop + Speichern mit Explorer
- [ ] Testing: MP4 Datei abspielen verifizieren

## Nächste Schritte

1. **Testing durchführen**
   - Manuelles Recording mit echtem Pi + USB-Webcam
   - Dateigrößen und Frame-Raten überprüfen
   - LED-Stimulus-Timing verifizieren

2. **Verbesserungen optional**
   - Recording-Metadaten zur Database speichern
   - Recording-Fortschrittsanzeige (z.B. Progressbar)
   - Thumbnail-Generierung für Aufnahmen
   - Verzeichnis-Navigation zum Abspielen von älteren Recordings

3. **Performance-Optimierung**
   - Frame-Buffer-Größe monitoren
   - Speicher-Nutzung während langer Sessions
   - Video-Kompression-Einstellungen tunen

---

**Status**: ✅ Implementierung COMPLETE - Bereit für Testing
