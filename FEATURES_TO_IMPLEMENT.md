# Features aus a86fbde - zu implementieren in Test-Branch

## Priorität 1: Settings Screen Verbesserungen
- **Settings Camera Preview funktioniert**: Live-Preview (nicht nur "No Signal")
- **Camera-Auswahl sollte funktionieren** ohne Startfehler
- **QStackedWidget für Video-Anzeige**: 
  - Index 0: Video Player (normal)
  - Index 1: Live Preview (während Recording)
  - Preview-Label Widget für Live-Frames

## Priorität 2: Recording Screen UI Features
- **Baseline-Button (grün #1a4a1a)**: `btn_set_baseline`
  - Setzt Recording als Baseline für Vergleiche
  - Färbt Item grün in der Liste
- **Comparison-Button (blau #4488ff)**: `btn_add_comparison`
  - Fügt Recording zu Vergleichsgruppe hinzu
  - Färbt Item blau in der Liste
- **Multi-Select Mode**: RecordingList mit Multi-Selection
- **Auto-select neuestes Recording**
- **Status-Label**:
  - `recording_status_label`: Zeigt "Baseline: xxx" + Vergleich-Count
  - `recording_info.setText()`: Status-Feedbacks

## Priorität 3: Recording-List Anzeige
- **Recording-Liste nicht mehr leer**:
  - Die Liste sollte Recordings anzeigen
  - Muss von Datenbank geladen werden (UUID-Integration?)
  - Filtering nach Patient

## Priorität 4: Database/Patient Integration
- **Patient UUID/ID Integration**:
  - Recordings an Patient gebunden (wie in a86fbde)
  - Datenbank sollte Recordings speichern und abrufen
  - Patient-Filter sollte funktionieren

## Priorität 5: Camera Controller Improvements (a86fbde hat auch Fixes)
- **LED-Handling**: LED nach Connection sofort wieder LED OFF
- **Recording State Reset**: `is_recording = False` nach Save
- **Debug-Prints entfernen**: Sauberer Code ohne Debug-Output

## Priorität 6: Plots/Comparison Features
- **Baseline-Plot (grün)**
- **Comparison-Plots (verschiedene Farben)**
- **Live-Preview Timer**: `_on_preview_timer()` mit echten Frames

## Implementierungs-Strategie:
1. Wechsel zu Test-Branch (stabil)
2. Implementiere nacheinander:
   - Settings Preview (QStackedWidget)
   - Baseline/Comparison UI (Buttons + Styling)
   - Recording-List Fix (Datenbank)
   - Plots (wenn Zeit)

## Wichtig: Threading-Fixes nicht verlieren!
Test-Branch hat bereits die OpenCV Threading-Locks:
- camera_controller.py: 3x threading.Lock() um capture.read()
- Diese MÜSSEN erhalten bleiben!

## Dateien zu modifizieren:
- app_layout.py: UI-Features
- src/camera_controller.py: LED/State Fixes (optional)
- data_manager.py: Recording-List Fix (optional)

Datum: 2026-02-18
Status: Dokumentiert vor Wechsel zu Test-Branch
