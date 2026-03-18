"""
PLR Analysis Demo - Using 2025 TBI Export Video
Demonstrates end-to-end pupil detection with visible results
"""

import os
import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pupil_analyzer import PupilAnalyzer
from db import PatientDataManager

print("=" * 70)
print("PLR ANALYSE DEMO - Pupil Detection mit PyTorch + YOLO")
print("=" * 70)

# Initialize
db = PatientDataManager(db_path="data/eyecon.db")
analyzer = PupilAnalyzer()

print("\n[1] Lade Datenbankverbindung...")
patients = db.get_all_patients()
print(f"    ✓ {len(patients)} Patienten in DB")

print("\n[2] Suche Videos aus TBI-Export (Timestamp 2025)...")
recordings_dir = Path("data/recordings")
videos_2025 = sorted([v for v in recordings_dir.glob("2025-*.mp4")])
print(f"    ✓ {len(videos_2025)} Videos mit 2025-Timestamp gefunden")

if not videos_2025:
    print("    ✗ Keine 2025er Videos gefunden!")
    sys.exit(1)

# Use first video
video_path = videos_2025[0]
print(f"\n[3] Analysiere Video: {video_path.name}")
print(f"    Dateigröße: {video_path.stat().st_size / (1024*1024):.1f} MB")

print("\n[4] Extrahiere Frames und erkenne Pupillen...")
try:
    # Extract key frames with YOLO detection
    key_frames = analyzer.extract_key_frames_for_preview(
        str(video_path),
        num_frames=6
    )
    
    if key_frames and len(key_frames) > 0:
        print(f"    ✓ {len(key_frames)} Frames extrahiert und analysiert")
        
        print("\n[5] ERKANNTE PUPILLEN - DETEKTIONSERGEBNISSE:")
        print("-" * 70)
        
        for idx, frame_data in enumerate(key_frames, 1):
            print(f"\n    Frame {idx}:")
            print(f"      Frame-Nummer: {frame_data.get('frame_number', 'N/A')}")
            print(f"      Pupillendurchmesser: {frame_data.get('diameter_px', 0):.1f} px")
            print(f"      Detektionszuverlässigkeit: {frame_data.get('confidence', 0):.1%}")
            
            position = frame_data.get('position', (0, 0))
            print(f"      Position im Frame: ({position[0]:.0f}, {position[1]:.0f})")
            
            # Check if image exists
            if frame_data.get('image') is not None:
                print(f"      ✓ Bild vorhanden")
        
        print("\n" + "-" * 70)
        print(f"\n[6] PLR ANALYSE ZUSAMMENFASSUNG:")
        print(f"    Video: {video_path.name}")
        print(f"    Analysierte Frames: {len(key_frames)}")
        
        # Calculate statistics
        diameters = [f.get('diameter_px', 0) for f in key_frames if f.get('diameter_px', 0) > 0]
        confidences = [f.get('confidence', 0) for f in key_frames]
        
        if diameters:
            print(f"    Durchschnittlicher Pupillendurchmesser: {sum(diameters)/len(diameters):.1f} px")
            print(f"    Min/Max Durchmesser: {min(diameters):.1f} / {max(diameters):.1f} px")
        
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            print(f"    Durchschnittliche Detektionszuverlässigkeit: {avg_conf:.1%}")
        
        print("\n✓ VIDEOANALYSE ERFOLGREICH ABGESCHLOSSEN!")
        print("  PyTorch + YOLOv8 haben die Pupillen erkannt und analysiert")
        print("  Die Ergebnisse sind für PLRTestScreen verfügbar")
        
    else:
        print(f"    ✗ Keine Frames extrahiert")
        
except Exception as e:
    print(f"    ✗ Fehler bei Analyse: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("ende demo")
print("=" * 70)
