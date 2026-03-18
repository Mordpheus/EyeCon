"""Debug script to analyze PLR detection pattern."""
import numpy as np
from src.pupil_analyzer import PupilAnalyzer, MM_PER_PIXEL

video = r'data\recordings\4064-1990-01-01-W\2026-02-28-14-41-18.mp4'
a = PupilAnalyzer()
a.extract_frames_from_video(video, frame_pool=1, max_frames=None)

print('frame | time  | d_mm  | d_px  | conf  | eye_idx')
print('------+-------+-------+-------+-------+--------')
for pf in a.pupil_frames:
    d_mm = pf.diameter_px * MM_PER_PIXEL
    ei = getattr(pf, 'eye_index', '?')
    print(f'{pf.frame_number:5d} | {pf.timestamp:5.2f} | {d_mm:5.2f} | {pf.diameter_px:5.1f} | {pf.confidence:.3f} | {ei}')

print()
print('=== Detection details per frame (first 30) ===')
for fc in sorted(a.all_detections.keys())[:30]:
    dets = a.all_detections[fc]
    parts = []
    for d in dets:
        parts.append(f'eye{d.eye_index}:{d.diameter_px:.1f}px,conf={d.confidence:.2f}')
    if not parts:
        parts = ['NO DETECTION']
    primary = [d for d in dets if d.eye_index == 0]
    used = 'L' if primary else ('R' if dets else 'N')
    sep = ' | '
    print(f'  Frame {fc:3d} (t={fc/20:.2f}): {sep.join(parts)} -> used={used}')
