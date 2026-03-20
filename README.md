# EyeCon

EyeCon is a desktop application for pupil analysis and Pupil Light Reflex (PLR) testing, built with Python and PySide6. It supports video recording, pupil detection using YOLOv8, and session/patient management.

## Features

- Video preview and recording from USB/webcam
- Automated pupil detection and diameter measurement (YOLOv8 + OpenCV)
- PLR (Pupil Light Reflex) test analysis with velocity and amplitude metrics
- Patient and session management with SQLite database
- Interactive result plots (matplotlib)

## Quick Start

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python .\Main.py
```

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python Main.py
```

## Project Layout

```
EyeCon/
├── Main.py              # Application entry point
├── app_layout.py        # Main window and UI layout
├── data_manager.py      # Patient/session data management
├── patient_widgets.py   # Patient UI widgets
├── src/                 # Core modules
│   ├── db.py            # SQLite database helpers
│   ├── pupil_analyzer.py# Pupil detection and PLR analysis
│   ├── plr_test_screen.py # PLR test UI
│   └── ...
├── models/              # YOLOv8 model files (.pt)
├── data/                # Default folders for recordings and sessions
├── requirements.txt     # Python dependencies
└── README.md
```

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| PySide6 | 6.7.3+ | Qt 6 GUI framework |
| opencv-python | 4.8.0+ | Video capture and image processing |
| ultralytics | 8.0.0+ | YOLOv8 pupil detection |
| torch / torchvision | 2.0.0+ / 0.15.0+ | Deep learning backend |
| matplotlib | 3.8.0+ | Result visualization |
| scipy | 1.11.0+ | Signal filtering |
| numpy | 1.24.0+ | Numerical computing |
| Pillow | 10.0.0+ | Image handling |
| pyserial | 3.5+ | Serial communication (LED trigger) |

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to review pull requests, open issues, and submit your own changes.

## License

This project is licensed under the [MIT License](LICENSE).
