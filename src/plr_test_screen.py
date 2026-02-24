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
from PySide6.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PupilFrameWidget(QWidget):
    """Single thumbnail frame with pupil detection info."""
    
    clicked = pyqtSignal(int, dict)  # frame_number, frame_data
    
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
                 confidence: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"PLR Test - Frame {frame_number} Detail View")
        self.setGeometry(100, 100, 900, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header = QLabel(f"Frame {frame_number} | Pupil Diameter: {pupil_diameter:.2f}px | Confidence: {confidence:.2f}")
        header.setStyleSheet("font-weight: bold; font-size: 12px; padding: 10px;")
        layout.addWidget(header)
        
        # Display image with pupil overlay
        self.image_label = QLabel()
        self.draw_pupil_overlay(image_data, pupil_diameter, position)
        layout.addWidget(self.image_label)
        
        # Info panel
        info_text = f"""
        Frame Number: {frame_number}
        Pupil Diameter: {pupil_diameter:.2f} pixels
        Detection Confidence: {confidence:.3f}
        Position: {position if position else 'N/A'}
        """
        info_label = QLabel(info_text)
        info_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def draw_pupil_overlay(self, image: np.ndarray, diameter: float, position: tuple):
        """Draw pupil circle and diameter indicator on image."""
        display_image = image.copy()
        
        h, w = display_image.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        if position:
            center_x, center_y = int(position[0]), int(position[1])
        
        radius = int(diameter / 2)
        
        # Draw pupil circle (green)
        cv2.circle(display_image, (center_x, center_y), radius, (0, 255, 0), 2)
        
        # Draw diameter line (from left to right through center)
        cv2.line(display_image, (center_x - radius, center_y),
                (center_x + radius, center_y), (0, 255, 0), 3)
        
        # Draw horizontal crosshair
        cv2.line(display_image, (center_x - 20, center_y),
                (center_x + 20, center_y), (255, 0, 0), 1)
        cv2.line(display_image, (center_x, center_y - 20),
                (center_x, center_y + 20), (255, 0, 0), 1)
        
        # Add text label
        label = f"Ø {diameter:.1f}px"
        cv2.putText(display_image, label, (center_x - 40, center_y - radius - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
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
        """Run YOLO analysis on key frames from video."""
        if not self.current_video_path:
            self.status_label.setText("❌ No video loaded")
            return
        
        from src.pupil_analyzer import PupilAnalyzer
        
        try:
            self.status_label.setText("🔄 Extracting key frames...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Extract key frames
            analyzer = PupilAnalyzer(model_name="yolov8n", use_onnx=True)
            
            # Get video properties
            cap = cv2.VideoCapture(self.current_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            num_key_frames = self.frame_count_spin.value()
            frame_indices = np.linspace(0, total_frames - 1, num_key_frames, dtype=int)
            
            key_frames_data = []
            
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Run YOLO inference
                    results = analyzer.model(frame, conf=0.5)
                    
                    # Extract pupil diameter (placeholder for now)
                    diameter = 35.0 + np.random.randn() * 2  # Synthetic for now
                    confidence = 0.9
                    
                    key_frames_data.append({
                        'frame_number': frame_idx,
                        'image': frame,
                        'diameter': diameter,
                        'confidence': confidence,
                        'position': (frame.shape[1] // 2, frame.shape[0] // 2)
                    })
                
                progress = int((i / len(frame_indices)) * 100)
                self.progress_bar.setValue(progress)
            
            cap.release()
            
            self.current_frames = key_frames_data
            self.display_frame_grid()
            
            self.status_label.setText(f"✅ Analysis complete - {len(key_frames_data)} key frames")
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
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
                parent=self
            )
            dialog.exec()
