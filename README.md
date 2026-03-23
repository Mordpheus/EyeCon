````markdown
# EyeCon

Installation, dependencies, and complete operating workflow for the current EyeCon application (Windows/PySide6).

Important note: The term `PLR headset` is used synonymously with `TBI headset` in this document, based on test import data naming.

## 1. System Requirements

- Operating system: Windows (PowerShell)
- Python: >= 3.10 (3.12 was used during development)
- Internet access for first-time package installation
- Optional hardware:
  - USB camera for live preview and recording
  - Serial LED device (COM port) for light stimulation

## 2. Python Dependencies (from `requirements.txt`)

- `PySide6==6.7.3`
- `matplotlib>=3.8.0`
- `pyserial>=3.5`
- `numpy>=1.24.0`
- `Pillow>=10.0.0`
- `pyyaml>=6.0.0`
- `opencv-python>=4.8.0`
- `scipy>=1.11.0`
- `ultralytics>=8.4.0` (PyPI package stays on 8.x; YOLO11 models can still be used)
- `torch>=2.0.0`
- `torchvision>=0.15.0`
- `tensorflow>=2.16.0`

## 3. Installation (PowerShell)

Windows 11 with Python >= 3.10 (preferably 3.12) is expected.
Run in the project folder:

1. Create a virtual environment

```powershell
python -m venv .venv
```

2. Upgrade pip

```powershell
.\.venv\Scripts\python -m pip install --upgrade pip
```

3. Install packages

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

4. Start the application

```powershell
.\.venv\Scripts\python .\Main.py
```

## 4. Alternative: Activate `venv` in PowerShell

1. Activate

```powershell
.\.venv\Scripts\Activate.ps1
```

2. Start

```powershell
python .\Main.py
```

## 5. Quick Installation Check

Import test:

```powershell
.\.venv\Scripts\python -c "import PySide6, cv2, numpy, scipy, ultralytics, torch, tensorflow, yaml; print('OK')"
```

If `OK` is printed, the core dependencies are available.

## 6. Important Runtime Files and Their Roles

- `Main.py`
  Entry point, initializes main window and `AppLayout`.

- `app_layout.py`
  Main GUI with left navigation, center screen logic, and right results panel for PLR analysis.

- `patient_widgets.py`
  Patient list and dialogs (`Create/Edit/Delete/Duplicate`).

- `data_manager.py` / `src/db.py`
  SQLite data access (`data/eyecon.db`) for patient, recording, and analysis data.

- `src/camera_controller.py`
  Camera/recording control and optional serial LED control.

- `src/importer.py`
  ZIP import (`TBI_Headset`), database mapping, and recording copy logic.

- `src/plr_test_screen.py`
  PLR analysis screen, frame grid, detail dialog, comparison plot, and emission of results to the right sidebar.

- `src/pupil_analyzer.py`
  Pupil detection and PLR metric computation.

- `models/best_float32_230.tflite`
  Default model for pupil analysis.

- `data/eyecon.db`
  Local SQLite database.

- `data/recordings/`
  Patient video recordings.

## 7. Operating Workflow (Screen by Screen)

### 7.1 Start and Basic Layout

After startup, the main view shows 3 areas:

1. Left column (navigation and context via icons and buttons)
2. Center area (`QStackedWidget` with multiple screens)
3. Right column (`PLR Results`, empty until an analysis has been run)

The default center screen is the patient list with a dashboard-like layout.

### 7.2 Left Column - All Functions

Top navigation buttons:

1. `Patients`
	Switches to patient list.

2. `Import Data`
	Starts ZIP import workflow (`TBI_Headset` import).
	A standard file explorer dialog opens to choose the ZIP file.

3. `Settings`
	Switches to settings screen.
	Currently used for serial USB connection between app and PLR headset.

4. `Help`
	Switches to help screen (placeholder).

Bottom context area:

1. Display of currently selected patient
2. `New Recording`
	Opens recording screen for the selected patient.
3. `Recordings` dropdown
	Shows recordings of selected patient.
	Selecting an entry loads the recording in recording screen.
	If currently on PLR screen, the analysis for the newly selected recording starts directly.

### 7.3 Screen 0 - Patient List (Center)

Available actions:

1. Select patient in list
	- Sets active patient.
	- Updates left column (patient + recordings in dropdown).

2. `Create patient`
	- Opens creation dialog.
	- Saves new patient to SQLite.
	- Adds patient to list.

3. `Edit patient`
	- Opens edit dialog for selected patient.
	- Saves changes to SQLite.
	- Updates list.

4. `Delete patient`
	- Opens confirmation dialog.
	- Deletes patient in SQLite.
	- Removes entry from list and resets sidebar state.

### 7.4 Import Workflow (Left Column > Import Data)

Steps:

1. Select ZIP file.
2. ZIP is extracted to temporary folder.
3. `patient_database.db` is searched inside export.
4. Patients and recordings are imported/mapped.
5. Videos are copied to `data/recordings/{patient_id}/`.
6. Duplicate handling uses a decision dialog.
7. Result dialog with statistics/errors is shown.
8. Patient list is refreshed.

### 7.5 Screen 1 - Recording Player

This screen is used for playback, recording, and analysis start.

Elements/functions:

1. `Back`
	Returns to patient list.

2. Video display + timeline
	- Slider for position control.
	- Display of current time and duration.

3. Playback controls
	- `Play`
	- `Pause`
	- `Stop`

4. Recording controls
	- `Start Recording`
	- `Stop Recording`
	Recordings are created via `CameraController` and assigned to active patient context.

5. `Change Baseline`
	Sets/changes reference recording for comparisons.

6. `PLR Analysis`
	Switches to PLR screen and starts analysis automatically for selected recording (including optional baseline comparison).

### 7.6 Screen 2 - Help

1. Shows help text / usage hints.
2. `Back` returns to patient list.

### 7.7 Screen 3 - Settings

Functions:

1. Status indicators for camera/LED/connection.
2. COM port dropdown for LED device.
3. `Scan Ports` to reload available serial ports.
4. `LED ON` / `LED OFF` test buttons.
5. Camera preview including no-signal visualization if no camera is available.
6. `Back` returns to patient list.

### 7.8 Screen 4 - PLR Analysis

Flow:

1. Screen loads with specific video (optional with baseline).
2. Analysis starts automatically.
3. Frame grid with detected pupils is generated.
4. Clicking a thumbnail opens detail dialog with overlay.
5. Comparison plot (recording vs baseline) is shown if baseline exists.
6. `Back` returns to patient list.

In parallel:

1. Metrics are sent as signal to right column.
2. On errors, messages are displayed in status and right column.

### 7.9 Right Column - PLR Results

The right column shows B&K-style PLR metrics:

1. Baseline
	Mean/Max/Min diameter

2. Latency
	Latency in ms and frame index

3. Constriction
	Peak/Avg velocity, frame

4. Minimum
	Minimum diameter, amplitude, frame

5. Dilation
	Peak/Avg velocity, frame

6. Recovery (PRT)
	PRT 50, PRT 63, PRT 75

## 8. Typical End-to-End Use Case

1. Start app.
2. Create patients or import them via ZIP.
3. Select patient in list.
4. In left column choose `New Recording` or an existing recording.
5. In recording screen verify video or create a new recording.
6. Optionally set baseline.
7. Start `PLR Analysis`.
8. On PLR screen inspect frames and detail view.
9. Evaluate biometric results on right side.
10. If needed, select another recording in dropdown and analyze again.

## 9. Common Issues

1. `Activate.ps1` is blocked
	Direct start without activation:

	```powershell
	.\.venv\Scripts\python .\Main.py
	```

2. Camera not available
	App still starts, but recording/preview are limited.

3. LED/COM not responding
	Re-scan COM ports in settings and choose correct port if auto-detection fails.
	Test `LED ON/OFF`.
	Important: if camera is detected, LED may remain ON and must be switched off manually.

4. PLR analysis cannot find video
	Check that recording file path exists and file is present.

## 10. Contact

For additional questions: `cmbwax@gmail.com`
