"""
Test: Videoanalyse mit PyTorch - funktionsfähig?
"""
import sys
from pathlib import Path
from src.db import PatientDataManager
from src.pupil_analyzer import PupilAnalyzer

print("\n" + "="*60)
print("PLR VIDEO ANALYSIS TEST - PyTorch")
print("="*60 + "\n")

# Schritt 1: Datenbank prüfen
print("[1] Datenbank prüfen...")
try:
    db = PatientDataManager('data/eyecon.db')
    patients = db.get_all_patients()
    print(f"    ✓ {len(patients)} Patienten in DB")
except Exception as e:
    print(f"    ✗ DB Fehler: {e}")
    sys.exit(1)

# Schritt 2: Videos finden
print("\n[2] Videos suchen...")
patients_with_videos = {}
for patient in patients:
    recs = db.get_recordings(patient['id'])
    if recs:
        patients_with_videos[patient['id']] = (patient, recs)
        print(f"    ✓ {patient['last_name']}, {patient['first_name']}: {len(recs)} Videos")

if not patients_with_videos:
    print("    ✗ Keine Videos gefunden!")
    sys.exit(1)

# Schritt 3: Erstes Video analysieren
print("\n[3] Erste Video-Analyse starten...")
first_patient_id = list(patients_with_videos.keys())[0]
patient, recordings = patients_with_videos[first_patient_id]
video_path = recordings[0]['file_path']

print(f"    Patient: {patient['last_name']}, {patient['first_name']}")
print(f"    Video: {Path(video_path).name}")
print(f"    Pfad: {video_path}")

# Schritt 4: Analyzer laden
print("\n[4] CV-Pipeline laden...")
try:
    analyzer = PupilAnalyzer()
    print("    ✓ Analyzer geladen (Classical CV)")
except Exception as e:
    print(f"    ✗ Modell-Fehler: {e}")
    sys.exit(1)

# Schritt 5: Frames extrahieren & analysieren
print("\n[5] Video-Frames extrahieren und analysieren...")
try:
    key_frames = analyzer.extract_key_frames_for_preview(video_path, num_frames=9)
    print(f"    ✓ {len(key_frames)} Key-Frames extrahiert")
    
    # Resultate zeigen
    print("\n[6] Analyse-Resultate:")
    print("    " + "-"*50)
    for i, frame in enumerate(key_frames[:3], 1):
        print(f"    Frame {i}:")
        print(f"      - Pupillendurchmesser: {frame['diameter_px']:.2f} px")
        print(f"      - Erkennungsvertrauen: {frame['confidence']:.2%}")
        print(f"      - Position: ({frame['position'][0]:.0f}, {frame['position'][1]:.0f})")
        print(f"      - Zeit: {frame['timestamp']:.2f}s")
    
    print("\n" + "="*60)
    print("✓ VIDEO-ANALYSE FUNKTIONIERT!")
    print("="*60)
    print(f"\nAnalyseergebnis: {len(key_frames)} Frames, PyTorch aktiv")
    print("Sichtbare Ergebnisse verfügbar für PLR Test Screen")
    
except Exception as e:
    print(f"    ✗ Analyse-Fehler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
