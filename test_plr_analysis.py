"""
PLR (Pupil Light Reflex) Analysis Demo and Test

This script demonstrates the complete pupil analysis pipeline:
1. Load a video
2. Extract frames with YOLO based pupil detection
3. Calculate PLR biomarkers using Bergamin-Kardon method
4. Store results in database
5. Visualize results

For testing without a real video, set CREATE_DEMO_DATA=True
"""

import sys
import numpy as np
from pathlib import Path
from dataclasses import asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pupil_analyzer import PupilAnalyzer, PupilFrame, PLRMetrics
from src.db import PatientDataManager

# Demo settings
CREATE_DEMO_DATA = True  # Set to False to use real video
DEMO_VIDEO_PATH = None   # Replace with actual path
FRAME_POOL = 2           # Process every 2nd frame (50% speedup)

def create_demo_pupil_frames(num_frames: int = 300) -> tuple[list, str]:
    """
    Create synthetic pupil data for testing.
    
    Simulates:
    - 300 frames at 30 FPS = 10 seconds
    - Stimulus from frame 30-60 (1-2 seconds)
    - Normal pupil dynamics
    """
    print("\n📊 Creating demo pupil data...")
    
    frames = []
    recording_id = "demo_2026-02-24-14-00-00"
    
    # Create realistic pupil diameter curve
    baseline_diameter = 4.0  # mm
    fps = 30
    
    for i in range(num_frames):
        timestamp = i / fps
        
        # Baseline period (frames 0-30): stable diameter
        if i < 30:
            diameter = baseline_diameter + np.random.normal(0, 0.05)
            position_x = 320 + np.random.normal(0, 5)
            position_y = 240 + np.random.normal(0, 5)
            confidence = 0.95
        
        # Stimulus onset (frames 30-60): constriction
        elif i < 60:
            t_stim = (i - 30) / 30  # 0 to 1
            # Smooth exponential constriction
            diameter = baseline_diameter * (1 - 0.6 * np.sin(t_stim * np.pi / 2))
            diameter += np.random.normal(0, 0.03)
            position_x = 320 + 2 * np.sin(t_stim * np.pi)
            position_y = 240 + np.random.normal(0, 3)
            confidence = 0.93
        
        # Stimulus offset (frames 60-150): dilation recovery
        elif i < 150:
            t_recovery = (i - 60) / 90  # 0 to 1
            # Gradual recovery
            diameter = 2.0 + (baseline_diameter - 2.0) * (1 - np.exp(-3 * t_recovery))
            diameter += np.random.normal(0, 0.05)
            position_x = 320 + np.random.normal(0, 4)
            position_y = 240 + np.random.normal(0, 4)
            confidence = 0.92
        
        # Post-stimulus (frames 150+): baseline
        else:
            diameter = baseline_diameter + np.random.normal(0, 0.05)
            position_x = 320 + np.random.normal(0, 5)
            position_y = 240 + np.random.normal(0, 5)
            confidence = 0.95
        
        frames.append({
            'frame_number': i,
            'timestamp': timestamp,
            'diameter_px': diameter * 10,  # Convert to pixels (~40 px = 4mm)
            'position_x': position_x,
            'position_y': position_y,
            'confidence': confidence,
            'eye_area_px': int(diameter * 10 * 20)  # Approximate area
        })
    
    print(f"✅ Created {len(frames)} synthetic frames")
    print(f"   - Baseline: frames 0-30 (diameter ~40px)")
    print(f"   - Stimulus: frames 30-60 (constriction)")
    print(f"   - Recovery: frames 60-150 (dilation)")
    
    return frames, recording_id


def test_pupil_analysis():
    """Test the complete pupil analysis pipeline."""
    
    print("\n" + "="*70)
    print("🧪 PLR (PUPIL LIGHT REFLEX) ANALYSIS - DEMO")
    print("="*70)
    
    # Step 1: Create or load pupil data
    if CREATE_DEMO_DATA:
        pupil_frames, recording_id = create_demo_pupil_frames(num_frames=300)
    else:
        if not DEMO_VIDEO_PATH:
            print("❌ No video path specified. Set DEMO_VIDEO_PATH or use CREATE_DEMO_DATA=True")
            return
        
        print(f"\n📹 Loading video: {DEMO_VIDEO_PATH}")
        analyzer = PupilAnalyzer(model_name="yolov8n", use_onnx=True)
        success = analyzer.extract_frames_from_video(
            DEMO_VIDEO_PATH,
            frame_pool=FRAME_POOL,
            max_frames=300
        )
        
        if not success:
            print("❌ Failed to load video")
            return
        
        pupil_frames = [asdict(pf) for pf in analyzer.pupil_frames]
        recording_id = "demo_video"
    
    # Step 2: Create analyzer and populate with data
    analyzer = PupilAnalyzer(model_name="yolov8n")
    
    # Manually populate frames (in real usage, extract_frames_from_video does this)
    for frame_data in pupil_frames:
        analyzer.pupil_frames.append(PupilFrame(**frame_data))
    
    print(f"\n📊 Pupil data loaded:")
    print(f"   - Total frames: {len(analyzer.pupil_frames)}")
    print(f"   - Duration: {analyzer.pupil_frames[-1].timestamp:.2f} seconds")
    
    # Display diameter statistics
    diameters = [f.diameter_px for f in analyzer.pupil_frames]
    print(f"   - Diameter range: {min(diameters):.1f} - {max(diameters):.1f} px")
    print(f"   - Mean ± SD: {np.mean(diameters):.1f} ± {np.std(diameters):.1f} px")
    
    # Step 3: Calculate PLR metrics
    # Stimulus is at frames 30-60 (1-2 seconds at 30 FPS)
    light_stimulus_start = 30
    light_stimulus_end = 60
    
    print(f"\n💡 Light stimulus: frames {light_stimulus_start}-{light_stimulus_end}")
    
    try:
        metrics = analyzer.calculate_plr_metrics(
            light_stimulus_start_frame=light_stimulus_start,
            light_stimulus_end_frame=light_stimulus_end
        )
        print("\n✅ PLR metrics calculated successfully!")
    except Exception as e:
        print(f"❌ Error calculating metrics: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Display results
    print("\n" + "="*70)
    print("📋 PLR BIOMARKER RESULTS")
    print("="*70)
    
    print(f"\n🔷 BASELINE (before stimulus):")
    print(f"   Mean diameter:    {metrics.baseline_mean:.2f} px")
    print(f"   Max diameter:     {metrics.baseline_max:.2f} px")
    print(f"   Min diameter:     {metrics.baseline_min:.2f} px")
    
    print(f"\n⚡ LATENCY (Bergamin-Kardon method):")
    print(f"   Latency time:     {metrics.latency*1000:.1f} ms")
    print(f"   At frame:         {metrics.latency_frame_idx}")
    
    print(f"\n📉 CONSTRICTION (pupil closing):")
    print(f"   Peak velocity:    {metrics.peak_constriction_velocity:.4f} px/s")
    print(f"   At frame:         {metrics.peak_constriction_velocity_frame}")
    print(f"   Average velocity: {metrics.average_constriction_velocity:.4f} px/s")
    
    print(f"\n📊 AMPLITUDE & MINIMUM:")
    print(f"   Minimum diameter: {metrics.minimum_diameter:.2f} px")
    print(f"   At frame:         {metrics.minimum_diameter_frame}")
    print(f"   Amplitude:        {metrics.amplitude:.2f} px")
    
    print(f"\n📈 DILATION (pupil reopening):")
    print(f"   Peak velocity:    {metrics.peak_dilation_velocity:.4f} px/s")
    print(f"   At frame:         {metrics.peak_dilation_velocity_frame}")
    print(f"   Average velocity: {metrics.average_dilation_velocity:.4f} px/s")
    
    print(f"\n⏱️  PUPIL RECOVERY TIME (PRT):")
    print(f"   PRT-50 (50%):     {metrics.prt_50*1000:.1f} ms")
    print(f"   PRT-63 (63%):     {metrics.prt_63*1000:.1f} ms")
    print(f"   PRT-75 (75%):     {metrics.prt_75*1000:.1f} ms")
    
    # Step 5: Save to database
    print(f"\n💾 Saving to database...")
    db = PatientDataManager("data/eyecon.db")
    
    # First find or create a test recording
    patients = db.get_all_patients()
    if patients:
        patient_id = patients[0]['id']
        recordings = db.get_recordings(patient_id)
        recording_exists = any(r['id'] == recording_id for r in recordings) if recordings else False
        
        if not recording_exists:
            db.add_recording(recording_id, patient_id, date=1771910000, baseline=0)
            print(f"   Created recording: {recording_id}")
        else:
            print(f"   Using existing recording: {recording_id}")
    else:
        print("   ⚠️  No patients in database, skipping recording creation")
        return
    
    # Save pupil frames
    frame_count = db.save_pupil_frames(recording_id, pupil_frames)
    print(f"   ✅ Saved {frame_count} pupil frames")
    
    # Save PLR metrics
    metrics_dict = asdict(metrics)
    success = db.save_plr_metrics(
        recording_id,
        metrics_dict,
        light_stimulus_start,
        light_stimulus_end
    )
    
    if success:
        print(f"   ✅ Saved PLR metrics")
    else:
        print(f"   ❌ Failed to save PLR metrics")
    
    # Log analysis session
    session_id = db.create_analysis_session(
        recording_id,
        frame_count=len(analyzer.pupil_frames),
        analyzed_frame_count=len(analyzer.pupil_frames),
        status="completed"
    )
    print(f"   ✅ Created analysis session: {session_id}")
    
    # Step 6: Verify by reading back
    print(f"\n🔍 Verification - Reading back from database:")
    retrieved_frames = db.get_pupil_frames(recording_id)
    retrieved_metrics = db.get_plr_metrics(recording_id)
    
    if retrieved_frames:
        print(f"   ✅ Retrieved {len(retrieved_frames)} pupil frames")
    if retrieved_metrics:
        print(f"   ✅ Retrieved PLR metrics")
        print(f"      - Latency: {retrieved_metrics['latency']*1000:.1f} ms")
        print(f"      - Amplitude: {retrieved_metrics['amplitude']:.2f} px")
    
    print(f"\n" + "="*70)
    print("✅ PLR ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_pupil_analysis()
