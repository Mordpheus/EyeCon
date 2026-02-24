"""
Pupil Light Reflex (PLR) Analysis Module

Analyzes patient videos for pupil detection and calculates PLR biomarkers
using YOLO for real-time pupil detection and Bergamin-Kardon method for
latency calculation.

Features:
- Frame-by-frame pupil detection (YOLO)
- Temporal filtering (Savitzky-Golay, Gaussian)
- PLR parameter calculation (amplitude, latency, constriction/dilation velocity)
- Database persistence
- CPU-optimized for low-end hardware (ONNX Runtime)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import CubicSpline
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class PupilFrame:
    """Data class for per-frame pupil detection results."""
    frame_number: int
    timestamp: float  # seconds
    diameter_px: float
    position_x: float  # center x coordinate in pixels
    position_y: float  # center y coordinate in pixels
    confidence: float  # YOLO confidence score
    eye_area_px: int  # bounding box area


@dataclass
class PLRMetrics:
    """Data class for PLR (Pupil Light Reflex) biomarkers."""
    # Baseline parameters
    baseline_mean: float
    baseline_max: float
    baseline_min: float
    
    # Latency and timing
    latency: float  # seconds
    latency_frame_idx: int
    
    # Constriction phase (pupil closing)
    peak_constriction_velocity: float  # mm/s or px/frame
    peak_constriction_velocity_frame: int
    average_constriction_velocity: float
    
    # Minimum diameter
    minimum_diameter: float
    minimum_diameter_frame: int
    amplitude: float  # baseline - minimum
    
    # Dilation phase (pupil reopening)
    peak_dilation_velocity: float
    peak_dilation_velocity_frame: int
    average_dilation_velocity: float
    
    # Pupil Recovery Time (PRT)
    prt_50: Optional[float] = None  # seconds to 50% recovery
    prt_63: Optional[float] = None  # seconds to 63% recovery (1/e)
    prt_75: Optional[float] = None  # seconds to 75% recovery


class PupilAnalyzer:
    """
    Main class for pupil analysis pipeline.
    
    Workflow:
    1. Load video file
    2. Frame extraction with optional pooling (e.g., every 2nd frame for speed)
    3. YOLO inference for pupil detection
    4. Temporal filtering and smoothing
    5. PLR biomarker calculation
    6. Database persistence
    """
    
    def __init__(self, model_name: str = "yolov8n", use_onnx: bool = True, device: str = "cpu"):
        """
        Initialize pupil analyzer with YOLO model.
        
        Args:
            model_name: YOLO model variant (yolov8n recommended for CPU)
            use_onnx: Convert to ONNX for CPU optimization
            device: "cpu" or "cuda" (if NVIDIA available)
        """
        self.model_name = model_name
        self.use_onnx = use_onnx
        self.device = device
        
        logger.info(f"Loading YOLO model: {model_name} on {device}")
        self.model = YOLO(f"{model_name}.pt")
        
        if use_onnx and device == "cpu":
            try:
                # Export to ONNX for CPU optimization (~2-3x faster)
                logger.info("Converting to ONNX for CPU optimization...")
                self.model.export(format="onnx")
                # Switch to ONNX model
                self.model = YOLO(f"{model_name}.onnx")
            except Exception as e:
                logger.warning(f"ONNX conversion failed, using PyTorch: {e}")
        
        self.pupil_frames: List[PupilFrame] = []
        self.metrics: Optional[PLRMetrics] = None
    
    def extract_frames_from_video(
        self, 
        video_path: str, 
        frame_pool: int = 1,
        max_frames: Optional[int] = None
    ) -> bool:
        """
        Extract frames from video and perform YOLO inference.
        
        Performance optimization: frame_pool=2 processes every 2nd frame,
        reducing computation by ~50% with minimal quality loss.
        
        Args:
            video_path: Path to video file
            frame_pool: Process every nth frame (1=all, 2=every 2nd, etc.)
            max_frames: Limit analysis to first N frames (for testing)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Opening video: {video_path}")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return False
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30  # Default to 30 FPS
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Video: {fps} FPS, {total_frames} frames total")
        logger.info(f"Frame pooling: every {frame_pool}th frame = {total_frames // frame_pool} effective frames")
        
        frame_count = 0
        analyzed_frames = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Frame pooling: skip frames for speed
                if frame_count % frame_pool != 0:
                    frame_count += 1
                    continue
                
                # Optional: limit total frames analyzed
                if max_frames and analyzed_frames >= max_frames:
                    break
                
                # YOLO inference
                timestamp = (frame_count / fps)
                results = self.model(frame, conf=0.5, verbose=False)
                
                # Extract pupil data from YOLO detections
                self._process_yolo_results(
                    results, 
                    frame, 
                    frame_count=frame_count, 
                    timestamp=timestamp,
                    fps=fps
                )
                
                analyzed_frames += 1
                frame_count += 1
                
                if analyzed_frames % 30 == 0:  # Log every 30 frames
                    logger.info(f"Processed {analyzed_frames * frame_pool} frames ({analyzed_frames} analyzed)")
        
        finally:
            cap.release()
        
        logger.info(f"✅ Analysis complete: {analyzed_frames} frames analyzed")
        return len(self.pupil_frames) > 0
    
    def _process_yolo_results(
        self,
        results,
        frame: np.ndarray,
        frame_count: int,
        timestamp: float,
        fps: float
    ) -> None:
        """
        Process YOLO results and extract pupil diameter/position.
        
        YOLO detects eyes, we calculate diameter from bounding box.
        """
        for result in results:
            if result.boxes is None:
                continue
            
            for box in result.boxes:
                # Extract bounding box (in pixels)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                
                # Calculate diameter and center
                width = x2 - x1
                height = y2 - y1
                diameter = (width + height) / 2  # Average of width and height
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                area = width * height
                
                # Store frame data
                self.pupil_frames.append(PupilFrame(
                    frame_number=frame_count,
                    timestamp=timestamp,
                    diameter_px=float(diameter),
                    position_x=float(center_x),
                    position_y=float(center_y),
                    confidence=conf,
                    eye_area_px=int(area)
                ))
    
    def calculate_plr_metrics(
        self,
        light_stimulus_start_frame: int,
        light_stimulus_end_frame: int
    ) -> PLRMetrics:
        """
        Calculate PLR biomarkers using Bergamin-Kardon method.
        
        Args:
            light_stimulus_start_frame: Frame index when light turns on
            light_stimulus_end_frame: Frame index when light turns off
            
        Returns:
            PLRMetrics dataclass with all computed parameters
        """
        if not self.pupil_frames:
            raise ValueError("No pupil frames detected. Run extract_frames_from_video() first.")
        
        # Extract diameter and timestamp arrays
        diameters = np.array([f.diameter_px for f in self.pupil_frames])
        timestamps = np.array([f.timestamp for f in self.pupil_frames])
        
        logger.info(f"Calculating PLR metrics...")
        logger.info(f"Stimulus: frames {light_stimulus_start_frame} to {light_stimulus_end_frame}")
        
        # === BASELINE CALCULATION ===
        baseline_diameters = diameters[:light_stimulus_start_frame]
        baseline_mean = np.mean(baseline_diameters)
        baseline_max = np.max(baseline_diameters)
        baseline_min = np.min(baseline_diameters)
        
        logger.info(f"Baseline: mean={baseline_mean:.2f}, max={baseline_max:.2f}, min={baseline_min:.2f}")
        
        # === LATENCY CALCULATION (Bergamin-Kardon Method) ===
        stim_time = timestamps[light_stimulus_start_frame]
        latency_frame_idx, _ = self._bergamin_kardon_method(timestamps, diameters, stim_time)
        latency = timestamps[latency_frame_idx] - stim_time
        
        logger.info(f"Latency: {latency*1000:.1f} ms (frame {latency_frame_idx})")
        
        # === VELOCITY AND AMPLITUDE CALCULATIONS ===
        min_diameter = np.inf
        min_diameter_frame = light_stimulus_start_frame
        
        peak_constr_vel = -np.inf  # Most negative (closing)
        peak_constr_vel_frame = light_stimulus_start_frame
        
        peak_dilat_vel = np.inf  # Most positive (opening)
        peak_dilat_vel_frame = light_stimulus_end_frame
        
        # Calculate velocity using 3-point numerical derivative
        for i in range(light_stimulus_start_frame + 1, len(diameters) - 1):
            if i < len(timestamps) - 1:
                # 3-point derivative: (d[i+1] - d[i-1]) / (t[i+1] - t[i-1])
                dt = timestamps[i + 1] - timestamps[i - 1]
                if dt > 0:
                    velocity = (diameters[i + 1] - diameters[i - 1]) / dt
                    
                    # Peak constriction velocity (most negative)
                    if velocity < peak_constr_vel:
                        peak_constr_vel = velocity
                        peak_constr_vel_frame = i
                    
                    # Peak dilation velocity (most positive, after stimulus ends)
                    if i >= light_stimulus_end_frame and velocity > peak_dilat_vel:
                        peak_dilat_vel = velocity
                        peak_dilat_vel_frame = i
            
            # Minimum diameter
            if diameters[i] < min_diameter:
                min_diameter = diameters[i]
                min_diameter_frame = i
        
        amplitude = baseline_mean - min_diameter
        
        logger.info(f"Minimum diameter: {min_diameter:.2f} (frame {min_diameter_frame})")
        logger.info(f"Amplitude: {amplitude:.2f}")
        logger.info(f"Peak constriction velocity: {peak_constr_vel:.4f} px/s")
        logger.info(f"Peak dilation velocity: {peak_dilat_vel:.4f} px/s")
        
        # === AVERAGE VELOCITIES ===
        avg_constr_velocity = (
            (diameters[min_diameter_frame] - diameters[light_stimulus_start_frame]) /
            (timestamps[min_diameter_frame] - timestamps[light_stimulus_start_frame])
        )
        
        avg_dilat_velocity = (
            (diameters[-1] - diameters[min_diameter_frame]) /
            (timestamps[-1] - timestamps[min_diameter_frame])
        )
        
        # === PUPIL RECOVERY TIME (PRT) ===
        prt_50, prt_63, prt_75 = self._calculate_prt(
            diameters, timestamps, light_stimulus_end_frame,
            baseline_mean, min_diameter
        )
        
        logger.info(f"PRT-50: {prt_50*1000:.1f} ms, PRT-63: {prt_63*1000:.1f} ms, PRT-75: {prt_75*1000:.1f} ms")
        
        # Create and return metrics
        self.metrics = PLRMetrics(
            baseline_mean=float(baseline_mean),
            baseline_max=float(baseline_max),
            baseline_min=float(baseline_min),
            latency=float(latency),
            latency_frame_idx=int(latency_frame_idx),
            peak_constriction_velocity=float(peak_constr_vel),
            peak_constriction_velocity_frame=int(peak_constr_vel_frame),
            average_constriction_velocity=float(avg_constr_velocity),
            minimum_diameter=float(min_diameter),
            minimum_diameter_frame=int(min_diameter_frame),
            amplitude=float(amplitude),
            peak_dilation_velocity=float(peak_dilat_vel),
            peak_dilation_velocity_frame=int(peak_dilat_vel_frame),
            average_dilation_velocity=float(avg_dilat_velocity),
            prt_50=float(prt_50),
            prt_63=float(prt_63),
            prt_75=float(prt_75)
        )
        
        return self.metrics
    
    def _bergamin_kardon_method(
        self,
        time: np.ndarray,
        signal: np.ndarray,
        stim_time: float
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate latency using Bergamin-Kardon method.
        
        Uses:
        1. Savitzky-Golay filter (5-point, 2nd order)
        2. Cubic spline interpolation to 300 Hz
        3. First derivative (velocity)
        4. Gaussian filter on first derivative (sigma=25)
        5. Second derivative (acceleration)
        6. Maximum negative acceleration after stimulus
        
        Returns:
            (latency_frame_index, visualization_data)
        """
        # Step 1: Savitzky-Golay filter
        signal_smoothed = savgol_filter(signal, window_length=5, polyorder=2)
        
        # Step 2: Cubic spline interpolation
        f_spline = CubicSpline(time, signal_smoothed)
        t_interp = np.linspace(time[0], time[-1], int((time[-1] - time[0]) * 300) + 1)
        signal_interp = f_spline(t_interp)
        
        # Step 3: First derivative
        deriv1 = np.gradient(signal_interp, t_interp[1] - t_interp[0])
        
        # Step 4: Gaussian filter
        deriv1_filtered = gaussian_filter1d(deriv1, sigma=25)
        
        # Step 5: Second derivative
        deriv2 = np.gradient(deriv1_filtered, t_interp[1] - t_interp[0])
        
        # Step 6: Find maximum negative acceleration after stimulus
        mask = t_interp >= stim_time
        if not np.any(mask):
            idx_rel = 0
        else:
            idx_rel = np.argmin(deriv2[mask])
        
        idx_interp = np.where(mask)[0][0] + idx_rel
        
        # Map back to original frame index
        frame_idx = int(idx_interp * (len(signal) / len(signal_interp)))
        
        return frame_idx, {
            "type": "acceleration",
            "deriv1": deriv1_filtered,
            "deriv2": deriv2,
            "t_interp": t_interp
        }
    
    def _calculate_prt(
        self,
        diameters: np.ndarray,
        timestamps: np.ndarray,
        stim_end_frame: int,
        baseline_mean: float,
        min_diameter: float
    ) -> Tuple[float, float, float]:
        """
        Calculate Pupil Recovery Time (PRT) at 50%, 63%, 75% recovery levels.
        
        Recovery is measured from minimum diameter back towards baseline.
        """
        amplitude = baseline_mean - min_diameter
        
        prt_50 = None
        prt_63 = None
        prt_75 = None
        threshold_50 = min_diameter + amplitude * 0.50
        threshold_63 = min_diameter + amplitude * 0.63
        threshold_75 = min_diameter + amplitude * 0.75
        
        stim_end_time = timestamps[stim_end_frame]
        
        for i in range(stim_end_frame, len(diameters)):
            if prt_50 is None and diameters[i] >= threshold_50:
                prt_50 = timestamps[i] - stim_end_time
            if prt_63 is None and diameters[i] >= threshold_63:
                prt_63 = timestamps[i] - stim_end_time
            if prt_75 is None and diameters[i] >= threshold_75:
                prt_75 = timestamps[i] - stim_end_time
                break
        
        return (
            prt_50 or (timestamps[-1] - stim_end_time),
            prt_63 or (timestamps[-1] - stim_end_time),
            prt_75 or (timestamps[-1] - stim_end_time)
        )
    
    def extract_key_frames_for_preview(
        self,
        video_path: str,
        num_frames: int = 9
    ) -> List[Dict[str, Any]]:
        """
        Extract equally-spaced key frames from video for quick preview/testing.
        
        Optimized for UI preview: returns frame images + YOLO detections
        without storing full analysis in self.pupil_frames.
        
        Args:
            video_path: Path to video file
            num_frames: Number of key frames to extract
            
        Returns:
            List of dicts with keys:
            - frame_number: int
            - image: np.ndarray (BGR)
            - diameter_px: float
            - confidence: float
            - position: tuple (center_x, center_y)
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate equally-spaced frame indices
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        key_frames_data = []
        
        logger.info(f"Extracting {num_frames} key frames from {total_frames} total frames")
        
        try:
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                
                timestamp = frame_idx / fps
                
                # Run YOLO inference
                results = self.model(frame, conf=0.5, verbose=False)
                
                # Extract first detection (usually largest/most confident)
                diameter = None
                confidence = 0.0
                center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
                
                if results and results[0].boxes is not None:
                    for box in results[0].boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        
                        width = x2 - x1
                        height = y2 - y1
                        diameter = (width + height) / 2
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        confidence = conf
                        break  # Use first detection
                
                if diameter is None:
                    diameter = 35.0  # Default fallback
                
                key_frames_data.append({
                    'frame_number': frame_idx,
                    'image': frame,
                    'diameter_px': float(diameter),
                    'confidence': confidence,
                    'position': (float(center_x), float(center_y)),
                    'timestamp': float(timestamp)
                })
        
        finally:
            cap.release()
        
        logger.info(f"✅ Extracted {len(key_frames_data)} key frames")
        return key_frames_data
