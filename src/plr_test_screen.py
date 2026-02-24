"""
PLR (Pupil Light Reflex) Test Analysis Screen.
Provides visual testing interface for pupil detection on video frames.
"""

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QDialog, QFileDialog,
    QProgressBar, QSpinBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QThread, Signal
from typing import List, Dict, Optional
import logging

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
            info_text += f"\nØ {pupil_diameter:.1f}px"
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
                       f"Primary Ø: {pupil_diameter:.2f}px | Confidence: {confidence:.2f}")
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
                info_text += f"        Eye {side}: ({ex:.0f}, {ey:.0f}) Ø {ed:.1f}px  Conf: {ec:.2f}\n"
        else:
            info_text += f"        Position: {position if position else 'N/A'}\n"
            info_text += f"        Pupil Diameter: {pupil_diameter:.2f} pixels\n"
        
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
            label = f"{side} Ø{diam:.0f}px"
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
        self.current_video_path = None
        self.current_frames = []
        self.current_analysis = None
    
    def init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Header
        title = QLabel("PLR (Pupil Light Reflex) Test Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Video")
        self.load_btn.clicked.connect(self.load_video)
        control_layout.addWidget(self.load_btn)
        
        control_layout.addWidget(QLabel("Key Frame Count:"))
        self.frame_count_spin = QSpinBox()
        self.frame_count_spin.setMinimum(3)
        self.frame_count_spin.setMaximum(12)
        self.frame_count_spin.setValue(9)
        control_layout.addWidget(self.frame_count_spin)
        
        self.analyze_btn = QPushButton("Analyze & Preview")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.run_analysis)
        control_layout.addWidget(self.analyze_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        # Add spacer and back button
        control_layout.addSpacing(20)
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
        
        # Status bar
        self.status_label = QLabel("Ready. Load a video to start.")
        self.status_label.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 3px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def load_video(self):
        """Open file dialog to load video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        
        if file_path:
            self.current_video_path = file_path
            self.analyze_btn.setEnabled(True)
            self.status_label.setText(f"Loaded: {file_path.split('/')[-1]}")
    
    def run_analysis(self):
        """Run pupil analysis on video using improved detection."""
        if not self.current_video_path:
            self.status_label.setText("❌ No video loaded")
            return
        
        from src.pupil_analyzer import PupilAnalyzer
        
        try:
            self.status_label.setText("🔄 Analyzing video frames...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Use Haar Cascade + Hough Circle Detection pipeline
            analyzer = PupilAnalyzer()
            
            # Extract frames from video (process all frames)
            cap = cv2.VideoCapture(self.current_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Determine how many frames to display (every nth frame for performance)
            num_display_frames = self.frame_count_spin.value()
            frame_pool = max(1, total_frames // num_display_frames)
            
            # Analyze all frames but only display key frames
            analyzer.extract_frames_from_video(
                self.current_video_path,
                frame_pool=frame_pool,
                max_frames=None
            )
            
            # Build display data from analyzed frames
            key_frames_data = []
            frame_count = 0
            cap = cv2.VideoCapture(self.current_video_path)
            
            for pupil_frame in analyzer.pupil_frames:
                # Set frame position and read
                cap.set(cv2.CAP_PROP_POS_FRAMES, pupil_frame.frame_number)
                ret, frame = cap.read()
                
                if ret:
                    # Check for valid detection BEFORE converting to int
                    diameter = pupil_frame.diameter_px
                    confidence = pupil_frame.confidence
                    position_x = pupil_frame.position_x
                    position_y = pupil_frame.position_y
                    
                    # Skip frames with NaN values (undetected pupils)
                    if np.isnan(diameter) or np.isnan(position_x) or np.isnan(position_y):
                        logger.warning(f"Skipping frame {pupil_frame.frame_number}: No pupil detected (NaN values)")
                        continue
                    
                    # Now safe to convert to int
                    position = (int(position_x), int(position_y))

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
                progress = int((frame_count / len(analyzer.pupil_frames)) * 100)
                self.progress_bar.setValue(progress)
                frame_count += 1
            
            cap.release()
            
            self.current_frames = key_frames_data
            self.display_frame_grid()
            
            self.status_label.setText(f"✅ Analysis complete - {len(key_frames_data)} frames analyzed")
            self.progress_bar.setVisible(False)
            logger.info(f"Analyzed {len(analyzer.pupil_frames)} frames, displayed {len(key_frames_data)}")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"❌ Error: {str(e)}")
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
