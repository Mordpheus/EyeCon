"""
Pupil Light Reflex (PLR) Analysis Module

Analyzes patient videos for pupil detection and calculates PLR biomarkers
using classical computer vision (IR Corneal Reflex + Hough Circles) and
Bergamin-Kardon method for latency calculation.

Detection pipeline:
1. Detect bright IR corneal reflections as eye anchor points
2. Set ROI around each reflection (guaranteed eye area)
3. CLAHE contrast enhancement within ROI
4. Hough Circle Detection for dark pupil within ROI
5. Multi-factor scoring (darkness, size, proximity to IR reflex)
6. Temporal tracking for frame-to-frame consistency

Features:
- Frame-by-frame pupil detection (classical CV, no neural network)
- IR-reflex-anchored ROI (robust for IR close-up cameras)
- Temporal filtering (Savitzky-Golay, Gaussian)
- PLR parameter calculation (amplitude, latency, constriction/dilation velocity)
- Database persistence
- Lightweight: uses only OpenCV + NumPy (no PyTorch/CUDA required)
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

logger = logging.getLogger(__name__)

# IR reflex detection: minimum brightness threshold percentile
_IR_REFLEX_BRIGHTNESS_PERCENTILE = 99.5

# Anatomical Y-band for eye position in mask recordings:
# Eyes are never in the top 25% (forehead/mask) or bottom 33% (nose/mask).
_EYE_Y_MIN_RATIO = 0.25
_EYE_Y_MAX_RATIO = 0.67

# Pixel-to-millimeter calibration factor for the IR camera at 640x480.
# Derived from typical Pi NoIR close-up eye distance.
# Adjust if camera setup changes.
MM_PER_PIXEL = 0.1


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

    Detection uses classical computer vision (no neural network):
    - IR corneal reflex detection for eye localization
    - Hough Circle Detection for pupil candidates within the eye ROI
    - Multi-factor scoring: darkness + size + proximity to IR reflex
    - Temporal tracking to stabilize detections across frames

    Workflow:
    1. Load video file
    2. Frame extraction with optional pooling
    3. IR corneal reflex detection (bright hotspot = eye center)
    4. ROI around each reflex
    5. Pupil detection within ROI (Hough Circles + scoring)
    6. Temporal filtering and smoothing
    7. PLR biomarker calculation
    8. Database persistence
    """

    # Hough Circle Detection parameters
    HOUGH_DP = 1.2              # Accumulator resolution ratio
    HOUGH_MIN_DIST = 30         # Min distance between detected circle centers
    HOUGH_PARAM1 = 50           # Upper Canny edge threshold
    HOUGH_PARAM2 = 22           # Accumulator threshold (lower = more sensitive)
    HOUGH_MIN_RADIUS = 5        # Minimum pupil radius in pixels
    HOUGH_MAX_RADIUS = 55       # Maximum pupil radius in pixels

    # CLAHE parameters for contrast enhancement
    CLAHE_CLIP_LIMIT = 3.0      # Contrast amplification limit
    CLAHE_TILE_SIZE = (8, 8)    # Grid size for local histogram equalization

    # Scoring weights for circle candidate evaluation
    SCORE_SIZE_WEIGHT = 1.5     # Penalty per radius pixel (prefer small circles)
    SCORE_POSITION_WEIGHT = 0.3 # Penalty per pixel distance from IR reflex center

    # Confidence normalization threshold (intensity at which confidence = 0)
    CONFIDENCE_NORM = 180.0

    # Temporal tracking: max pixel displacement between consecutive frames
    TRACKING_MAX_JUMP = 80

    # IR corneal reflex detection parameters
    IR_ROI_HALF_SIZE = 100      # Half-width of ROI around each IR reflex (px)
    IR_MIN_SEPARATION = 80      # Min distance between two IR reflexes (px)
    IR_REFLEX_MIN_AREA = 3      # Min contour area for a valid IR reflex
    IR_REFLEX_MAX_AREA = 300    # Max contour area for a valid IR reflex

    def __init__(self):
        """
        Initialize pupil analyzer with IR-reflex-anchored CV pipeline.

        No external model files required. Uses IR corneal reflections
        (bright hotspots visible in IR camera footage) to locate eyes.
        Detects BOTH eyes independently per frame.
        """
        # Primary eye frames (left-most eye, used for PLR metrics)
        self.pupil_frames: List[PupilFrame] = []
        # All eye detections per frame: {frame_number: [PupilFrame, ...]}
        self.all_detections: Dict[int, List[PupilFrame]] = {}
        self.metrics: Optional[PLRMetrics] = None

        # Per-eye temporal tracking: {eye_index: (x, y)}
        self._last_positions: Dict[int, Tuple[float, float]] = {}
        # Per-eye consecutive miss counters
        self._consecutive_misses: Dict[int, int] = {0: 0, 1: 0}
        self._MISS_RESET_THRESHOLD: int = 3

        logger.info("PupilAnalyzer initialized (IR-reflex dual-eye pipeline)")
    
    def extract_frames_from_video(
        self,
        video_path: str,
        frame_pool: int = 1,
        max_frames: Optional[int] = None
    ) -> bool:
        """
        Extract frames from video and detect pupils using classical CV.

        Performance optimization: frame_pool=2 processes every 2nd frame,
        reducing computation by ~50% with minimal quality loss.

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
        self._last_positions = {}
        self._consecutive_misses = {0: 0, 1: 0}

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
                self._detect_pupil(
                    frame=frame,
                    frame_count=frame_count,
                    timestamp=timestamp
                )

                analyzed_frames += 1
                frame_count += 1

                if analyzed_frames % 30 == 0:
                    logger.info(f"Processed {analyzed_frames * frame_pool} "
                                f"frames ({analyzed_frames} analyzed)")

        finally:
            cap.release()

        logger.info(f"Analysis complete: {analyzed_frames} frames analyzed")
        return len(self.pupil_frames) > 0
    
    def _detect_ir_reflections(self, gray: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect bright IR corneal reflections in a grayscale IR image.

        The corneal reflection ("glint") is the brightest point in each eye,
        caused by the IR LED reflecting off the cornea. These are trivial to
        detect in IR images and provide reliable eye anchor points.

        Steps:
        1. Threshold at the top brightness percentile
        2. Find contours of bright blobs
        3. Filter by area (reject noise / large bright patches)
        4. Return centroids as (x, y) anchor points

        Args:
            gray: Grayscale image (single channel, uint8)

        Returns:
            List of (center_x, center_y) for each detected IR reflex.
            Typically 1-2 points (one per visible eye).
        """
        h, w = gray.shape

        # Adaptive threshold: use the brightest pixels in the image
        brightness_threshold = np.percentile(gray, _IR_REFLEX_BRIGHTNESS_PERCENTILE)
        # Ensure threshold is at least 200 (reflexes are very bright in IR)
        brightness_threshold = max(brightness_threshold, 200)

        _, binary = cv2.threshold(gray, int(brightness_threshold), 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        reflexes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.IR_REFLEX_MIN_AREA or area > self.IR_REFLEX_MAX_AREA:
                continue

            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])

            # Reject reflexes too close to frame border (noise)
            if cx < 20 or cx > w - 20 or cy < 20 or cy > h - 20:
                continue

            # Reject reflexes outside the anatomical eye band.
            # In mask recordings, eyes are between 25%-67% of frame height.
            # Top 25% = forehead/mask frame, bottom 33% = nose/mask material.
            if cy < h * _EYE_Y_MIN_RATIO or cy > h * _EYE_Y_MAX_RATIO:
                continue

            reflexes.append((cx, cy))

        # Deduplicate: merge reflexes that are too close together
        if len(reflexes) > 1:
            merged = [reflexes[0]]
            for rx, ry in reflexes[1:]:
                too_close = False
                for mx, my in merged:
                    if np.sqrt((rx - mx) ** 2 + (ry - my) ** 2) < self.IR_MIN_SEPARATION:
                        too_close = True
                        break
                if not too_close:
                    merged.append((rx, ry))
            reflexes = merged

        return reflexes

    def _reflexes_to_rois(
        self, reflexes: List[Tuple[int, int]], img_shape: Tuple[int, int]
    ) -> List[Tuple[int, int, int, int]]:
        """
        Convert IR reflex center points into search ROIs.

        Each reflex gets a square ROI of size (2*IR_ROI_HALF_SIZE) centered
        on the reflex point, clipped to image bounds.

        Args:
            reflexes: List of (x, y) reflex center points
            img_shape: (height, width) of the image

        Returns:
            List of (x, y, width, height) ROI rectangles
        """
        h, w = img_shape
        half = self.IR_ROI_HALF_SIZE
        rois = []
        for rx, ry in reflexes:
            x1 = max(0, rx - half)
            y1 = max(0, ry - half)
            x2 = min(w, rx + half)
            y2 = min(h, ry + half)
            rois.append((x1, y1, x2 - x1, y2 - y1))
        return rois

    def _find_best_circle_in_roi(
        self,
        enhanced: np.ndarray,
        roi: Tuple[int, int, int, int]
    ) -> Optional[Tuple[int, int, int, float, float]]:
        """
        Run Hough Circle Detection inside a single ROI and return the best candidate.

        Scoring considers three factors:
        - Darkness: lower mean intensity inside the circle → better score
        - Size: smaller radius → better score (pupils are smaller than irises)
        - Centrality: closer to ROI center → better score

        Args:
            enhanced: CLAHE-enhanced grayscale image (full frame)
            roi: Bounding box (x, y, width, height) to search within

        Returns:
            Tuple (abs_x, abs_y, radius, score, mean_intensity) in full-frame
            coordinates, or None if no valid circle found
        """
        rx, ry, rw, rh = roi
        roi_img = enhanced[ry:ry + rh, rx:rx + rw]

        if roi_img.size == 0:
            return None

        circles = cv2.HoughCircles(
            roi_img,
            cv2.HOUGH_GRADIENT,
            dp=self.HOUGH_DP,
            minDist=self.HOUGH_MIN_DIST,
            param1=self.HOUGH_PARAM1,
            param2=self.HOUGH_PARAM2,
            minRadius=self.HOUGH_MIN_RADIUS,
            maxRadius=self.HOUGH_MAX_RADIUS
        )

        if circles is None:
            return None

        circles = np.uint16(np.around(circles))
        roi_cx, roi_cy = rw / 2, rh / 2

        best = None
        best_score = float('inf')

        for circle in circles[0]:
            cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])

            if r < self.HOUGH_MIN_RADIUS or r > self.HOUGH_MAX_RADIUS:
                continue

            # Reject circles that touch the ROI border (likely partial / wrong structure)
            if cx - r < 2 or cy - r < 2 or cx + r > rw - 2 or cy + r > rh - 2:
                continue

            # Measure mean intensity inside this circle
            mask = np.zeros(roi_img.shape, dtype=np.uint8)
            cv2.circle(mask, (cx, cy), r, 255, -1)
            mean_intensity = cv2.mean(roi_img, mask=mask)[0]

            # Compute distance from ROI center
            dist_from_center = np.sqrt((cx - roi_cx) ** 2 + (cy - roi_cy) ** 2)

            # Combined score: darkness + size penalty + position penalty
            score = (mean_intensity
                     + r * self.SCORE_SIZE_WEIGHT
                     + dist_from_center * self.SCORE_POSITION_WEIGHT)

            if score < best_score:
                best_score = score
                # Convert ROI-local coordinates to full-frame coordinates
                best = (rx + cx, ry + cy, r, score, mean_intensity)

        return best

    def _detect_pupil(
        self,
        frame: np.ndarray,
        frame_count: int,
        timestamp: float
    ) -> None:
        """
        Detect pupils in BOTH eyes using IR-reflex-anchored pipeline.

        Pipeline:
        1. Convert to grayscale
        2. Detect IR corneal reflections (bright hotspots = eye anchors)
        3. Set ROI around EACH reflex (one per eye)
        4. Apply Gaussian blur + CLAHE
        5. Run Hough Circle Detection per ROI
        6. Score candidates (darkness + size + proximity to IR reflex)
        7. Apply per-eye temporal tracking
        8. Store detections for each eye as separate PupilFrames

        Results stored in:
        - self.pupil_frames: primary eye only (left-most, for PLR metrics)
        - self.all_detections[frame_count]: list of all detected eyes

        Args:
            frame: BGR video frame (numpy array)
            frame_count: Current frame index in the video
            timestamp: Timestamp of this frame in seconds
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape

        # Step 1: Pre-process full frame (blur + CLAHE)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)

        # Adaptive CLAHE: adjust clip limit based on overall brightness
        mean_brightness = np.mean(blurred)
        if mean_brightness < 60:
            clip_limit = 5.0   # Dark image: strong contrast boost
        elif mean_brightness > 170:
            clip_limit = 2.0   # Bright image: gentle enhancement
        else:
            clip_limit = self.CLAHE_CLIP_LIMIT  # Normal conditions

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=self.CLAHE_TILE_SIZE)
        enhanced = clahe.apply(blurred)

        # Step 2: Detect IR corneal reflections (expect 0-2 per frame)
        reflexes = self._detect_ir_reflections(gray)

        # Step 2b: Sort reflexes left-to-right so eye_index 0 = left, 1 = right
        if reflexes:
            reflexes.sort(key=lambda r: r[0])

        # Step 2c: Build ROIs — one per reflex, plus fallback from tracking
        reflex_rois = []  # List of (roi, reflex_point_or_None)
        if reflexes:
            rois = self._reflexes_to_rois(reflexes, (h_img, w_img))
            for reflex, roi in zip(reflexes, rois):
                reflex_rois.append((roi, reflex))
        
        # Fallback: if we have tracking positions but no reflexes, search there
        if not reflex_rois:
            for eye_idx, pos in self._last_positions.items():
                lx_i, ly_i = int(pos[0]), int(pos[1])
                half = self.IR_ROI_HALF_SIZE
                sx = max(0, lx_i - half)
                sy = max(0, ly_i - half)
                ex = min(w_img, lx_i + half)
                ey = min(h_img, ly_i + half)
                reflex_rois.append(((sx, sy, ex - sx, ey - sy), None))

        if not reflex_rois:
            # No reflexes, no tracking — cannot detect
            logger.warning(f"Frame {frame_count}: No IR reflexes found")
            self._store_miss(frame_count, timestamp)
            return

        # Step 3: Find best circle in each ROI (one pupil per eye)
        detections = []  # List of (eye_index, x, y, r, score, intensity)

        for idx, (roi, reflex_pt) in enumerate(reflex_rois):
            candidate = self._find_best_circle_in_roi(enhanced, roi)
            if candidate is None:
                continue

            abs_x, abs_y, r, score, mean_intensity = candidate

            # Determine eye index based on X position (left=0, right=1)
            eye_idx = 0 if abs_x < w_img / 2 else 1

            # Per-eye temporal tracking: reject large jumps
            if eye_idx in self._last_positions:
                lx, ly = self._last_positions[eye_idx]
                jump_dist = np.sqrt((abs_x - lx) ** 2 + (abs_y - ly) ** 2)
                if jump_dist > self.TRACKING_MAX_JUMP:
                    continue
                score += jump_dist * 0.3

            detections.append((eye_idx, abs_x, abs_y, r, score, mean_intensity))

        # Step 4: Store detection results for each eye
        frame_detections = []

        if detections:
            # Group by eye_index, keep the best candidate per eye
            best_per_eye: Dict[int, tuple] = {}
            for det in detections:
                eye_idx = det[0]
                score = det[4]
                if eye_idx not in best_per_eye or score < best_per_eye[eye_idx][4]:
                    best_per_eye[eye_idx] = det

            for eye_idx, (_, x, y, r, score, mean_intensity) in best_per_eye.items():
                diameter = 2 * r
                confidence = max(0.0, 1.0 - (mean_intensity / self.CONFIDENCE_NORM))
                confidence = min(confidence, 0.99)

                pf = PupilFrame(
                    frame_number=frame_count,
                    timestamp=timestamp,
                    diameter_px=float(diameter),
                    position_x=float(x),
                    position_y=float(y),
                    confidence=confidence,
                    eye_area_px=int(np.pi * r * r),
                    eye_index=eye_idx
                )
                frame_detections.append(pf)

                # Update per-eye tracking
                self._last_positions[eye_idx] = (float(x), float(y))
                self._consecutive_misses[eye_idx] = 0

                logger.debug(f"Frame {frame_count}: Eye {eye_idx} at ({x}, {y}), "
                             f"diameter={diameter:.1f}px, conf={confidence:.2f}")

        # Store all eye detections for this frame
        self.all_detections[frame_count] = frame_detections

        # Per-eye miss tracking: increment miss counter for eyes NOT detected
        detected_eye_indices = {d.eye_index for d in frame_detections}
        for eye_idx in list(self._consecutive_misses.keys()):
            if eye_idx not in detected_eye_indices:
                self._consecutive_misses[eye_idx] = self._consecutive_misses.get(eye_idx, 0) + 1
                if self._consecutive_misses[eye_idx] >= self._MISS_RESET_THRESHOLD:
                    logger.info(f"Frame {frame_count}: Eye {eye_idx} — "
                                f"{self._consecutive_misses[eye_idx]} consecutive misses, "
                                f"resetting tracking")
                    self._last_positions.pop(eye_idx, None)
                    self._consecutive_misses[eye_idx] = 0

        # Store primary eye (eye_index=0, left) in pupil_frames for PLR metrics
        primary = [d for d in frame_detections if d.eye_index == 0]
        if primary:
            self.pupil_frames.append(primary[0])
        elif frame_detections:
            # Only one eye detected — use whichever we have
            self.pupil_frames.append(frame_detections[0])
        else:
            self._store_miss(frame_count, timestamp)

    def _store_miss(self, frame_count: int, timestamp: float) -> None:
        """
        Record a missed detection and handle tracking reset.

        After _MISS_RESET_THRESHOLD consecutive misses per eye, resets that
        eye's tracking so the next frame does a full search for it.
        """
        for eye_idx in list(self._consecutive_misses.keys()):
            self._consecutive_misses[eye_idx] = self._consecutive_misses.get(eye_idx, 0) + 1
            if self._consecutive_misses[eye_idx] >= self._MISS_RESET_THRESHOLD:
                logger.info(f"Frame {frame_count}: Eye {eye_idx} — "
                            f"{self._consecutive_misses[eye_idx]} consecutive misses, "
                            f"resetting tracking")
                self._last_positions.pop(eye_idx, None)
                self._consecutive_misses[eye_idx] = 0

        logger.warning(f"Frame {frame_count}: No pupil detected")

        # Store empty detection for this frame
        self.all_detections[frame_count] = []
        self.pupil_frames.append(PupilFrame(
            frame_number=frame_count,
            timestamp=timestamp,
            diameter_px=np.nan,
            position_x=np.nan,
            position_y=np.nan,
            confidence=0.0,
            eye_area_px=0
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
        Extract equally-spaced key frames from video for quick preview.

        Runs the full CV detection pipeline on each key frame independently
        (no temporal tracking). Detects BOTH eyes per frame.

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

                # Run single-frame detection using IR reflex anchoring
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (11, 11), 0)
                clahe = cv2.createCLAHE(
                    clipLimit=self.CLAHE_CLIP_LIMIT,
                    tileGridSize=self.CLAHE_TILE_SIZE
                )
                enhanced = clahe.apply(blurred)

                reflexes = self._detect_ir_reflections(gray)

                # Sort left-to-right for consistent eye indexing
                if reflexes:
                    reflexes.sort(key=lambda r: r[0])

                eye_rois = self._reflexes_to_rois(reflexes, gray.shape)

                # Find best circle per ROI (one per eye)
                eye_results = []
                for roi in eye_rois:
                    candidate = self._find_best_circle_in_roi(enhanced, roi)
                    if candidate is not None:
                        cx, cy, r, score, intensity = candidate
                        confidence = max(0.0, 1.0 - (intensity / self.CONFIDENCE_NORM))
                        confidence = min(confidence, 0.99)
                        eye_results.append({
                            'position': (float(cx), float(cy)),
                            'diameter_px': float(2 * r),
                            'confidence': float(confidence)
                        })

                if eye_results:
                    # Primary eye = first (left-most)
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
