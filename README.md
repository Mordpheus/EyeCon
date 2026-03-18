````markdown
# EyeCon — Minimalversion

Dieses Repository enthält eine stark vereinfachte Version der EyeCon-Anwendung.
Die Anwendung zeigt nur ein leeres Hauptfenster. Alle Texte sind auf Deutsch.

Schnellstart (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python .\Main.py
```

Projektstruktur (vereinfacht)

- `Main.py` — Einstiegspunkt, zeigt ein leeres Hauptfenster
- `src/` — Platzhalter-Module für spätere Erweiterung (deutsche Kommentare)
- `config/config.yaml` — minimale Konfiguration
- `requirements.txt` — benötigte Pakete

Hinweis: Diese Version enthält keine Datenbank, keine Patientenverwaltung und
keine Video-/Aufnahme-Logik. Die Struktur ist bewusst einfach gehalten, damit
Funktionalität schrittweise ergänzt werden kann.

````
# EyeCon

Simple PySide6 desktop app for video preview and session management.

Quick start (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python .\Main.py
```

Project layout

- `Main.py` — app entry and main window
- `src/` — application modules (config loader, video input/widget, dialogs, db)
- `config/config.yaml` — optional overrides for defaults
- `data/` — default folders for incoming videos and sessions

## Dependencies

- **PySide6** (6.7.3+) — Qt 6 GUI framework for Python
- **matplotlib** (3.8.0+) — Plot visualization for eye-tracking analysis

This repository contains a minimal working scaffold of the EyeCon desktop application. The `src/db.py` file provides a lightweight SQLite database used by the UI for development and testing.
