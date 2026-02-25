"""
PLR (Pupil Light Reflex) Test Analysis Screen.
Provides visual testing interface for pupil detection on video frames.
"""

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QDialog,
    QProgressBar
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QThread, Signal
from typing import List, Dict, Optional
import logging

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from scipy.signal import savgol_filter

from src.pupil_analyzer import MM_PER_PIXEL

logger = logging.getLogger(__name__)


class PupilFrameWidget(QWidget):
    """Single thumbnail frame with pupil detection info."""
    
    clicked = Signal(int, dict)  # frame_number, frame_data
    
    def __init__(self, frame_number: int, image_data: np.ndarray, 
                 pupil_diameter: float = None, confidence: float = 0.0):
        super().__init__()
        self.frame_number = frame_number
        self.image_data = image_data
        self.pupil_diameter = pupil_diameter
        self.confidence = confidence
        
        self.setFixedSize(200, 150)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Display frame as pixmap
        self.image_label = QLabel()
        self.update_display()
        layout.addWidget(self.image_label)
        
        # Info label
        info_text = f"Frame {frame_number}"
        if pupil_diameter:
            info_text += f"\nØ {pupil_diameter * MM_PER_PIXEL:.2f}mm"
        if confidence > 0:
            info_text += f"\nConf: {confidence:.2f}"
        
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet("font-size: 9px; text-align: center;")
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
            QWidget:hover {
                border: 2px solid #2E7D32;
                background-color: #e8f5e9;
            }
        """)
    
    def update_display(self):
        """Convert numpy array to QPixmap and display."""
        if self.image_data is None:
            return
        
        h, w = self.image_data.shape[:2]
        bytes_per_line = 3 * w if len(self.image_data.shape) == 3 else w
        
        if len(self.image_data.shape) == 3:
            rgb_image = cv2.cvtColor(self.image_data, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            q_img = QImage(self.image_data.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(180, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
    
    def mousePressEvent(self, event):
        """Emit signal when frame thumbnail is clicked."""
        if event.button() == Qt.LeftButton:
            data = {
                'frame_number': self.frame_number,
                'diameter': self.pupil_diameter,
                'confidence': self.confidence
            }
            self.clicked.emit(self.frame_number, data)


class DetailViewDialog(QDialog):
    """Full-size detail view of a single frame with pupil overlay."""
    
    def __init__(self, frame_number: int, image_data: np.ndarray,
                 pupil_diameter: float, position: tuple = None,
                 confidence: float = 0.0, all_eyes: list = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"PLR Test - Frame {frame_number} Detail View")
        self.setGeometry(100, 100, 900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        num_eyes = len(all_eyes) if all_eyes else (1 if position else 0)
        header = QLabel(f"Frame {frame_number} | Eyes detected: {num_eyes} | "
                       f"Primary Ø: {pupil_diameter * MM_PER_PIXEL:.2f}mm | Confidence: {confidence:.2f}")
        header.setStyleSheet("font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(header)
        
        # Display image with pupil overlay for ALL eyes
        self.image_label = QLabel()
        self.draw_pupil_overlay(image_data, pupil_diameter, position, all_eyes)
        layout.addWidget(self.image_label)
        
        # Info panel
        info_text = f"\n        Frame Number: {frame_number}\n"
        if all_eyes:
            for i, eye in enumerate(all_eyes):
                side = "L" if i == 0 else "R"
                ex, ey = eye.get('position', (0, 0))
                ed = eye.get('diameter_px', 0)
                ec = eye.get('confidence', 0)
                info_text += f"        Eye {side}: ({ex:.0f}, {ey:.0f}) Ø {ed * MM_PER_PIXEL:.2f}mm  Conf: {ec:.2f}\n"
        else:
            info_text += f"        Position: {position if position else 'N/A'}\n"
            info_text += f"        Pupil Diameter: {pupil_diameter * MM_PER_PIXEL:.2f} mm\n"
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def draw_pupil_overlay(self, image: np.ndarray, diameter: float,
                           position: tuple, all_eyes: list = None):
        """Draw pupil circles for all detected eyes on image."""
        display_image = image.copy()
        h, w = display_image.shape[:2]

        # Build list of eyes to draw
        eyes_to_draw = []
        if all_eyes:
            for eye in all_eyes:
                pos = eye.get('position')
                diam = eye.get('diameter_px', 0)
                if pos and len(pos) >= 2 and not np.isnan(pos[0]) and not np.isnan(pos[1]):
                    eyes_to_draw.append((pos, diam))
        elif position and len(position) >= 2 and not np.isnan(position[0]) and not np.isnan(position[1]):
            eyes_to_draw.append((position, diameter))

        # Color per eye: green for left, blue for right
        colors = [(0, 255, 0), (255, 180, 0)]  # Green, Light Blue (BGR)
        labels = ["L", "R"]

        for idx, (pos, diam) in enumerate(eyes_to_draw):
            center_x = max(0, min(int(pos[0]), w - 1))
            center_y = max(0, min(int(pos[1]), h - 1))
            radius = int(diam / 2)
            color = colors[idx % len(colors)]

            # Draw pupil circle
            cv2.circle(display_image, (center_x, center_y), radius, color, 2)

            # Draw diameter line
            cv2.line(display_image, (center_x - radius, center_y),
                    (center_x + radius, center_y), color, 3)

            # Draw crosshair
            cs = 30
            cv2.line(display_image, (center_x - cs, center_y),
                    (center_x + cs, center_y), (0, 255, 255), 2)
            cv2.line(display_image, (center_x, center_y - cs),
                    (center_x, center_y + cs), (0, 255, 255), 2)

            # Text label with eye side and diameter
            side = labels[idx] if idx < len(labels) else str(idx)
            label = f"{side} Ø{diam * MM_PER_PIXEL:.1f}mm"
            cv2.putText(display_image, label,
                       (center_x - 40, center_y - radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Convert to QPixmap
        h, w = display_image.shape[:2]
        bytes_per_line = 3 * w
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)


class PLRTestScreen(QWidget):
    """Main PLR test analysis screen with frame grid and analysis options."""
    
    back_clicked = Signal()  # Signal emitted when back button is clicked
    plr_results_ready = Signal(dict)  # Signal with PLR metrics for RightArea display
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        self.current_video_path = None
        self.current_baseline_path = None
        self.current_frames = []
        self.current_analysis = None
    
    def init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Header
        title = QLabel("PLR (Pupil Light Reflex) Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; color: #000000;")
        layout.addWidget(title)
        
        # Control panel (back button only)
        control_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        control_layout.addStretch()
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        control_layout.addWidget(self.back_btn)
        
        layout.addLayout(control_layout)
        
        # Frame grid area with scroll
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        
        scroll_area.setWidget(self.grid_widget)
        layout.addWidget(scroll_area)
        
        # === COMPARISON PLOT (Recording vs Baseline) ===
        self.comparison_figure = Figure(figsize=(6.5, 2.4), dpi=80)
        self.comparison_figure.patch.set_facecolor("#f5f5f5")
        self.comparison_canvas = FigureCanvas(self.comparison_figure)
        self.comparison_canvas.setStyleSheet("background-color: #f5f5f5; border-radius: 8px;")
        self.comparison_canvas.setFixedHeight(200)
        self.comparison_canvas.setMaximumWidth(620)
        self.comparison_canvas.setVisible(False)
        layout.addWidget(self.comparison_canvas, 0, Qt.AlignLeft)
        
        # Status bar
        self.status_label = QLabel("Aufnahme aus der Videoliste im linken Bereich ausw\u00e4hlen um Analyse zu starten.")
        self.status_label.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 3px; color: #000000;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def load_video(self, file_path: str, baseline_path: str = None):
        """Load and analyze a video file with optional baseline comparison."""
        if not file_path:
            return
        
        self.current_video_path = file_path
        self.current_baseline_path = baseline_path
        self.run_analysis()
    
    def run_analysis(self):
        """Run pupil analysis on video using improved detection."""
        if not self.current_video_path:
            self.status_label.setText("Kein Video geladen")
            return
        
        from src.pupil_analyzer import PupilAnalyzer
        
        try:
            self.status_label.setText("Analysiere Video-Frames...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Use Haar Cascade + Hough Circle Detection pipeline
            analyzer = PupilAnalyzer()
            
            # Extract ALL frames from video for full analysis (frame_pool=1)
            cap = cv2.VideoCapture(self.current_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            analyzer.extract_frames_from_video(
                self.current_video_path,
                frame_pool=1,
                max_frames=None
            )
            
            # Pick 9 evenly spaced frames for grid display
            valid_frames = [pf for pf in analyzer.pupil_frames
                           if not np.isnan(pf.diameter_px) and not np.isnan(pf.position_x)]
            num_display = min(9, len(valid_frames))
            if num_display > 0:
                step = max(1, len(valid_frames) // num_display)
                display_indices = list(range(0, len(valid_frames), step))[:num_display]
                display_pupil_frames = [valid_frames[i] for i in display_indices]
            else:
                display_pupil_frames = []
            
            # Build display data for the 9 grid thumbnails
            key_frames_data = []
            frame_count = 0
            cap = cv2.VideoCapture(self.current_video_path)
            
            for pupil_frame in display_pupil_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pupil_frame.frame_number)
                ret, frame = cap.read()
                
                if ret:
                    diameter = pupil_frame.diameter_px
                    confidence = pupil_frame.confidence
                    position = (int(pupil_frame.position_x), int(pupil_frame.position_y))

                    # Build all_eyes list from analyzer.all_detections
                    all_eyes = []
                    frame_dets = analyzer.all_detections.get(pupil_frame.frame_number, [])
                    for det in frame_dets:
                        if det.confidence > 0 and not np.isnan(det.position_x):
                            all_eyes.append({
                                'position': (det.position_x, det.position_y),
                                'diameter_px': det.diameter_px,
                                'confidence': det.confidence
                            })
                    
                    key_frames_data.append({
                        'frame_number': pupil_frame.frame_number,
                        'image': frame,
                        'diameter': diameter,
                        'confidence': confidence,
                        'position': position,
                        'all_eyes': all_eyes
                    })
                
                # Progress bar
                progress = int((frame_count / max(1, len(display_pupil_frames))) * 100)
                self.progress_bar.setValue(progress)
                frame_count += 1
            
            # Read FPS before releasing capture
            fps = cap.get(cv2.CAP_PROP_FPS) or 20
            cap.release()
            
            self.current_frames = key_frames_data
            self.display_frame_grid()
            
            # === PLR BIOMARKER CALCULATION (using ALL analyzed frames) ===
            self.status_label.setText("Berechne PLR Biomarker...")
            self.progress_bar.setValue(90)
            
            # Diameter data from ALL frames for plot and metrics
            rec_times = np.array([pf.timestamp for pf in analyzer.pupil_frames])
            rec_diameters = np.array([pf.diameter_px for pf in analyzer.pupil_frames]) * MM_PER_PIXEL
            
            try:
                # Recording protocol: 0-1s IR baseline, 1-2s LED flash, 2-8s recovery
                # frame_pool=1, so use fps directly
                light_start_frame = int(1.0 * fps)
                light_end_frame = int(2.0 * fps)
                
                # Clamp to valid range
                n_frames = len(analyzer.pupil_frames)
                light_start_frame = min(light_start_frame, n_frames - 2)
                light_end_frame = min(light_end_frame, n_frames - 1)
                
                if light_start_frame > 0 and light_end_frame > light_start_frame:
                    metrics = analyzer.calculate_plr_metrics(
                        light_start_frame, light_end_frame
                    )
                    self._emit_results(metrics)
                else:
                    self.plr_results_ready.emit({'error': 'Not enough frames for PLR calculation.'})
                    
            except Exception as e:
                logger.warning(f"PLR metrics calculation failed: {e}")
                self.plr_results_ready.emit({'error': f'PLR calculation error: {str(e)}'})
            
            # === BASELINE COMPARISON PLOT (also analyze all frames) ===
            baseline_times = None
            baseline_diameters = None
            if self.current_baseline_path and self.current_baseline_path != self.current_video_path:
                try:
                    self.status_label.setText("Analysiere Baseline fuer Vergleich...")
                    baseline_analyzer = PupilAnalyzer()
                    baseline_analyzer.extract_frames_from_video(
                        self.current_baseline_path,
                        frame_pool=1,
                        max_frames=None
                    )
                    if baseline_analyzer.pupil_frames:
                        baseline_times = np.array([pf.timestamp for pf in baseline_analyzer.pupil_frames])
                        baseline_diameters = np.array([pf.diameter_px for pf in baseline_analyzer.pupil_frames]) * MM_PER_PIXEL
                except Exception as e:
                    logger.warning(f"Baseline analysis for comparison failed: {e}")
            
            self._draw_comparison_plot(rec_times, rec_diameters, baseline_times, baseline_diameters)
            
            self.status_label.setText("Analyse abgeschlossen")
            self.progress_bar.setVisible(False)
            logger.info(f"Analyzed {len(analyzer.pupil_frames)} frames, displayed {len(key_frames_data)}")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Fehler: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def display_frame_grid(self):
        """Display extracted frames in grid layout."""
        # Clear previous grid
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Add frame thumbnails
        col = 0
        row = 0
        cols_per_row = 3
        
        for frame_data in self.current_frames:
            frame_widget = PupilFrameWidget(
                frame_data['frame_number'],
                frame_data['image'],
                frame_data['diameter'],
                frame_data['confidence']
            )
            frame_widget.clicked.connect(self.show_detail_view)
            
            self.grid_layout.addWidget(frame_widget, row, col)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
    
    def show_detail_view(self, frame_number: int, frame_data: dict):
        """Show detail view dialog for clicked frame."""
        frame_info = next((f for f in self.current_frames 
                          if f['frame_number'] == frame_number), None)
        
        if frame_info:
            dialog = DetailViewDialog(
                frame_number,
                frame_info['image'],
                frame_info['diameter'],
                frame_info['position'],
                frame_info['confidence'],
                all_eyes=frame_info.get('all_eyes'),
                parent=self
            )
            dialog.exec()
    
    def _draw_comparison_plot(self, rec_times, rec_diameters,
                              baseline_times=None, baseline_diameters=None):
        """Draw comparison plot: recording vs baseline pupil diameter over time."""
        self.comparison_figure.clear()
        self.comparison_figure.patch.set_facecolor("#f5f5f5")
        ax = self.comparison_figure.add_subplot(111)
        ax.set_facecolor("#ffffff")
        ax.tick_params(colors="#333", labelsize=7)
        ax.grid(True, axis="both", linestyle="--", linewidth=0.4, color="#ddd", alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color("#ccc")

        # Light impulse shaded area (1-2s)
        ax.axvspan(1.0, 2.0, alpha=0.18, color="#ffaa00", zorder=0)
        ax.axvline(x=1.0, color="#e6a000", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.axvline(x=2.0, color="#e6a000", linewidth=0.8, linestyle="--", alpha=0.5)

        has_data = False

        # Plot baseline (gray) if available
        if baseline_times is not None and baseline_diameters is not None and len(baseline_times) > 0:
            # Interpolate NaN values
            nan_mask = np.isnan(baseline_diameters)
            valid = ~nan_mask
            if np.sum(valid) >= 2:
                bl_d = baseline_diameters.copy()
                bl_d[nan_mask] = np.interp(
                    np.where(nan_mask)[0], np.where(valid)[0], bl_d[valid]
                )
            else:
                bl_d = baseline_diameters

            # Smooth baseline
            if len(bl_d) >= 7:
                bl_smooth = savgol_filter(bl_d, window_length=7, polyorder=2)
            else:
                bl_smooth = bl_d

            ax.plot(baseline_times, bl_smooth, color="#888888", linewidth=1.5,
                    label="Baseline", alpha=0.7, zorder=2)
            has_data = True

        # Plot current recording (orange)
        if rec_times is not None and rec_diameters is not None and len(rec_times) > 0:
            # Interpolate NaN values
            nan_mask = np.isnan(rec_diameters)
            valid = ~nan_mask
            if np.sum(valid) >= 2:
                rec_d = rec_diameters.copy()
                rec_d[nan_mask] = np.interp(
                    np.where(nan_mask)[0], np.where(valid)[0], rec_d[valid]
                )
            else:
                rec_d = rec_diameters

            # Smooth recording
            if len(rec_d) >= 7:
                rec_smooth = savgol_filter(rec_d, window_length=7, polyorder=2)
            else:
                rec_smooth = rec_d

            ax.plot(rec_times, rec_smooth, color="#e65100", linewidth=2.0,
                    label="Aufnahme", zorder=3)
            has_data = True

        if has_data:
            ax.set_xlabel("Time (s)", color="#e65100", fontsize=9, fontweight="bold")
            ax.set_ylabel("Pupil Diameter (mm)", color="#e65100", fontsize=9,
                          fontweight="bold", rotation=90)
            ax.set_title("Aufnahme vs. Baseline", color="#333", fontsize=11, fontweight="bold")

            # "Lichtimpuls" label
            y_lim = ax.get_ylim()
            y_top = y_lim[1] - (y_lim[1] - y_lim[0]) * 0.05
            ax.text(1.5, y_top, "Lichtimpuls", ha="center", va="top",
                    fontsize=7, fontweight="bold", color="#333",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffaa00",
                              edgecolor="none", alpha=0.85))

            ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
            self.comparison_figure.subplots_adjust(left=0.10, right=0.97, top=0.82, bottom=0.16)
            self.comparison_canvas.setVisible(True)
        else:
            self.comparison_canvas.setVisible(False)

        self.comparison_canvas.draw()

    def _emit_results(self, metrics):
        """Package PLR metrics as dict and emit signal for RightArea display."""
        results = {
            'baseline_mean': metrics.baseline_mean,
            'baseline_max': metrics.baseline_max,
            'baseline_min': metrics.baseline_min,
            'latency': metrics.latency,
            'latency_frame_idx': metrics.latency_frame_idx,
            'peak_constriction_velocity': metrics.peak_constriction_velocity,
            'peak_constriction_velocity_frame': metrics.peak_constriction_velocity_frame,
            'average_constriction_velocity': metrics.average_constriction_velocity,
            'minimum_diameter': metrics.minimum_diameter,
            'minimum_diameter_frame': metrics.minimum_diameter_frame,
            'amplitude': metrics.amplitude,
            'peak_dilation_velocity': metrics.peak_dilation_velocity,
            'peak_dilation_velocity_frame': metrics.peak_dilation_velocity_frame,
            'average_dilation_velocity': metrics.average_dilation_velocity,
            'prt_50': metrics.prt_50,
            'prt_63': metrics.prt_63,
            'prt_75': metrics.prt_75,
        }
        self.plr_results_ready.emit(results)
