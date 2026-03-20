EyeCon - Installation, Dependencies und Vollständiger Bedien-Workflow
======================================================================

Dieses Dokument beschreibt den aktuellen Stand von EyeCon (Windows/PySide6),
inklusive Setup, Abhängigkeiten, Laufzeitdateien und der kompletten
Bedienlogik mit allen Screens und Aktionen.
Wichtiger Hinweis: Da meine Test-Import-Daten und die Kommunikation das Headset
TBI-Headset nannten, ist im folgenden das PLR-Headset synonym zum TBI-Headset benutzt! 


1) Systemvoraussetzungen
------------------------
- Betriebssystem: Windows (PowerShell)
- Python: >= 3.10 (3.12 wurde verwendet)
- Internetzugang fuer Erstinstallation der Pakete
- Optional Hardware:
  - USB-Kamera fuer Live-Vorschau/Aufnahme
  - Serielles LED-Geraet (COM-Port) fuer Lichtstimulation


2) Exakte Python-Dependencies (aus requirements.txt)
----------------------------------------------------
PySide6==6.7.3
matplotlib>=3.8.0
pyserial>=3.5
numpy>=1.24.0
Pillow>=10.0.0
pyyaml>=6.0.0
opencv-python>=4.8.0
scipy>=1.11.0
ultralytics>=8.4.0 (PyPI-Paketversion bleibt 8.x; YOLO11-Modelle sind trotzdem möglich)
torch>=2.0.0
torchvision>=0.15.0
tensorflow>=2.16.0


3) Installation (PowerShell)
----------------------------
Windows 11 mit einer Python Installation >= 3.10 besser 3.12 wird vorausgesetzt. Diese Installationsschritte beschreibe ich hier nicht.
Im Projektordner ausführen:

1. Virtuelle Umgebung erstellen
  python -m venv .venv

2. pip aktualisieren
  .\.venv\Scripts\python -m pip install --upgrade pip

3. Pakete installieren
  .\.venv\Scripts\pip install -r requirements.txt

4. Anwendung starten
  .\.venv\Scripts\python .\Main.py


4) Alternative: venv aktivieren über Powershell
-------------------------------
1. Aktivieren
  .\.venv\Scripts\Activate.ps1

2. Starten
  python .\Main.py


5) Schneller Installationscheck
-------------------------------
Importtest:

.\.venv\Scripts\python -c "import PySide6, cv2, numpy, scipy, ultralytics, torch, tensorflow, yaml; print('OK')"

Wenn "OK" ausgegeben wird, sind die Kernabhaengigkeiten verfügbar.


6) Wichtige Laufzeitdateien und ihre funktionen
---------------------------
- Main.py
  Einstiegspunkt, initialisiert Hauptfenster und AppLayout.

- app_layout.py
  Haupt-GUI mit linker Navigation, mittlerer Screen-Logik und rechter
  Ergebnisanzeige, wenn PLR-Analyse durchgeführt wird.

- patient_widgets.py
  Patientenliste und Dialoge (Create/Edit/Delete/Duplicate).

- data_manager.py / src/db.py
  Datenbankzugriff auf SQLite (data/eyecon.db), Patienten-, Recording- und
  Analyse-Daten.

- src/camera_controller.py
  Kamera-/Aufnahmesteuerung und optionale serielle LED-Steuerung.

- src/importer.py
  ZIP-Import (TBI_Headset), Datenbankmapping, Kopieren der Recordings.

- src/plr_test_screen.py
  PLR-Analyse-Screen, Frame-Grid, Detaildialog, Vergleichsplot,
  Ergebnis-Emission an die rechte Seitenleiste.

- src/pupil_analyzer.py
  Pupil-Detection und PLR-Metrikberechnung.

- models/best_float32_230.tflite
  Standardmodell fuer die Pupil-Analyse.

- data/eyecon.db
  Lokale SQLite-Datenbank.

- data/recordings/
  Videoaufnahmen pro Patient.


7)Bedien-Workflow (Screen für Screen)
------------------------------------------------------

7.1 Start und Grundlayout
-------------------------
Nach Programmstart wird die Hauptansicht mit 3 Bereichen angezeigt:

1. Linke Spalte (Navigation und Kontext in Form von Icons & Buttons)
2. Mitte (QStackedWidget mit mehreren Screens)
3. Rechte Spalte (PLR Results, die leer sind solange keine Analyse stattfand)

Standard-Startscreen in der Mitte ist die Patientenliste angelehnt an ein Dashboard Design.


7.2 Linke Spalte - Alle Funktionen
----------------------------------
Obere Navigationsbuttons:
1. Patients
  Wechselt auf Patientenliste.

2. Import Data
  Startet ZIP-Import-Workflow (TBI_Headset Import, die Datei heisst so weil meine Testdatei TBI-Headset_import so hiess, die mir geschickt wurde)
  dabei wird sich ein standard Explorer Dialog zum auswählen der Zip Datei öffnen.

3. Settings
  Wechselt auf Settings-Screen. Ist aktuell nur für die Verbindung der App mit dem PLR-Headset über Serielle USB Verbindung zu nutzen.

4. Help
  Wechselt auf Help-Screen. Ist nur Platzhalter

Unterer Kontextbereich:
1. Anzeige aktuell ausgewählter Patient
2. Neue Aufnahme
  Öffnet Recording-Screen für den aktuell ausgewählten Patienten.
3. Recordings-Dropdown
  Zeigt Recordings des gewählten Patienten.
  Auswahl eines Eintrags lödt das Recording im Recording-Screen.
  Falls man bereits auf dem PLR-Screen ist, wird stattdessen dort direkt
  die Analyse für das neu ausgewählte Recording gestartet.


7.3 Screen 0 - Patientenliste (Center)
--------------------------------------
Verfügbare Aktionen:
1. Patient in Liste auswählen
  - Setzt den aktiven Patienten.
  - Aktualisiert linke Spalte (Patient + Recordings im Dropdown).

2. Create patient
  - Öffnet Erfassungsdialog.
  - Speichert neuen Patienten in SQLite.
  - Fügt ihn in die Liste ein.

3. Edit patient
  - Öffnet Bearbeitungsdialog für den ausgewählten Patienten.
  - Speichert Aenderungen in SQLite.
  - Aktualisiert Liste.

4. Delete patient
  - Öffnet Bestätigungsdialog.
  - Löscht Patienten in SQLite.
  - Entfernt Eintrag aus Liste und setzt Sidebar-Zustand zurück.


7.4 Import-Workflow (aus Linke Spalte > Import Data)
----------------------------------------------------
Schritte:
1. ZIP-Datei wählen.
2. ZIP wird temp entpackt.
3. patient_database.db im Export wird gesucht.
4. Patienten und Recordings werden importiert/gemappt.
5. Videos werden in data/recordings/{patient_id}/ kopiert.
6. Bei Duplikaten wird ein Entscheidungsdialog verwendet.
7. Ergebnisdialog mit Statistik/Fehlern wird angezeigt.
8. Patientenliste wird aktualisiert.


7.5 Screen 1 - Recording Player
-------------------------------
Dieser Screen dient fuer Wiedergabe, Aufnahme und Analyse-Start.

Elemente/Funktionen:
1. Back
  Zurück zur Patientenliste.

2. Videoanzeige + Timeline
  - Slider zur Positionssteuerung.
  - Anzeige aktueller Zeit und Dauer.

3. Wiedergabesteuerung
  - Play
  - Pause
  - Stop

4. Aufnahme-Steuerung
  - Start Recording
  - Stop Recording
  Aufnahmen werden ueber den CameraController erzeugt und dem aktiven
  Patientenkontext zugeordnet.

5. Change Baseline
  Setzt/verändert Referenzaufnahme für Vergleiche.

6. PLR Analysis
  Wechselt auf PLR-Screen und startet dort automatisch Analyse für das
  aktuell gewählte Recording (inkl. optionalem Baseline-Vergleich).


7.6 Screen 2 - Help
-------------------
1. Zeigt Hilfetext/Bedienhinweise.
2. Back bringt zurück zur Patientenliste.


7.7 Screen 3 - Settings
-----------------------
Funktionen:
1. Statusanzeige für Kamera/LED/Verbindung.
2. COM-Port Dropdown für LED-Gerät.
3. Scan Ports zum Neu-Einlesen verfügbarer serieller Ports.
4. LED ON / LED OFF Testbuttons.
5. Kamera-Vorschau inkl. No-Signal-Darstellung bei fehlender Kamera.
6. Back bringt zurueck zur Patientenliste.


7.8 Screen 4 - PLR Analysis
---------------------------
Ablauf:
1. Screen wird mit einem konkreten Video geladen (optional mit Baseline).
2. Analyse startet automatisch.
3. Es wird ein Frame-Grid mit erkannten Pupillen erstellt.
4. Klick auf ein Thumbnail öffnet Detaildialog mit Overlay.
5. Vergleichsplot (Recording vs Baseline) wird angezeigt, wenn Baseline
  verfügbar ist.
6. Back kehrt zur Patientenliste zurück.

Parallel dazu:
1. Metriken werden als Signal an die rechte Spalte gesendet.
2. Bei Fehlern werden Fehlermeldungen im Status und in der rechten Spalte
  dargestellt.


7.9 Rechte Spalte - PLR Results
-------------------------------
Die rechte Spalte zeigt die Metriken aus der PLR-Analyse nach B&K:

1. Baseline
  Mean/Max/Min Durchmesser

2. Latency
  Latenz in ms und Frameindex

3. Constriction
  Peak/Avg Velocity, Frame

4. Minimum
  Minimaldurchmesser, Amplitude, Frame

5. Dilation
  Peak/Avg Velocity, Frame

6. Recovery (PRT)
  PRT 50, PRT 63, PRT 75


8) Typischer End-to-End Use Case
--------------------------------
1. App starten.
2. Patienten anlegen oder per ZIP importieren.
3. Patienten in Liste auswählen.
4. In linker Spalte "Neue Aufnahme" oder vorhandenes Recording wöhlen.
5. Im Recording-Screen Video prüfen oder neue Aufnahme machen.
6. Optional Baseline setzen.
7. PLR Analysis starten.
8. Auf PLR-Screen Frames und Detailansicht prüfen.
9. Rechts die biometrischen Ergebnisse auswerten.
10. Bei Bedarf anderes Recording im Dropdown wählen und erneut analysieren.


9) Häufige Probleme
--------------------
1. Activate.ps1 blockiert
  Direkter Start ohne Aktivierung:
  .\.venv\Scripts\python .\Main.py

2. Kamera nicht verfügbar
  App startet weiter, aber Aufnahme/Preview sind eingeschränkt.

3. LED/COM reagiert nicht
  In Settings COM-Port neu scannen, richtigen Port wählen, wenn automatisch nicht erkannt.
  LED ON/OFF testen. WICHTIG, wenn die Kamera erkannt wird bleibt die LED ON, das muss man manuell ausschalten. 
  Habe ich vergessen zu fixen, diente Testzwecken

4. PLR-Analyse findet Video nicht
  Prüfen, ob Dateipfad im Recording existiert und Datei vorhanden ist.


10) Bei zusätzlichen Fragen Kontakt unter cmbwax@gmail.com
