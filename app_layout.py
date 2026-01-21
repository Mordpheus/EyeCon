from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QMessageBox, QDialog, QComboBox, QStackedWidget, QListWidget, QListWidgetItem, QSlider
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPaintEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from patient_widgets import DeleteConfirmDialog, EditPatientDialog, PatientListWidget, CreatePatientDialog
from data_manager import PatientDataManager
from src.importer import TBIHeadsetImporter


# -------------------------------------------------
# LEFT AREA - Navigation Sidebar with Icons
# -------------------------------------------------
class LeftArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
        self.setAttribute(Qt.WA_StyledBackground, True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)

        # === UPPER HALF (50% height): Navigation Buttons ===
        upper_container = QWidget()
        upper_layout = QVBoxLayout(upper_container)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(0)  # No fixed spacing - use stretch for dynamic sizing

        upper_layout.addStretch(1)  # Initial space at top

        # 1. Patients Button
        patients_layout = QHBoxLayout()
        patients_icon = QLabel("👥")
        patients_icon.setStyleSheet("font-size: 28px;")
        patients_btn = QPushButton("Patients")
        patients_btn.setMinimumHeight(50)
        patients_layout.addWidget(patients_icon)
        patients_layout.addWidget(patients_btn, 1)
        patients_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(patients_layout)

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

        # 2. Import Data Button
        import_layout = QHBoxLayout()
        import_icon = QLabel("📥")
        import_icon.setStyleSheet("font-size: 28px;")
        self.btn_import = QPushButton("Import Data")
        self.btn_import.setMinimumHeight(50)
        import_layout.addWidget(import_icon)
        import_layout.addWidget(self.btn_import, 1)
        import_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(import_layout)

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

        # 3. Settings Button
        settings_layout = QHBoxLayout()
        settings_icon = QLabel("⚙️")
        settings_icon.setStyleSheet("font-size: 28px;")
        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setMinimumHeight(50)
        settings_layout.addWidget(settings_icon)
        settings_layout.addWidget(self.btn_settings, 1)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(settings_layout)

        upper_layout.addStretch(2)  # DYNAMIC SPACING: Scales with window height

        # 4. Help Button
        help_layout = QHBoxLayout()
        help_icon = QLabel("❓")
        help_icon.setStyleSheet("font-size: 28px;")
        self.btn_help = QPushButton("Help")
        self.btn_help.setMinimumHeight(50)
        help_layout.addWidget(help_icon)
        help_layout.addWidget(self.btn_help, 1)
        help_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(help_layout)

        upper_layout.addStretch(1)  # Final space at bottom
        main_layout.addWidget(upper_container, 1)  # UPPER HALF: 50% of sidebar height

        # === LOWER HALF (50% height): Patient Info ===
        lower_container = QWidget()
        lower_layout = QVBoxLayout(lower_container)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(10)

        # Patient Name Display (non-clickable) - STARTS AT 50% HEIGHT
        self.patient_name_display = QPushButton()
        self.patient_name_display.setText("No patient selected")
        self.patient_name_display.setEnabled(False)
        self.patient_name_display.setMinimumHeight(55)
        self.patient_name_display.setStyleSheet(
            "QPushButton { "
            "background-color: #e7ecf8; "
            "color: #333333; "
            "border: 1px solid #cccccc; "
            "border-radius: 4px; "
            "padding: 10px; "
            "font-weight: bold; "
            "text-align: left; "
            "font-size: 12px; "
            "}"
        )
        lower_layout.addWidget(self.patient_name_display)

        # === Recordings Section: Label + Dropdown ===
        # Displays all recordings for currently selected patient
        # User can select a recording from the dropdown to analyze it
        
        # Recordings label - descriptive text
        self.recordings_label = QLabel("Recordings:")
        self.recordings_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        lower_layout.addWidget(self.recordings_label)

        # === QComboBox: Recordings Dropdown ===
        # Displays list of recordings for selected patient
        # Initially empty - populated when patient is selected
        # User selection triggers analysis screen update (Iteration 4.2)
        self.recordings_dropdown = QComboBox()
        self.recordings_dropdown.setMinimumHeight(35)
        self.recordings_dropdown.setStyleSheet(
            "QComboBox { "
            "background-color: #ffffff; "
            "color: #333333; "
            "border: 1px solid #cccccc; "
            "border-radius: 3px; "
            "padding: 5px; "
            "font-size: 11px; "
            "} "
            "QComboBox::drop-down { "
            "border: none; "
            "} "
            "QComboBox QAbstractItemView { "
            "background-color: #ffffff; "
            "color: #333333; "
            "selection-background-color: #d0dff0; "
            "}"
        )
        # Add placeholder item when no recordings available
        self.recordings_dropdown.addItem("-- Select a recording --")
        self.recordings_dropdown.setEnabled(False)  # Disabled until patient selected
        lower_layout.addWidget(self.recordings_dropdown)

        lower_layout.addStretch()  # LOWER HALF: Fill remaining space
        main_layout.addWidget(lower_container, 1)  # LOWER HALF: 50% of sidebar height

        self.setFixedWidth(220)

    def set_selected_patient(self, patient_name: str, patient_id: int = None) -> None:
        """
        Update patient name display and load recordings for selected patient.
        
        Parameters:
            patient_name (str): Full name of the patient (first + last)
            patient_id (int): Database ID of the selected patient
                Passed from CenterArea to load recordings
        """
        # Update patient name display with highlighted styling
        self.patient_name_display.setText(patient_name)
        self.patient_name_display.setStyleSheet(
            "QPushButton { "
            "background-color: #d0dff0; "
            "color: #1a1a1a; "
            "border: 2px solid #5f8fdc; "
            "border-radius: 4px; "
            "padding: 8px; "
            "font-weight: bold; "
            "text-align: left; "
            "}"
        )
        
        # Load recordings for this patient into the dropdown
        if patient_id is not None:
            self._load_recordings_for_patient(patient_id)
    
    def _load_recordings_for_patient(self, patient_id: int) -> None:
        """
        Signal handler placeholder for loading recordings.
        
        This method will be called when patient is selected.
        Actual recording loading happens in AppLayout._on_patient_selected
        which has access to CenterArea.manager
        
        Parameters:
            patient_id (int): Database ID of the patient
        """
        # Placeholder - implementation in AppLayout
        pass
    
    def update_recordings_dropdown(self, recordings: list) -> None:
        """
        Update recordings dropdown with fetched recording data.
        
        Called from AppLayout after fetching recordings from database.
        Each recording item is formatted as: "Recording ID - Date"
        
        Parameters:
            recordings (list): List of recording dictionaries from database
                Each dict contains: {id, date, baseline}
        """
        # Clear all existing items from dropdown
        self.recordings_dropdown.clear()
        
        # If no recordings, show placeholder and disable
        if not recordings:
            self.recordings_dropdown.addItem("-- No recordings --")
            self.recordings_dropdown.setEnabled(False)
            return
        
        # Add each recording to dropdown with formatted display text
        for rec in recordings:
            # Extract recording ID and timestamp
            rec_id = rec.get("id", "Unknown")
            date_unix = rec.get("date", 0)
            
            # Extract filename from path (if rec_id is a file path)
            # E.g. "/data/user/0/com.example/recording.mp4" → "recording.mp4"
            # or "file:///.../recording.mp4" → "recording.mp4"
            if "/" in str(rec_id):
                display_name = str(rec_id).split("/")[-1]  # Get last part after /
            elif "\\" in str(rec_id):
                display_name = str(rec_id).split("\\")[-1]  # Get last part after \
            else:
                display_name = str(rec_id)
            
            # Convert Unix timestamp to human-readable format
            # Handle invalid timestamps (0, None, negative values)
            if date_unix and date_unix > 0:
                try:
                    date_str = datetime.fromtimestamp(date_unix).strftime("%Y-%m-%d %H:%M")
                except (OSError, ValueError, OverflowError):
                    # Timestamp is invalid on this system
                    date_str = ""  # Empty = no date display
            else:
                date_str = ""  # Empty = no date display
            
            # Create display text
            if date_str:
                display_text = f"{display_name} - {date_str}"
            else:
                display_text = display_name  # Just show filename if no date
            
            # Add to dropdown with complete recording object as user data
            self.recordings_dropdown.addItem(display_text, rec)
        
        # Enable dropdown now that recordings are available
        self.recordings_dropdown.setEnabled(True)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#9bbcf0"))
        grad.setColorAt(1.0, QColor("#5f8fdc"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# RECORDING PLAYER SCREEN - Video playback for recordings
# -------------------------------------------------
class RecordingPlayerScreen(QWidget):
    """Screen to display and play a recording video."""
    
    back_clicked = Signal()  # Signal emitted when back button clicked
    
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #1a1a1a;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # === Back Button ===
        back_btn_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Patients")
        self.back_btn.setMaximumWidth(150)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        back_btn_layout.addWidget(self.back_btn)
        back_btn_layout.addStretch()
        layout.addLayout(back_btn_layout)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        
        # === Recording Info ===
        self.recording_info = QLabel("No recording selected")
        self.recording_info.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.recording_info)
        
        # === Video Player with QMediaPlayer ===
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_widget.setMinimumHeight(400)
        layout.addWidget(self.video_widget, 1)
        
        # === Media Player ===
        self.media_player = QMediaPlayer(self)
        self.media_player.setVideoOutput(self.video_widget)
        
        # === VIDEO TIMELINE ===
        timeline_layout = QHBoxLayout()
        timeline_layout.setContentsMargins(0, 5, 0, 5)
        timeline_layout.setSpacing(10)
        
        # Time display (left side)
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white; font-size: 11px; min-width: 80px;")
        timeline_layout.addWidget(self.time_label)
        
        # Timeline slider with current position indicator
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #333;
            }
            QSlider::handle:horizontal {
                background: #ff6600;
                width: 12px;
                margin: -2px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #ff8833;
            }
        """)
        self.timeline_slider.setMaximum(1000)  # Use 0-1000 scale
        self.timeline_slider.sliderMoved.connect(self.on_timeline_moved)
        self.timeline_slider.setCursor(Qt.PointingHandCursor)
        timeline_layout.addWidget(self.timeline_slider, 1)
        
        # Duration display (right side)
        self.duration_label = QLabel("--:--")
        self.duration_label.setStyleSheet("color: white; font-size: 11px; min-width: 40px; text-align: right;")
        timeline_layout.addWidget(self.duration_label)
        
        layout.addLayout(timeline_layout)
        
        # Connect media player signals for timeline updates
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        
        # === Playback Controls ===
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.pause_btn = QPushButton("⏸ Pause")
        self.stop_btn = QPushButton("⏹ Stop")
        
        self.play_btn.clicked.connect(self.media_player.play)
        self.pause_btn.clicked.connect(self.media_player.pause)
        self.stop_btn.clicked.connect(self.media_player.stop)
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # === THREE PLOT AREA (Eye Tracking Visualization) ===
        plots_container = QWidget()
        plots_layout = QHBoxLayout(plots_container)
        plots_layout.setContentsMargins(0, 0, 0, 0)
        plots_layout.setSpacing(10)
        
        # Left: Baseline Graph
        self.baseline_plot_widget = QWidget()
        baseline_plot_layout = QVBoxLayout(self.baseline_plot_widget)
        baseline_plot_layout.setContentsMargins(0, 0, 0, 0)
        baseline_label = QLabel("Baseline Recording")
        baseline_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        baseline_plot_layout.addWidget(baseline_label)
        self.baseline_figure = Figure(figsize=(3, 2), dpi=80)
        self.baseline_canvas = FigureCanvas(self.baseline_figure)
        self.baseline_canvas.setStyleSheet("background-color: #1a1a1a;")
        baseline_plot_layout.addWidget(self.baseline_canvas)
        plots_layout.addWidget(self.baseline_plot_widget, 1)
        
        # Middle: Current Recording Graph (synchronized with video)
        self.current_plot_widget = QWidget()
        current_plot_layout = QVBoxLayout(self.current_plot_widget)
        current_plot_layout.setContentsMargins(0, 0, 0, 0)
        current_label = QLabel("Current Recording (Live)")
        current_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        current_plot_layout.addWidget(current_label)
        self.current_figure = Figure(figsize=(3, 2), dpi=80)
        self.current_canvas = FigureCanvas(self.current_figure)
        self.current_canvas.setStyleSheet("background-color: #1a1a1a;")
        current_plot_layout.addWidget(self.current_canvas)
        plots_layout.addWidget(self.current_plot_widget, 1)
        
        # Right: Recording Selection (placeholder)
        self.recording_select_widget = QWidget()
        recording_select_layout = QVBoxLayout(self.recording_select_widget)
        recording_select_layout.setContentsMargins(0, 0, 0, 0)
        select_label = QLabel("Recordings & Baselines")
        select_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        recording_select_layout.addWidget(select_label)
        self.recording_list = QListWidget()
        self.recording_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
            }
        """)
        recording_select_layout.addWidget(self.recording_list)
        plots_layout.addWidget(self.recording_select_widget, 1)
        
        layout.addWidget(plots_container, 0)
        layout.setStretchFactor(plots_container, 0)
        
        # === Recording Details ===
        self.details_label = QLabel()
        self.details_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label)
        
        self.current_recording = None
    
    def set_recording(self, recording: dict) -> None:
        """
        Display a recording in the player.
        
        Args:
            recording: Dictionary with keys {id, date, baseline, patientId}
        """
        self.current_recording = recording
        
        # Update info display
        rec_id = recording.get('id', 'Unknown')
        rec_date = recording.get('date', 0)
        is_baseline = recording.get('baseline', 0)
        
        # Extract filename from path if needed
        if "/" in str(rec_id):
            display_name = str(rec_id).split("/")[-1]
        elif "\\" in str(rec_id):
            display_name = str(rec_id).split("\\")[-1]
        else:
            display_name = str(rec_id)
        
        # Format date
        if rec_date and rec_date > 0:
            try:
                date_str = datetime.fromtimestamp(rec_date).strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = ""  # Empty if invalid
        else:
            date_str = ""  # Empty if no timestamp
        
        # Update labels
        if date_str:
            self.recording_info.setText(f"Recording: {display_name} - {date_str}")
        else:
            self.recording_info.setText(f"Recording: {display_name}")
        
        baseline_text = "✓ Baseline Recording" if is_baseline else "Normal Recording"
        if date_str:
            self.details_label.setText(f"{baseline_text}\nFile: {display_name}\nDate: {date_str}")
        else:
            self.details_label.setText(f"{baseline_text}\nFile: {display_name}\nDate: Not recorded")
        
        # Load video file
        # Note: Recording IDs are file paths from TBI_Headset database
        # Try to load the file if it exists
        try:
            video_path = str(rec_id)
            if Path(video_path).exists():
                media_url = QUrl.fromLocalFile(video_path)
                self.media_player.setSource(media_url)
                self.details_label.setText(f"{baseline_text}\nFile: {display_name}\nDate: {date_str if date_str else 'Not recorded'}\n✓ Video loaded successfully")
            else:
                self.details_label.setText(f"{baseline_text}\nFile: {display_name}\nDate: {date_str if date_str else 'Not recorded'}\n⚠ Video file not found at: {video_path}")
        except Exception as e:
            self.details_label.setText(f"{baseline_text}\nFile: {display_name}\nDate: {date_str if date_str else 'Not recorded'}\n⚠ Error loading video: {str(e)}")
        
        # === Populate Plots ===
        self._update_plots(recording)
    
    def _update_plots(self, recording: dict) -> None:
        """Update the three plot areas with current and baseline data."""
        
        # Clear previous plots
        self.baseline_figure.clear()
        self.current_figure.clear()
        self.recording_list.clear()
        
        # === Left Plot: Baseline Recording (if exists) ===
        baseline_ax = self.baseline_figure.add_subplot(111)
        baseline_ax.set_facecolor("#1a1a1a")
        baseline_ax.tick_params(colors='white')
        for spine in baseline_ax.spines.values():
            spine.set_color("#555")
        
        if recording.get('baseline'):
            # Plot baseline data (placeholder - would load actual eye-tracking data)
            baseline_ax.plot([0, 1, 2, 3], [100, 120, 110, 115], color='blue', linewidth=1.5, label='Baseline')
            baseline_ax.set_title("Baseline Data", color='white', fontsize=10)
            baseline_ax.set_xlabel("Time (s)", color='white', fontsize=8)
            baseline_ax.set_ylabel("Position (px)", color='white', fontsize=8)
            baseline_ax.legend(facecolor='#2a2a2a', edgecolor='white', fontsize=8)
        else:
            baseline_ax.text(0.5, 0.5, 'No Baseline Available', ha='center', va='center',
                           transform=baseline_ax.transAxes, color='#666', fontsize=10)
            baseline_ax.set_xticks([])
            baseline_ax.set_yticks([])
        
        self.baseline_figure.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)
        self.baseline_canvas.draw()
        
        # === Middle Plot: Current Recording (synchronized with video) ===
        current_ax = self.current_figure.add_subplot(111)
        current_ax.set_facecolor("#1a1a1a")
        current_ax.tick_params(colors='white')
        for spine in current_ax.spines.values():
            spine.set_color("#555")
        
        # Plot current recording data (placeholder - would update with video playback)
        current_ax.plot([0, 1, 2, 3], [110, 115, 125, 120], color='green', linewidth=1.5, label='Current Recording')
        current_ax.set_title(f"Current Recording", color='white', fontsize=10)
        current_ax.set_xlabel("Time (s)", color='white', fontsize=8)
        current_ax.set_ylabel("Position (px)", color='white', fontsize=8)
        current_ax.legend(facecolor='#2a2a2a', edgecolor='white', fontsize=8)
        
        self.current_figure.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15)
        self.current_canvas.draw()
        
        # === Right Widget: Recording Selection List ===
        # Populate with all recordings for this patient (from parent CenterArea)
        # For now, add placeholder entries
        recordings = [
            f"Recording {i+1} {'(Baseline)' if i == 0 else ''}"
            for i in range(3)
        ]
        
        for rec in recordings:
            item = QListWidgetItem(rec)
            item.setForeground(QColor('white'))
            if '(Baseline)' in rec:
                item.setBackground(QColor('#4a4a4a'))
            self.recording_list.addItem(item)
    
    def on_position_changed(self, position_ms: int) -> None:
        """Update timeline slider and time label when video position changes."""
        if self.media_player.duration() > 0:
            # Update slider (0-1000 scale)
            slider_value = int((position_ms / self.media_player.duration()) * 1000)
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setValue(slider_value)
            self.timeline_slider.blockSignals(False)
            
            # Update time display (MM:SS / MM:SS)
            current_secs = position_ms // 1000
            total_secs = self.media_player.duration() // 1000
            current_min, current_sec = divmod(current_secs, 60)
            total_min, total_sec = divmod(total_secs, 60)
            
            self.time_label.setText(f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}")
    
    def on_duration_changed(self, duration_ms: int) -> None:
        """Update duration label when video duration is loaded."""
        if duration_ms > 0:
            total_secs = duration_ms // 1000
            total_min, total_sec = divmod(total_secs, 60)
            self.duration_label.setText(f"{total_min:02d}:{total_sec:02d}")
        else:
            self.duration_label.setText("--:--")
    
    def on_timeline_moved(self, value: int) -> None:
        """Handle user scrubbing on timeline slider."""
        if self.media_player.duration() > 0:
            # Convert slider position (0-1000) to milliseconds
            position_ms = int((value / 1000) * self.media_player.duration())
            self.media_player.setPosition(position_ms)


# -------------------------------------------------
# HELP SCREEN
# -------------------------------------------------
class HelpScreen(QWidget):
    """Help screen with Lorem Ipsum placeholder content."""
    
    back_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Help & Documentation")
        title.setStyleSheet("color: black; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)
        
        # Content (Lorem Ipsum placeholder)
        content = QLabel(
            "Lorem Ipsum\n\n"
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
            "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
            "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.\n\n"
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat "
            "nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia "
            "deserunt mollit anim id est laborum.\n\n"
            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque "
            "laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi "
            "architecto beatae vitae dicta sunt explicabo.\n\n"
            "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia "
            "consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt."
        )
        content.setStyleSheet("color: black; font-size: 12px;")
        content.setWordWrap(True)
        layout.addWidget(content, 1)
        
        # Back button
        back_btn = QPushButton("← Back to Patients")
        back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(back_btn)


# -------------------------------------------------
# SETTINGS SCREEN
# -------------------------------------------------
class SettingsScreen(QWidget):
    """Settings screen with USB port configuration."""
    
    back_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Settings")
        title.setStyleSheet("color: black; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)
        
        # USB Port Selection Section
        usb_label = QLabel("Camera USB Port")
        usb_label.setStyleSheet("color: black; font-weight: bold; font-size: 13px;")
        layout.addWidget(usb_label)
        
        # USB Port Dropdown + Camera Preview Layout
        usb_container_layout = QHBoxLayout()
        usb_container_layout.setSpacing(20)
        
        # Left side: Dropdown and Scan button
        usb_layout = QVBoxLayout()
        usb_layout.setSpacing(10)
        
        port_row = QHBoxLayout()
        port_label = QLabel("Select Port:")
        port_label.setStyleSheet("color: black;")
        port_row.addWidget(port_label)
        
        self.port_dropdown = QComboBox()
        self.port_dropdown.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: black;
                border: 1px solid #999;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #e0e0e0;
            }
        """)
        self.port_dropdown.addItem("-- Select USB Port --", None)
        self.port_dropdown.addItem("COM1", "COM1")
        self.port_dropdown.addItem("COM2", "COM2")
        self.port_dropdown.addItem("COM3", "COM3")
        self.port_dropdown.addItem("COM4", "COM4")
        self.port_dropdown.currentIndexChanged.connect(self._on_port_changed)
        port_row.addWidget(self.port_dropdown)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Scan Ports")
        refresh_btn.setMaximumWidth(120)
        refresh_btn.clicked.connect(self._on_refresh_ports)
        port_row.addWidget(refresh_btn)
        
        usb_layout.addLayout(port_row)
        usb_container_layout.addLayout(usb_layout, 1)
        
        # Right side: Camera Preview (150x150)
        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(5)
        
        preview_label = QLabel("Camera Preview")
        preview_label.setStyleSheet("color: black; font-size: 11px; font-weight: bold;")
        preview_layout.addWidget(preview_label)
        
        self.camera_preview = QLabel()
        self.camera_preview.setFixedSize(150, 150)
        self.camera_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 5px;
            }
        """)
        self.camera_preview.setAlignment(Qt.AlignCenter)
        self._show_no_signal()
        preview_layout.addWidget(self.camera_preview)
        preview_layout.addStretch()
        
        usb_container_layout.addLayout(preview_layout)
        
        layout.addLayout(usb_container_layout)
        
        # Spacer
        layout.addSpacing(20)
        
        # Info text
        info = QLabel(
            "Camera Configuration:\n\n"
            "Select the USB port where your eye-tracking camera is connected. "
            "Use the 'Scan Ports' button to auto-detect available devices.\n\n"
            "More camera settings will be available in future versions."
        )
        info.setStyleSheet("color: #666666; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Spacer
        layout.addStretch()
        
        # Back button
        back_btn = QPushButton("← Back to Patients")
        back_btn.clicked.connect(self.back_clicked.emit)
        layout.addWidget(back_btn)
    
    def _show_no_signal(self):
        """Show 'No Signal' message with disconnected icon in preview."""
        self.camera_preview.setText("⊘\n\nKein Signal")
        self.camera_preview.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 5px;
                color: #999;
                font-size: 32px;
                font-weight: bold;
            }
        """)
    
    def _show_connected(self, port: str):
        """Show connected status (placeholder for live camera feed)."""
        self.camera_preview.setText(f"✓\n\n{port}\nverbunden")
        self.camera_preview.setStyleSheet("""
            QLabel {
                background-color: #e8f5e9;
                border: 2px solid #4caf50;
                border-radius: 5px;
                color: #2e7d32;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        # TODO: Hier würde OpenCV Camera-Feed angezeigt
    
    def _on_port_changed(self, index: int):
        """Handle USB port selection change."""
        if index <= 0:
            self._show_no_signal()
            return
        
        port = self.port_dropdown.currentData()
        if port:
            # Placeholder: Versuche Camera zu öffnen (später mit OpenCV)
            self._show_connected(port)
        else:
            self._show_no_signal()
    
    def _on_refresh_ports(self):
        """Refresh available COM ports (placeholder)."""
        # TODO: Implement actual COM port detection using pyserial
        pass


# -------------------------------------------------
# CENTER AREA - Main content
# -------------------------------------------------
class CenterArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Data manager and selection state
        self.manager = PatientDataManager(Path("data/eyecon.db"))
        self.selected_patient_id = None
        
        # Initialize TBI_Headset importer for ZIP imports
        self.importer = TBIHeadsetImporter(self.manager)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Button bar: Create | Edit | Delete ---
        # Buttons inherit global stylesheet from Main.py
        button_row = QHBoxLayout()
        self.btn_create = QPushButton("Create patient")
        self.btn_edit = QPushButton("Edit patient")
        self.btn_delete = QPushButton("Delete patient")

        button_row.addWidget(self.btn_create)
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_delete)
        button_row.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addLayout(button_row)

        # === STACKED WIDGET: Switch between different screens ===
        self.stacked_widget = QStackedWidget()
        
        # Screen 0: Patient List
        self.patient_list = PatientListWidget()
        self.stacked_widget.addWidget(self.patient_list)
        
        # Screen 1: Recording Player
        self.recording_player = RecordingPlayerScreen()
        self.stacked_widget.addWidget(self.recording_player)
        
        # Screen 2: Help
        self.help_screen = HelpScreen()
        self.stacked_widget.addWidget(self.help_screen)
        
        # Screen 3: Settings
        self.settings_screen = SettingsScreen()
        self.stacked_widget.addWidget(self.settings_screen)
        
        # Show patient list by default
        self.stacked_widget.setCurrentIndex(0)
        
        layout.addWidget(self.stacked_widget, 1)

        # Load and display patients
        for p in self.manager.get_all_patients():
            self.patient_list.add_patient(p)

        # Connect selection callback
        self.patient_list.patient_selected.connect(self._on_patient_selected)

        # Connect button callbacks
        self.btn_create.clicked.connect(self._on_create_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        
        # Connect recording player back button
        self.recording_player.back_clicked.connect(self._on_recording_back_clicked)

    def _on_patient_selected(self, patient_id: int) -> None:
        """
        Handle patient selection from PatientListWidget.
        
        This method:
        1. Stores selected patient ID for CRUD operations
        2. Fetches patient data from database
        3. Updates sidebar with patient name and recordings
        
        Parameters:
            patient_id (int): Database ID of selected patient
        """
        # Store currently selected patient ID for CRUD operations
        self.selected_patient_id = patient_id
        
        # Fetch patient data from database
        patient = self.manager.get_patient(patient_id)
        if patient:
            # Format patient name for display: "LastName, FirstName"
            patient_name = f"{patient['last_name']}, {patient['first_name']}"
            
            # Update sidebar patient display and load recordings
            # Pass patient_id to trigger recordings update in LeftArea
            self.parent().left.set_selected_patient(patient_name, patient_id)
            
            # Fetch all recordings for this patient from database
            recordings = self.manager.get_recordings(patient_id)
            
            # Update recordings dropdown in sidebar with fetched data
            self.parent().left.update_recordings_dropdown(recordings)

    def _on_create_clicked(self) -> None:
        """
        Handle create patient button click.
        
        Opens dialog for new patient data entry.
        On acceptance, creates patient in database and adds to list.
        """
        # Open create patient dialog
        dlg = CreatePatientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_patient_data()
            if data:
                # Create new patient in database
                patient_id = self.manager.create_patient(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    birthdate=data["birthdate"]
                )
                # Fetch patient from database (includes auto-generated ID)
                patient = self.manager.get_patient(patient_id)
                if patient:
                    # Add to patient list UI
                    self.patient_list.add_patient(patient)

    def _on_delete_clicked(self) -> None:
        """
        Handle delete patient button click.
        
        Shows confirmation dialog.
        On approval, deletes patient from database and removes from UI list.
        """
        # Check if patient is selected
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        
        # Fetch patient data for confirmation dialog
        patient = self.manager.get_patient(self.selected_patient_id)
        
        # Open confirmation dialog
        dlg = DeleteConfirmDialog(self)
        if dlg.ask():
            # Delete from database
            self.manager.delete_patient(self.selected_patient_id)
            # Remove from UI list
            self.patient_list.remove_patient(self.selected_patient_id)
            # Clear selection and recordings display
            self.selected_patient_id = None
            self.parent().left.patient_name_display.setText("No patient selected")
            self.parent().left.recordings_dropdown.clear()
            self.parent().left.recordings_dropdown.addItem("-- Select a recording --")
            self.parent().left.recordings_dropdown.setEnabled(False)

    def _on_edit_clicked(self) -> None:
        """
        Handle edit patient button click.
        
        Shows edit dialog with current patient data.
        On approval, updates patient in database and refreshes UI list.
        """
        # Check if patient is selected
        if self.selected_patient_id is None:
            QMessageBox.information(self, "Info", "No patient selected.")
            return
        
        # Fetch patient from database
        patient = self.manager.get_patient(self.selected_patient_id)
        if not patient:
            QMessageBox.warning(self, "Error", "Patient not found.")
            return
        
        # Open edit patient dialog
        dlg = EditPatientDialog(self, patient_data=patient)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.get_patient_data()
            if updated:
                # Update patient in database
                self.manager.update_patient(
                    self.selected_patient_id,
                    first_name=updated["first_name"],
                    last_name=updated["last_name"],
                )
                # Refresh UI: remove old button and add updated one
                self.patient_list.remove_patient(self.selected_patient_id)
                refreshed = self.manager.get_patient(self.selected_patient_id)
                if refreshed:
                    self.patient_list.add_patient(refreshed)
                    # Restore selection to updated patient
                    self.patient_list.select_patient(self.selected_patient_id)
    
    def _on_recording_back_clicked(self) -> None:
        """
        Handle back button click from RecordingPlayerScreen.
        
        Switch back to patient list view.
        """
        self.stacked_widget.setCurrentIndex(0)  # Show patient list screen

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#f3f3f3"))
        grad.setColorAt(1.0, QColor("#d9d9d9"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# RIGHT AREA - Analysis / Info
# -------------------------------------------------
class RightArea(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure stylesheets render background
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("RIGHT AREA")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setFixedWidth(260)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#cfe6a4"))
        grad.setColorAt(1.0, QColor("#a6c96a"))
        painter.fillRect(self.rect(), grad)


# -------------------------------------------------
# OVERALL FRAMEWORK
# -------------------------------------------------
class AppLayout(QWidget):
    # Pure layout framework: Left - Center - Right
    # No logic, no screens

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.left = LeftArea()
        self.center = CenterArea()
        self.right = RightArea()

        layout.addWidget(self.left)
        layout.addWidget(self.center, 1)  # flexible
        layout.addWidget(self.right)
        
        # === Signal connections ===
        # Import Button (LeftArea) → Import handler (CenterArea)
        # When user clicks "Import Data" button, trigger TBI_Headset import workflow
        self.left.btn_import.clicked.connect(self._on_import_clicked)
        
        # Recording Selection (LeftArea) → Recording Player (CenterArea)
        # When user selects a recording from dropdown, show recording player
        self.left.recordings_dropdown.currentIndexChanged.connect(self._on_recording_selected)
        
        # Settings Button → Settings Screen
        self.left.btn_settings.clicked.connect(self._on_settings_clicked)
        
        # Help Button → Help Screen
        self.left.btn_help.clicked.connect(self._on_help_clicked)
        
        # Back buttons from screens → Patient List
        self.center.recording_player.back_clicked.connect(self._on_back_to_patients)
        self.center.help_screen.back_clicked.connect(self._on_back_to_patients)
        self.center.settings_screen.back_clicked.connect(self._on_back_to_patients)

    def _on_import_clicked(self):
        """
        Handle import button click from LeftArea.
        
        Workflow:
        1. Show ZIP file dialog (user selects file)
        2. Extract ZIP and find patient_database.db
        3. Import patients and recordings with ID mapping
        4. Show result dialog with statistics
        5. Refresh patient list in CenterArea
        """
        # Show ZIP file selection dialog
        zip_path = self.center.importer.show_file_dialog(self)
        if not zip_path:
            # User cancelled the dialog
            return
        
        # Import data from selected ZIP file
        success, result = self.center.importer.import_from_zip(zip_path)
        
        # Show result dialog to user (statistics and errors if any)
        self.center.importer.show_result_dialog(self, success, result)
        
        # Refresh patient list in CenterArea to show newly imported patients
        if success:
            self.center.patient_list.clear_patients()
            for patient in self.center.manager.get_all_patients():
                self.center.patient_list.add_patient(patient)
    
    def _on_recording_selected(self, index: int) -> None:
        """
        Handle recording selection from dropdown in LeftArea.
        
        When user selects a recording from the dropdown, display it in the
        RecordingPlayerScreen and switch to that screen.
        
        Args:
            index: Index of selected item in dropdown (0 = placeholder, 1+ = actual recordings)
        """
        # Skip placeholder items (index 0 or negative)
        if index <= 0:
            return
        
        # Get the recording data from the dropdown
        recording_data = self.left.recordings_dropdown.currentData()
        if not recording_data:
            return
        
        # Set the recording in the player and show it
        self.center.recording_player.set_recording(recording_data)
        self.center.stacked_widget.setCurrentIndex(1)  # Show recording player screen
    
    def _on_help_clicked(self) -> None:
        """Show Help screen."""
        self.center.stacked_widget.setCurrentIndex(2)
    
    def _on_settings_clicked(self) -> None:
        """Show Settings screen."""
        self.center.stacked_widget.setCurrentIndex(3)
    
    def _on_back_to_patients(self) -> None:
        """Return to Patient List screen."""
        self.center.stacked_widget.setCurrentIndex(0)