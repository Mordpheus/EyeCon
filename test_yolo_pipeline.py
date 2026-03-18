"""Quick test: YOLO pipeline on second video + key frames preview."""
import cv2
import sys
import numpy as np

sys.path.insert(0, r"c:\Uni\EyeCon")
from src.pupil_analyzer import PupilAnalyzer

video = r"c:\Users\cmbwa\Downloads\Yolo version\Example\videos\2025-08-08-11-47-36.mp4"
analyzer = PupilAnalyzer()

# Test extract_key_frames_for_preview
kf = analyzer.extract_key_frames_for_preview(video, num_frames=9)
print(f"Key frames: {len(kf)}")
for f in kf:
    n_eyes = len(f["all_eyes"])
    fn = f["frame_number"]
    d = f["diameter_px"]
    c = f["confidence"]
    t = f["timestamp"]
    print(f"  Frame {fn}: d={d:.1f}px conf={c:.2f} eyes={n_eyes} t={t:.1f}s")

# Full analysis + PLR
print()
success = analyzer.extract_frames_from_video(video, frame_pool=1)
detected = sum(1 for pf in analyzer.pupil_frames if not np.isnan(pf.diameter_px))
total = len(analyzer.pupil_frames)
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
cap.release()
print(f"Detected: {detected}/{total} ({100*detected/total:.0f}%)")

light_start = int(1.0 * fps)
light_end = int(2.0 * fps)
n = len(analyzer.pupil_frames)
light_start = min(light_start, n - 2)
light_end = min(light_end, n - 1)

metrics = analyzer.calculate_plr_metrics(light_start, light_end)
print(f"Baseline: {metrics.baseline_mean:.3f}mm")
print(f"Latency: {metrics.latency*1000:.0f}ms")
print(f"MinDiameter: {metrics.minimum_diameter:.3f}mm")
print(f"Amplitude: {metrics.amplitude:.3f}mm")
print(f"PCV: {metrics.peak_constriction_velocity:.4f} mm/s")
print(f"PDV: {metrics.peak_dilation_velocity:.4f} mm/s")
print(f"PRT50: {metrics.prt_50*1000:.0f}ms")
