"""
Pupil Light Reflex (PLR) Analysis Module

Analyzes patient videos for pupil detection and calculates PLR biomarkers
using YOLO object detection for pupil localization and the
Bergamin-Kardon method for latency calculation.

Detection pipeline:
1. Crop left and right eye regions from 1280x720 frame
2. Run YOLO inference on each eye crop (TFLite model)
3. Calculate pupil diameter from bounding box dimensions
4. Convert pixel diameter to millimeters using calibration factor
5. PLR biomarker calculation from diameter time series

Features:
- YOLO-based pupil detection (same model as TBI Android app)
- Dual-eye detection with fixed eye crop regions
- Temporal filtering (Savitzky-Golay, Gaussian)
- PLR parameter calculation (amplitude, latency, constriction/dilation velocity)
- Lightweight: TFLite inference (no CUDA required)
"""

import os
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

# Pixel-to-millimeter calibration factor for the TBI headset camera.
# Matches the Android app value (Factors.kt: pixelConversionFactor = 0.07).
# Applies to the cropped eye region coordinate space.
MM_PER_PIXEL = 0.07

# Eye crop coordinates for 1280x720 TBI headset frames.
# From Android app EyeCoordinates.kt -- assumes fixed headset camera geometry.
LEFT_EYE_X = 30
LEFT_EYE_Y = 140
LEFT_EYE_W = 380
LEFT_EYE_H = 320
RIGHT_EYE_X = 850
RIGHT_EYE_Y = 140
RIGHT_EYE_W = 380
RIGHT_EYE_H = 320
REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720

# YOLO detection thresholds (matching Android app YOLODetector.kt)
YOLO_CONFIDENCE = 0.6
YOLO_IOU = 0.5

# Default model path relative to project root
YOLO_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "best_float32_230.tflite"
)


@dataclass
class PupilFrame:
    """Data class for per-frame pupil detection results."""
    frame_number: int
    timestamp: float  # seconds
    diameter_px: float
    position_x: float  # center x coordinate in pixels
    position_y: float  # center y coordinate in pixels
    confidence: float  # Detection confidence (0.0 - 0.99)
    eye_area_px: int  # Detected circle area in pixels
    eye_index: int = 0  # 0=primary (left-most), 1=secondary (right-most)


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
    peak_constriction_velocity: float  # mm/s
    peak_constriction_velocity_frame: int
    average_constriction_velocity: float  # mm/s
    
    # Minimum diameter (mm)
    minimum_diameter: float
    minimum_diameter_frame: int
    amplitude: float  # baseline_mean - minimum_diameter (mm)
    
    # Dilation phase (pupil reopening)
    peak_dilation_velocity: float  # mm/s
    peak_dilation_velocity_frame: int
    average_dilation_velocity: float  # mm/s
    
    # Pupil Recovery Time (PRT)
    prt_50: Optional[float] = None  # seconds to 50% recovery
    prt_63: Optional[float] = None  # seconds to 63% recovery (1/e)
    prt_75: Optional[float] = None  # seconds to 75% recovery


class PupilAnalyzer:
    """
    Main class for pupil analysis pipeline.

    Detection uses Ultralytics YOLO with a TFLite model trained on pupil images:
    - Crop left and right eye regions from the full frame
    - Run YOLO inference on each crop to detect the pupil bounding box
    - Calculate diameter from bounding box dimensions
    - Convert to millimeters using calibrated pixel conversion factor

    Workflow:
    1. Load video file
    2. Frame extraction with optional pooling
    3. Eye region cropping (fixed coordinates for TBI headset)
    4. YOLO pupil detection per eye crop
    5. Diameter calculation and mm conversion
    6. PLR biomarker calculation
    """

    def __init__(self, model_path: str = None):
        """
        Initialize pupil analyzer with YOLO detection model.

        Args:
            model_path: Path to YOLO TFLite model file.
                        Defaults to models/best_float32_230.tflite in project root.
        """
        self.pupil_frames: List[PupilFrame] = []
        self.all_detections: Dict[int, List[PupilFrame]] = {}
        self.metrics: Optional[PLRMetrics] = None

        # Load YOLO model
        path = model_path or YOLO_MODEL_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"YOLO model not found: {path}\n"
                f"Place best_float32_230.tflite in the models/ directory."
            )
        self._model = YOLO(path, task="detect")
        logger.info(f"PupilAnalyzer initialized (YOLO pipeline, model: {os.path.basename(path)})")

    def _crop_eyes(self, frame: np.ndarray) -> List[Tuple[np.ndarray, int, int, int, int, int]]:
        """
        Crop left and right eye regions from a full video frame.

        Coordinates are scaled proportionally if the frame is not 1280x720.

        Args:
            frame: BGR video frame (numpy array)

        Returns:
            List of tuples: (crop_image, eye_index, crop_x, crop_y, crop_w, crop_h)
            where eye_index 0 = left eye, 1 = right eye.
        """
        h, w = frame.shape[:2]

        # Scale factor if frame is not reference resolution
        sx = w / REFERENCE_WIDTH
        sy = h / REFERENCE_HEIGHT

        crops = []
        for eye_idx, (ex, ey, ew, eh) in enumerate([
            (LEFT_EYE_X, LEFT_EYE_Y, LEFT_EYE_W, LEFT_EYE_H),
            (RIGHT_EYE_X, RIGHT_EYE_Y, RIGHT_EYE_W, RIGHT_EYE_H),
        ]):
            # Scale coordinates to actual frame size
            x = int(ex * sx)
            y = int(ey * sy)
            crop_w = int(ew * sx)
            crop_h = int(eh * sy)

            # Clamp to frame bounds
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            x2 = min(x + crop_w, w)
            y2 = min(y + crop_h, h)

            crop = frame[y:y2, x:x2]
            if crop.size > 0:
                crops.append((crop, eye_idx, x, y, x2 - x, y2 - y))

        return crops

    def _detect_pupil_in_crop(
        self, crop: np.ndarray, eye_index: int,
        crop_x: int, crop_y: int, crop_w: int, crop_h: int,
        frame_count: int, timestamp: float
    ) -> Optional[PupilFrame]:
        """
        Run YOLO detection on a single eye crop and return a PupilFrame.

        Diameter is calculated from the bounding box dimensions using the
        same formula as the PLR-Analyzer Android app referenced File (AnalyzerScreen.kt):
            diameter_px = (bbox_w_norm * crop_W + bbox_h_norm * crop_H) / 2.0

        The normalized bbox dimensions are scaled to crop-region pixels,
        averaged (width + height), giving the equivalent circular diameter.

        Args:
            crop: Cropped eye region (BGR numpy array)
            eye_index: 0 = left eye, 1 = right eye
            crop_x, crop_y: Top-left corner of crop in full frame
            crop_w, crop_h: Dimensions of the crop region
            frame_count: Current frame index
            timestamp: Frame timestamp in seconds

        Returns:
            PupilFrame if pupil detected, None otherwise
        """
        results = self._model(crop, conf=YOLO_CONFIDENCE, iou=YOLO_IOU, verbose=False)
        boxes = results[0].boxes

        if boxes is None or len(boxes) == 0:
            return None

        # Select highest confidence detection
        best_idx = int(boxes.conf.argmax())

        # Normalized bounding box (0-1 relative to crop dimensions)
        xywhn = boxes.xywhn[best_idx].cpu().numpy()
        bbox_w_norm = float(xywhn[2])
        bbox_h_norm = float(xywhn[3])

        # Diameter in crop-region pixels (same formula as Android app)
        diameter_px = (bbox_w_norm * crop_w + bbox_h_norm * crop_h) / 2.0

        # Detection confidence from YOLO
        confidence = float(boxes.conf[best_idx].cpu())

        # Bounding box center in crop-local pixels
        xywh = boxes.xywh[best_idx].cpu().numpy()
        local_cx = float(xywh[0])
        local_cy = float(xywh[1])
        local_w = float(xywh[2])
        local_h = float(xywh[3])

        # Map position to full-frame coordinates
        full_x = crop_x + local_cx
        full_y = crop_y + local_cy

        # Estimated area from bounding box
        area_px = int(local_w * local_h)

        return PupilFrame(
            frame_number=frame_count,
            timestamp=timestamp,
            diameter_px=diameter_px,
            position_x=full_x,
            position_y=full_y,
            confidence=confidence,
            eye_area_px=area_px,
            eye_index=eye_index
        )

    def extract_frames_from_video(
        self,
        video_path: str,
        frame_pool: int = 1,
        max_frames: Optional[int] = None
    ) -> bool:
        """
        Extract frames from video and detect pupils using YOLO.

        Args:
            video_path: Path to video file
            frame_pool: Process every nth frame (1=all, 2=every 2nd, etc.)
            max_frames: Limit analysis to first N frames (for testing)

        Returns:
            True if at least one pupil was detected, False otherwise
        """
        logger.info(f"Opening video: {video_path}")
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return False

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Video: {fps} FPS, {total_frames} frames total")
        logger.info(f"Frame pooling: every {frame_pool}th frame "
                     f"= {total_frames // frame_pool} effective frames")

        # Reset state for new video
        self.pupil_frames = []
        self.all_detections = {}

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

                # Limit total frames analyzed (for testing)
                if max_frames and analyzed_frames >= max_frames:
                    break

                timestamp = frame_count / fps
                self._detect_pupil(frame, frame_count, timestamp)

                analyzed_frames += 1
                frame_count += 1

                if analyzed_frames % 30 == 0:
                    logger.info(f"Processed {analyzed_frames * frame_pool} "
                                f"frames ({analyzed_frames} analyzed)")

        finally:
            cap.release()

        detected = sum(1 for pf in self.pupil_frames if not np.isnan(pf.diameter_px))
        logger.info(f"Analysis complete: {analyzed_frames} frames analyzed, "
                    f"{detected} detections")
        return len(self.pupil_frames) > 0

    def _detect_pupil(
        self, frame: np.ndarray, frame_count: int, timestamp: float
    ) -> None:
        """
        Detect pupils in both eyes using YOLO on cropped eye regions.

        Pipeline:
        1. Crop left and right eye regions from full frame
        2. Run YOLO inference on each crop
        3. Calculate diameter from bounding box
        4. Store detections

        Results stored in:
        - self.pupil_frames: primary eye (left, eye_index=0) for PLR metrics
        - self.all_detections[frame_count]: all detected eyes

        Args:
            frame: BGR video frame (numpy array)
            frame_count: Current frame index in the video
            timestamp: Timestamp of this frame in seconds
        """
        eye_crops = self._crop_eyes(frame)
        frame_detections = []

        for crop, eye_idx, cx, cy, cw, ch in eye_crops:
            pf = self._detect_pupil_in_crop(
                crop, eye_idx, cx, cy, cw, ch, frame_count, timestamp
            )
            if pf is not None:
                frame_detections.append(pf)
                logger.debug(f"Frame {frame_count}: Eye {eye_idx} "
                            f"diameter={pf.diameter_px:.1f}px, conf={pf.confidence:.2f}")

        self.all_detections[frame_count] = frame_detections

        # Store primary eye (left, eye_index=0) in pupil_frames for PLR metrics
        primary = [d for d in frame_detections if d.eye_index == 0]
        if primary:
            self.pupil_frames.append(primary[0])
        elif frame_detections:
            # Only one eye detected -- use whichever we have
            self.pupil_frames.append(frame_detections[0])
        else:
            # No detection in either eye
            self.pupil_frames.append(PupilFrame(
                frame_number=frame_count,
                timestamp=timestamp,
                diameter_px=np.nan,
                position_x=np.nan,
                position_y=np.nan,
                confidence=0.0,
                eye_area_px=0
            ))


    def detect_light_stimulus_frames(
        self, light_duration: float = 1.0
    ) -> tuple:
        """
        Detect light stimulus onset from pupil constriction pattern.

        Uses the point of steepest diameter decrease (maximum negative
        velocity) to infer when the light turned on, accounting for
        ~200 ms PLR latency.  This is more robust than relying on
        hardcoded timestamps because the video file may not start at
        the same moment the recording thread begins timing. This is a
        oint to discuss with the developers of the PLR-Analyzer, 
        because the Android app relies on the recording thread timing to determine 
        the light stimulus onset and offset frames. 
        If the video file starts at a different time than the recording thread, 
        this could lead to misalignment between the detected pupil frames and the actual stimulus timing. 
        By analyzing the pupil diameter changes directly, we can more accurately determine when the light stimulus occurred, 
        regardless of any discrepancies in video start time.
        But this theorie must be tested and validated in future experiments, i think.
        The fact that the latency is 0.00 in the tests could be an indication that the video 
        start time and the recording thread timing are not perfectly aligned, leading to incorrect stimulus onset detection.
        If 0.00 ms occurs only rarely, it may also be caused by frame resolution, smoothing, or rounding effects.
        If 0.00 ms occurs frequently, it is a strong indication that the stimulus detection or the timing concept should be reviewed.

        Since this function was not the priority and the focus was on pupil detection with YOLO, I will leave it as a hypothesis for now.

        Args:
            light_duration: Expected duration of light stimulus in seconds
                            (default 1.0 s).

        Returns:
            (start_frame, end_frame) indices into self.pupil_frames.
        """
        if not self.pupil_frames:
            raise ValueError("No pupil frames available.")

        diameters = np.array([f.diameter_px for f in self.pupil_frames])
        timestamps = np.array([f.timestamp for f in self.pupil_frames])

        # Interpolate NaN values for velocity calculation
        nan_mask = np.isnan(diameters)
        if np.sum(~nan_mask) >= 2:
            diameters_clean = diameters.copy()
            diameters_clean[nan_mask] = np.interp(
                np.where(nan_mask)[0],
                np.where(~nan_mask)[0],
                diameters[~nan_mask]
            )
        else:
            diameters_clean = diameters

        # Smooth to reduce noise before differentiation
        from scipy.signal import savgol_filter
        if len(diameters_clean) >= 7:
            smooth = savgol_filter(diameters_clean, window_length=7, polyorder=2)
        else:
            smooth = diameters_clean

        # Numerical velocity (3-point central difference)
        n = len(smooth)
        velocity = np.zeros(n)
        for i in range(1, n - 1):
            dt = timestamps[i + 1] - timestamps[i - 1]
            if dt > 0:
                velocity[i] = (smooth[i + 1] - smooth[i - 1]) / dt

        # Maximum constriction velocity = most negative velocity
        # Search only in first 60% of recording to avoid confusing recovery
        search_end = int(n * 0.6)
        if search_end < 3:
            search_end = n - 1
        max_constr_idx = int(np.argmin(velocity[1:search_end]) + 1)

        # Light onset ≈ max-constriction time − 200 ms PLR latency
        PLR_LATENCY = 0.2  # seconds
        light_onset_time = timestamps[max_constr_idx] - PLR_LATENCY
        light_onset_time = max(0.0, light_onset_time)
        light_end_time = light_onset_time + light_duration

        # Convert times back to frame indices
        start_frame = int(np.argmin(np.abs(timestamps - light_onset_time)))
        end_frame = int(np.argmin(np.abs(timestamps - light_end_time)))

        # Clamp to valid range
        start_frame = max(1, min(start_frame, n - 2))
        end_frame = max(start_frame + 1, min(end_frame, n - 1))

        logger.info(
            f"Auto-detected light stimulus: "
            f"frames {start_frame}-{end_frame} "
            f"({timestamps[start_frame]:.2f}-{timestamps[end_frame]:.2f}s), "
            f"max constriction at frame {max_constr_idx} ({timestamps[max_constr_idx]:.2f}s)"
        )
        return start_frame, end_frame

    def calculate_plr_metrics(
        self,
        light_stimulus_start_frame: int,
        light_stimulus_end_frame: int
    ) -> PLRMetrics:
        """
        Calculate PLR biomarkers using Bergamin-Kardon method.
        Wichtigste PLR-Parameter: Amplitude, Latency, Peak Constriction Velocity, Peak Dilation Velocity, Pupil Recovery Time (PRT)
        Args:
            light_stimulus_start_frame: Frame index when light turns on
            light_stimulus_end_frame: Frame index when light turns off
            
        Returns:
            PLRMetrics dataclass with all computed parameters
        """
        if not self.pupil_frames:
            raise ValueError("No pupil frames detected. Run extract_frames_from_video() first.")
        
        # Extract diameter array and convert from pixels to millimeters
        diameters = np.array([f.diameter_px for f in self.pupil_frames]) * MM_PER_PIXEL
        timestamps = np.array([f.timestamp for f in self.pupil_frames])
        
        # Interpolate NaN values (missed detections) for smooth analysis
        nan_mask = np.isnan(diameters)
        nan_count = np.sum(nan_mask)
        if nan_count > 0:
            logger.info(f"Interpolating {nan_count} NaN frames ({100*nan_count/len(diameters):.0f}%)")
            valid = ~nan_mask
            if np.sum(valid) >= 2:
                diameters[nan_mask] = np.interp(
                    np.where(nan_mask)[0],
                    np.where(valid)[0],
                    diameters[valid]
                )
            else:
                raise ValueError("Not enough valid detections for PLR analysis")
        
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
        
        peak_constr_vel = np.inf  # Will be replaced by most negative velocity
        peak_constr_vel_frame = light_stimulus_start_frame
        
        peak_dilat_vel = -np.inf  # Will be replaced by most positive velocity
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
        logger.info(f"Peak constriction velocity: {peak_constr_vel:.4f} mm/s")
        logger.info(f"Peak dilation velocity: {peak_dilat_vel:.4f} mm/s")
        
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
        
        # Step 4: Gaussian filter // Maybe test it later with 15? combined with another polyorder for the Savitz filter?
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
        
        # Map back to original frame index. After Fixxx This maps the timestamp of the detected acceleration maximum directly to the nearest original frame independent of the interpolation rate. Reason why Latency 0.00 in Tests
        frame_idx = int(np.argmin(np.abs(time - t_interp[idx_interp])))
        
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
        Like in the Android app, we define thresholds as:
        threshold = min_diameter + amplitude * recovery_level sprich 0.50, 0.63, 0.75
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
        Extract equally-spaced key frames from video for quick preview.

        Runs YOLO detection on each key frame independently.
        Detects both eyes per frame.

        Args:
            video_path: Path to video file
            num_frames: Number of key frames to extract

        Returns:
            List of dicts with keys:
            - frame_number: int
            - image: np.ndarray (BGR)
            - diameter_px: float (primary eye)
            - confidence: float (primary eye)
            - position: tuple (center_x, center_y) (primary eye)
            - all_eyes: list of dicts with position, diameter, confidence
            - timestamp: float
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        key_frames_data = []

        logger.info(f"Extracting {num_frames} key frames from {total_frames} total")

        try:
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                timestamp = frame_idx / fps

                # Run YOLO detection on eye crops
                eye_crops = self._crop_eyes(frame)
                eye_results = []

                for crop, eye_idx, cx, cy, cw, ch in eye_crops:
                    pf = self._detect_pupil_in_crop(
                        crop, eye_idx, cx, cy, cw, ch, int(frame_idx), timestamp
                    )
                    if pf is not None:
                        eye_results.append({
                            'position': (pf.position_x, pf.position_y),
                            'diameter_px': pf.diameter_px,
                            'confidence': pf.confidence
                        })

                if eye_results:
                    primary = eye_results[0]
                    key_frames_data.append({
                        'frame_number': int(frame_idx),
                        'image': frame,
                        'diameter_px': primary['diameter_px'],
                        'confidence': primary['confidence'],
                        'position': primary['position'],
                        'all_eyes': eye_results,
                        'timestamp': float(timestamp)
                    })
                else:
                    key_frames_data.append({
                        'frame_number': int(frame_idx),
                        'image': frame,
                        'diameter_px': 0.0,
                        'confidence': 0.0,
                        'position': (float(frame.shape[1] // 2),
                                     float(frame.shape[0] // 2)),
                        'all_eyes': [],
                        'timestamp': float(timestamp)
                    })

        finally:
            cap.release()

        logger.info(f"Extracted {len(key_frames_data)} key frames")
        return key_frames_data
