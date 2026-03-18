"""
Platzhalter für die Konfigurations-Ladefunktion.

Diese Datei enthält nur eine sehr einfache Funktion `lade_konfig`, die eine
Standardkonfiguration zurückgibt. Die Funktion ist bewusst einfach gehalten,
damit später eine echte YAML-Ladung ergänzt werden kann.
"""

from typing import Dict, Any


def lade_konfig(pfad: str | None = None) -> Dict[str, Any]:
    """Gibt eine Standard-Konfiguration zurück.

    Parameter:
    - `pfad`: Optionaler Pfad zu einer Konfigurationsdatei (noch unbenutzt).

    Rückgabe: Ein Dictionary mit plausiblen Standardwerten.
    """
    return {
        "pfade": {
            "video_incoming_dir": "data/videos/incoming",
            "sessions_dir": "data/sessions",
            "database_path": "data/eyecon.db",
        },
        "video": {
            "default_source": "file",
            "usb_camera_index": 0,
            "accepted_extensions": [".mp4", ".mov", ".avi"],
        },
    }

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class AppPaths:
    video_incoming_dir: Path
    sessions_dir: Path
    database_path: Path
    logs_dir: Path


@dataclass(frozen=True)
class VideoConfig:
    default_source: str
    usb_camera_index: int
    accepted_extensions: tuple[str, ...]


@dataclass(frozen=True)
class UIConfig:
    theme: str


@dataclass(frozen=True)
class AppConfig:
    paths: AppPaths
    video: VideoConfig
    ui: UIConfig


DEFAULTS: Dict[str, Any] = {
    "paths": {
        "video_incoming_dir": "data/videos/incoming",
        "sessions_dir": "data/sessions",
        "database_path": "data/eyecon.db",
        "logs_dir": "logs",
    },
    "video": {
        "default_source": "file",
        "usb_camera_index": 0,
        "accepted_extensions": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    },
    "ui": {"theme": "light"},
}


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or Path("config/config.yaml")
    data: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    # Merge with defaults
    merged = {**DEFAULTS, **data}
    paths = merged.get("paths", {})
    video = merged.get("video", {})
    ui = merged.get("ui", {})

    app_paths = AppPaths(
        video_incoming_dir=Path(paths.get("video_incoming_dir", DEFAULTS["paths"]["video_incoming_dir"])) ,
        sessions_dir=Path(paths.get("sessions_dir", DEFAULTS["paths"]["sessions_dir"])) ,
        database_path=Path(paths.get("database_path", DEFAULTS["paths"]["database_path"])) ,
        logs_dir=Path(paths.get("logs_dir", DEFAULTS["paths"]["logs_dir"])) ,
    )

    video_cfg = VideoConfig(
        default_source=str(video.get("default_source", DEFAULTS["video"]["default_source"])),
        usb_camera_index=int(video.get("usb_camera_index", DEFAULTS["video"]["usb_camera_index"])),
        accepted_extensions=tuple(video.get("accepted_extensions", DEFAULTS["video"]["accepted_extensions"])),
    )

    ui_cfg = UIConfig(theme=str(ui.get("theme", DEFAULTS["ui"]["theme"])))

    return AppConfig(paths=app_paths, video=video_cfg, ui=ui_cfg)
