"""
Camera controller for USB cameras and LED control via Raspberry Pi.

Architecture (Option A - OpenCV):
- USB camera: exported by the Pi as a UVC gadget, detected by OpenCV
- LED: controlled via serial commands sent to the Pi (raspi-gpio/pinctrl)
- Video: stored locally on the Windows PC
- Communication: serial over COM port

OpenCV uses the Windows DirectShow API for camera detection.
Cameras are indexed numerically (0, 1, 2, ...).
User interaction with live preview ensures correct device selection.
"""

import logging
import serial
import time
import numpy as np
from typing import Optional, List
from pathlib import Path
from PIL import Image
import threading
import subprocess
import json
import os

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports with error handling for missing libraries
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV not installed. USB camera functionality is disabled.")

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.warning("pyserial not installed. LED and RPi control are disabled.")


class CameraController:
    """
    Manages USB camera access and LED control via Raspberry Pi.

    Architecture:
    - Camera: USB device exported by the Pi as UVC gadget (OpenCV via DirectShow)
    - LED: serial commands sent to the Pi (raspi-gpio/pinctrl)
    - Videos: saved locally on Windows PC
    """
    
    def __init__(self, com_port: str = 'COM3', baud_rate: int = 9600):
        """
        Initialize the camera controller.

        Args:
            com_port: serial COM port for Pi communication (default: COM3)
            baud_rate: serial baud rate (default: 9600)
        """
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_connection = None
        
        # Camera
        self.capture = None
        self.current_camera_index = None
        self.capture_lock = None  # Will import threading.Lock when needed
        
        # Frame buffering - Background thread continuously reads frames
        self.frame_thread = None
        self.frame_thread_running = False
        self.latest_frame = None
        self.frame_lock = None
        
        # Video recording
        self.is_recording = False
        self.recording_file = None
        self.video_writer = None
        self.recording_frames = []  # Buffer for frames captured during recording
        self.recording_start_time = None  # Timestamp for 8-second recording timer
        self.stop_recording_requested = False  # Flag for manual stop requests
        self.manual_stop = False  # True if user stopped, False if auto-stop after 8s
        self.recording_is_baseline = False  # True if current recording is marked as baseline
        self.baseline_counter = 0  # Counter for baseline numbering
        self.scan_counter = 0  # Counter for scan numbering
        
        # DON'T auto-connect at startup - wait for user to select port in UI
        # This prevents locking the camera/serial when the app starts
        # self._connect_serial()
        logger.info("CameraController initialized - waiting for user to select port")
    
    def disconnect_serial(self) -> bool:
        """
        Disconnect the serial connection to the Raspberry Pi.

        Returns:
            True on success
        """
        if not self.serial_connection:
            return True  # Already disconnected
        
        try:
            self.serial_connection.close()
            self.serial_connection = None
            logger.info(f"Serial connection to {self.com_port} closed")
            return True
        except Exception as e:
            logger.error(f"Error while closing serial connection: {e}")
            return False
    
    def init_serial(self) -> bool:
        """
        Initialize serial connection: close old one, open new one.

        Returns:
            True on success, otherwise False
        """
        # First disconnect old connection if exists
        try:
            self.disconnect_serial()
        except:
            pass
        
        # Add small delay for cleanup
        import time
        time.sleep(0.1)
        
        # Now reconnect
        return self._connect_serial()
    
    def _connect_serial(self) -> bool:
        """
        Connect to Raspberry Pi via serial.

        Returns:
            True on success, otherwise False
        """
        if not HAS_SERIAL:
            logger.warning("pyserial not available - LED control not possible")
            return False
        
        try:
            self.serial_connection = serial.Serial(
                self.com_port, 
                self.baud_rate, 
                timeout=2
            )
            logger.info(f"Serial connection to {self.com_port} established")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Error while connecting to {self.com_port}: {e}")
            return False
    
    def _send_serial_command(self, command: str) -> bool:
        """
        Send command to Pi over serial and wait for response.

        Args:
            command: shell command (e.g. 'pinctrl set 18 op dh')

        Returns:
            True if command was sent and executed successfully
        """
        if not self.serial_connection:
            logger.warning("No serial connection - command not sent")
            return False
        
        try:
            # Clear input and output buffers first
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Send command with newline
            cmd_bytes = (command + '\n').encode('utf-8')
            self.serial_connection.write(cmd_bytes)
            logger.info(f"Command sent: {command}")
            
            # Give the device a short processing delay
            time.sleep(0.2)
            
            # Read response from Pi (up to 1KB, max 500ms timeout)
            response = b''
            timeout_counter = 0
            while self.serial_connection.in_waiting > 0 and timeout_counter < 50:
                response += self.serial_connection.read(1)
                timeout_counter += 1
                time.sleep(0.01)
            
            if response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                # Truncate long responses (e.g. login banners)
                if len(response_str) > 200:
                    response_str = response_str[-200:]  # Keep only the last 200 chars
                logger.info(f"Pi response: {response_str}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error while sending command: {e}")
            return False
    
    def list_cameras(self) -> List[str]:
        """
        List all available USB cameras.

        NOTE: DirectShow on Windows can be quirky. We only validate whether
        indices can be opened here; full frame-read testing happens in connect_camera().

        Returns:
            List of camera description strings
        """
        if not HAS_OPENCV:
            logger.warning("OpenCV not available - camera detection not possible")
            return []
        
        camera_info = []
        
        # Check only first 5 indices (typically 0 = webcam, 1+ = optional)
        # IMPORTANT: We do NOT read every frame here to avoid OpenCV buffer conflicts
        for index in range(5):
            try:
                cap = cv2.VideoCapture(index)
                
                if cap.isOpened():
                    # Existence check only, NO frame test
                    # This prevents OpenCV buffer issues
                    info = f"[{index}] Camera"
                    camera_info.append(info)
                    logger.info(f"Camera index {index} available")
                    cap.release()
                else:
                    # No further camera found from this index onward
                    break
                    
            except Exception as e:
                logger.debug(f"Index {index} nicht verfügbar: {e}")
                break
        
        return camera_info if camera_info else []
    
    def connect_camera(self, device_index: int = 0) -> bool:
        """
        Connect to a USB camera via OpenCV.

        Args:
            device_index: camera index (default: 0 = first camera)

        Returns:
            True on success, otherwise False
        """
        if not HAS_OPENCV:
            logger.error("OpenCV nicht verfügbar - Kann nicht zu Kamera verbinden")
            return False
        
        try:
            # Initialize the lock for thread-safe capture access
            import threading
            if self.capture_lock is None:
                self.capture_lock = threading.Lock()
            
            # Close existing connection
            if self.capture:
                self.disconnect_camera()
            
            print(f"[camera_controller] Opening capture device {device_index}...")
            
            # Open new connection
            self.capture = cv2.VideoCapture(device_index)
            
            if not self.capture.isOpened():
                logger.error(f"Could not open camera {device_index}")
                self.capture = None
                return False
            
            print(f"[camera_controller] Capture device opened successfully")
            
            self.current_camera_index = device_index
            
            # Set resolution for better performance
            print(f"[camera_controller] Setting resolution to 640x480...")
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_FPS, 30)
            
            # Test: Try to read one frame (with lock for thread safety)
            if self.capture_lock is None:
                self.capture_lock = threading.Lock()
            print(f"[camera_controller] Testing frame read...")
            with self.capture_lock:
                ret, frame = self.capture.read()
            if not ret or frame is None:
                logger.error(f"Cannot read frame from camera {device_index}")
                self.disconnect_camera()
                return False
            
            print(f"[camera_controller] Frame read successful: {frame.shape}")
            logger.info(f"Connected to camera: index {device_index}")
            
            # Try LED - but don't fail if it doesn't work
            try:
                print(f"[camera_controller] Turning LED on...")
                self.led_on()
                print(f"[camera_controller] LED on successful")
            except Exception as led_err:
                logger.warning(f"LED control failed but camera is connected: {led_err}")
                # Don't fail - camera is still connected even if LED doesn't work
            
            return True
            
        except Exception as e:
            logger.error(f"Error while connecting camera: {e}")
            import traceback
            traceback.print_exc()
            if self.capture:
                try:
                    self.capture.release()
                    self.capture = None
                except:
                    pass
            return False
    
    def disconnect_camera(self):
        """Disconnect camera connection."""
        if self.capture:
            try:
                self.capture.release()
                self.capture = None
                logger.info("Camera connection closed")
            except Exception as e:
                logger.error(f"Error while closing camera: {e}")
    
    def get_frame(self) -> Optional[Image.Image]:
        """
        Get a video frame from the connected camera.

        Thread-safe via lock protection around OpenCV capture access.

        Returns:
            PIL Image (RGB format) or None on error
        """
        #print(f"[get_frame] capture={self.capture is not None}, isOpened={self.capture.isOpened() if self.capture else False}")
        
        if not self.capture or not self.capture.isOpened():
            logger.debug("No camera connected")
            #print(f"[get_frame] FAILED: No capture or not open")
            return None
        
        try:
            # Use lock for thread-safe capture access
            if self.capture_lock:
                with self.capture_lock:
                    ret, frame = self.capture.read()
                    #print(f"[get_frame] read result: ret={ret}, frame={'OK' if frame is not None else 'None'}")
                    
                    if ret and frame is not None:
                        # Convert BGR to RGB and then to PIL Image
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        #print(f"[get_frame] returning PIL image: {pil_image.size}")
                        return pil_image
                    else:
                        logger.warning("Error while reading frame")
                        #print(f"[get_frame] FAILED: ret={ret}, frame={frame}")
                        return None
            else:
                # Lock not available - create it now and use it
                self.capture_lock = threading.Lock()
                with self.capture_lock:
                    ret, frame = self.capture.read()
                #print(f"[get_frame] read result (with lock): ret={ret}, frame={'OK' if frame is not None else 'None'}")
                if ret and frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    #print(f"[get_frame] returning PIL image: {pil_image.size}")
                    return pil_image
                else:
                    logger.warning("Error while reading frame")
                    #print(f"[get_frame] FAILED: ret={ret}, frame={frame}")
                    return None
            
        except Exception as e:
            logger.error(f"Error while retrieving frame: {e}")
            return None
    
    def led_on(self) -> bool:
        """
        Turn LED (GPIO 18) on on the Pi.
        Command: pinctrl set 18 op dh (modern pinctrl, replaces deprecated raspi-gpio)

        Returns:
            True on success, otherwise False
        """
        return self._send_serial_command('pinctrl set 18 op dh')
    
    def led_off(self) -> bool:
        """
        Turn LED (GPIO 18) off on the Pi.
        Command: pinctrl set 18 op dl (modern pinctrl, replaces deprecated raspi-gpio)

        Returns:
            True on success, otherwise False
        """
        return self._send_serial_command('pinctrl set 18 op dl')
    
    def start_recording(self, output_file: Optional[str] = None, is_baseline: bool = False, patient_id: Optional[str] = None) -> bool:
        """
        Start video recording from camera (8-second pupillometry protocol).
        Videos are stored locally on the Windows PC.

        Args:
            output_file: output file path (requested if None - for file dialog)
            is_baseline: True for baseline recording, False for normal recording
            patient_id: patient identifier for saving into the correct folder

        Returns:
            True on success, otherwise False
        """
        if not self.capture:
            logger.error("No camera connected - recording is not possible")
            return False
        
        if self.is_recording:
            logger.warning("Recording is already running")
            return False
        
        try:
            # Start recording in background
            self.recording_file = output_file if output_file else "pending"  # Resolved later
            self.recording_is_baseline = is_baseline
            self.is_recording = True
            self.stop_recording_requested = False
            self.manual_stop = False
            self.recording_frames = []
            self.recording_start_time = time.time()
            
            baseline_label = "Baseline" if is_baseline else "Scan"
            logger.info(f"Recording started (8-second protocol, {baseline_label})")
            
            # Start the recording loop
            self._recording_loop(is_baseline, patient_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error while starting recording: {e}")
            self.is_recording = False
            return False
    
    def _recording_loop(self, is_baseline: bool = False, patient_id: Optional[str] = None):
        """
        Internal recording loop (called by start_recording()).
        - 8 seconds recording
        - LED stimulus at 1.0-2.0s (for both baseline and normal recordings)
        - Baseline/normal differ only in DB tagging, not in capture protocol
        - Save to MP4 at the end with timestamp naming
        """
        DURATION = 8.0  # 8 seconds
        LED_ON_DELAY = 1.0  # LED ON after 1s
        LED_ON_DURATION = 1.0  # LED stays ON for 1.0s (1.0-2.0s total)
        
        logger.info(f"[_recording_loop] Starting: is_baseline={is_baseline}, patient_id={patient_id}")
        
        # Read frame rate and resolution
        fps = int(self.capture.get(cv2.CAP_PROP_FPS)) or 30  # Default 30 FPS
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Recording mit {fps}FPS, {width}x{height}px, is_baseline={is_baseline}")
        
        # Start recording thread - pass is_baseline and patient_id explicitly
        recording_thread = threading.Thread(
            target=self._recording_thread,
            args=(DURATION, LED_ON_DELAY, LED_ON_DURATION, fps, width, height, is_baseline, patient_id)
        )
        recording_thread.daemon = False
        recording_thread.start()
        logger.info(f"[_recording_loop] Thread started")
    
    def _recording_thread(self, duration, led_on_delay, led_on_duration, fps, width, height, is_baseline: bool = False, patient_id: Optional[str] = None):
        """
        Thread routine for video recording with LED stimulus.

        Args:
            Duration: recordings duration in seconds
            led_on_delay: delay until LED ON (1.0s)
            led_on_duration: LED ON duration (1.0s -> 1.0-2.0s total)
            is_baseline: True for baseline capture (same LED stimulus as normal)
            patient_id: patient identifier for folder storage
        """
        try:
            logger.info(f"[_recording_thread START] is_baseline={is_baseline}, patient_id={patient_id}, duration={duration}s")
            frame_count = 0
            led_activated = False
            
            # LED aus am Start (BEFORE timing starts to avoid serial delay)
            self.led_off()
            logger.info(f"[_recording_thread] LED OFF at start, is_baseline={is_baseline}")
            
            # Flush camera buffer: discard stale frames
            for _ in range(10):
                self.capture.read()
            
            # Start timer AFTER(!) led_off and buffer flush
            start_time = time.time()
            
            while (time.time() - start_time) < duration and not self.stop_recording_requested:
                elapsed = time.time() - start_time
                
                    # LED stimulus at 1.0-2.0s for both baseline and normal recordings
                    # (Baseline also needs LED to remain comparable to normal)
                if led_on_delay <= elapsed < (led_on_delay + led_on_duration):
                    if not led_activated:
                        self.led_on()
                        led_activated = True
                        logger.info(f"LED ON bei {elapsed:.2f}s")
                elif led_activated and elapsed >= (led_on_delay + led_on_duration):
                    self.led_off()
                    led_activated = False
                    logger.info(f"LED OFF bei {elapsed:.2f}s")
                
                # Capture Frame
                ret, frame = self.capture.read()
                if ret and frame is not None:
                    # Store frame in RGB format (not BGR)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.recording_frames.append((frame_rgb, elapsed))
                    frame_count += 1
                    
                    # Log every 1 second
                    if frame_count % (fps or 30) == 0:
                        logger.debug(f"Recording: {elapsed:.1f}s, {frame_count} frames")
                else:
                    logger.warning("Frame capture failed")
                    time.sleep(0.01)  # Short pause to reduce CPU load
            
            # Turn LED off at the end
            self.led_off()
            
            # Save recorded frames
            if self.stop_recording_requested:
                # Manually stopped - handled by UI dialog
                self.manual_stop = True
                logger.info(f"Recording manually stopped after {elapsed:.2f}s")
            else:
                # Auto-stop after 8s - save recording
                self.manual_stop = False
                logger.info(f"[_recording_thread] Auto-stop after {elapsed:.2f}s - saving {len(self.recording_frames)} frames, is_baseline={is_baseline}, patient_id={patient_id}")
                result = self._save_recording_to_file(is_baseline=is_baseline, patient_id=patient_id)
                logger.info(f"[_recording_thread] Save result: {result}")
            
            self.is_recording = False  # CRITICAL: Always reset flag at end
            logger.info(f"[_recording_thread END] is_baseline={is_baseline}")
            
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.is_recording = False  # CRITICAL: Reset flag on error
            self.led_off()
    
    def _save_recording_to_file(self, output_file: Optional[str] = None, is_baseline: bool = False, patient_id: Optional[str] = None) -> Optional[str]:
        """
        Save captured frames to MP4 using timestamp-based naming.

        Naming schema:
        - Normal: {unix_timestamp}_scan_{number}.mp4
        - Baseline: {unix_timestamp}_baseline.mp4

        Args:
            output_file: target file (if None, generated automatically)
            is_baseline: True for baseline recording
            patient_id: patient identifier for folder, e.g. "patient_001"

        Returns:
            Path to saved file or None on error
        """
        if not self.recording_frames:
            logger.error("No frames available to save")
            return None
        
        try:
            # Generate output file if not provided
            if not output_file or output_file == "pending":
                # Create patient folder if patient_id is provided
                if patient_id:
                    recordings_dir = Path("data/recordings") / str(patient_id)
                else:
                    recordings_dir = Path("data/recordings")
                
                recordings_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename in YYYY-MM-DD-HH-MM-SS format (same as TBI schema)
                from datetime import datetime as dt
                timestamp_str = dt.now().strftime("%Y-%m-%d-%H-%M-%S")
                filename = f"{timestamp_str}.mp4"
                
                output_file = str(recordings_dir / filename)
                logger.info(f"Auto-generated filename: {filename} (is_baseline={is_baseline}, patient_id={patient_id})")
            
            # Get first frame for dimensions
            first_frame = self.recording_frames[0][0]
            height, width = first_frame.shape[:2]
            
            # Define codec and VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Calculate actual FPS from real wall-clock timestamps
            if len(self.recording_frames) >= 2:
                first_ts = self.recording_frames[0][1]
                last_ts = self.recording_frames[-1][1]
                real_duration = last_ts - first_ts
                if real_duration > 0:
                    fps = len(self.recording_frames) / real_duration
                else:
                    fps = 20
            else:
                fps = 20
            
            logger.info(f"Calculated actual FPS: {fps:.1f} ({len(self.recording_frames)} frames / {real_duration:.2f}s)")
            out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error(f"VideoWriter konnte nicht geöffnet werden: {output_file}")
                return None
            
            # Write frames
            for frame_rgb, elapsed in self.recording_frames:
                # Convert RGB back to RGB for OpenCV
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
            
            out.release()
            
            file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
            recording_type = "Baseline" if is_baseline else "Scan"
            logger.info(f"Recording saved ({recording_type}): {output_file} ({file_size_mb:.2f}MB, {len(self.recording_frames)} frames)")
            
            self.recording_file = output_file
            self.recording_frames = []  # Clear frame buffer
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error while saving recording: {e}")
            return None
    
    def start_recording_with_pupillometry(self, duration: float = 8.0, 
                                         led_on_delay: float = 1.0,
                                         output_video: Optional[str] = None,
                                         is_baseline: bool = False,
                                         patient_id: Optional[str] = None) -> Optional[str]:
        """
        Start recording using the 8-second pupillometry protocol.

        Args:
            duration: recording duration in seconds (default: 8.0)
            led_on_delay: delay until LED ON in seconds (default: 1.0)
            output_video: output MP4 file (auto-generated if None)
            is_baseline: True for baseline capture (same LED stimulus as normal)
            patient_id: patient identifier for folder storage

        Returns:
            Path to saved file or None on Error
        """
        if not self.capture:
            logger.error("No camera connected")
            return None
        
        if self.is_recording:
            logger.warning("Recording is already running")
            return None
        
        try:
            self.is_recording = True
            self.recording_is_baseline = is_baseline
            self.stop_recording_requested = False
            self.manual_stop = False
            self.recording_frames = []
            self.recording_start_time = time.time()
            
            # Read frame rate and resolution
            fps = int(self.capture.get(cv2.CAP_PROP_FPS)) or 30
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            recording_type = "Baseline" if is_baseline else "Pupillometrie"
            logger.info(f"Starting {recording_type} recording: {duration}s (patient_id={patient_id})")
            
            # LED aus am Start (BEFORE timing starts to avoid serial delay in the loop)
            self.led_off()
            
            # Flush camera buffer: discard stale frames so the first recorded
            # frame is truly "live". OpenCV buffers ~5 frames internally.
            for _ in range(10):
                if self.capture_lock:
                    with self.capture_lock:
                        self.capture.read()
                else:
                    self.capture.read()
            
            # Recording loop
            LED_ON_DURATION = 1.0  # Correct: 1.0-2.0s (not 1.0-1.5s)
            frame_count = 0
            # Start timer AFTER led_off and buffer flush are done
            start_time = time.time()
            led_activated = False
            
            while (time.time() - start_time) < duration and not self.stop_recording_requested:
                elapsed = time.time() - start_time
                
                # LED stimulus at 1.0-2.0s for both baseline and normal recordings
                if led_on_delay <= elapsed < (led_on_delay + LED_ON_DURATION):
                    if not led_activated:
                        self.led_on()
                        led_activated = True
                        logger.info(f"LED ON bei {elapsed:.2f}s")
                elif led_activated and elapsed >= (led_on_delay + LED_ON_DURATION):
                    self.led_off()
                    led_activated = False
                    logger.info(f"LED OFF bei {elapsed:.2f}s")
                
                # Capture Frame (with lock for thread safety)
                if self.capture_lock:
                    with self.capture_lock:
                        ret, frame = self.capture.read()
                else:
                    ret, frame = self.capture.read()
                
                if ret and frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.recording_frames.append((frame_rgb, elapsed))
                    frame_count += 1
                else:
                    time.sleep(0.01)
            
            # Turn LED off at the End
            self.led_off()
            
            # Determine whether stop was manual or automatic
            if self.stop_recording_requested:
                self.manual_stop = True
                self.is_recording = False
                return None  # Handled by UI
            else:
                # Auto-stop - save recording
                result = self._save_recording_to_file(output_video, is_baseline=is_baseline, patient_id=patient_id)
                self.is_recording = False  # CRITICAL: Reset flag after save completes
                return result
        
        except Exception as e:
            logger.error(f"Error in {recording_type} recording: {e}")
            self.is_recording = False
            self.led_off()
            return None
    
    def stop_recording(self) -> bool:
        """
        Stop video recording (manual stop by user).

        Returns:
            True on succes, otherwise False
        """
        if not self.is_recording:
            logger.warning("No active recording")
            return False
        
        try:
            self.stop_recording_requested = True
            self.manual_stop = True
            logger.info("Recording stop requested")
            
            # Give thread time to stop (max 1s)
            elapsed = 0
            while self.is_recording and elapsed < 1.0:
                time.sleep(0.01)
                elapsed += 0.01
            
            return True
            
        except Exception as e:
            logger.error(f"Error while stopping recording: {e}")
            self.is_recording = False
            return False
    
    def get_recorded_duration(self) -> float:
        """
        Return current recorded duration in seconds.

        Returns:
            Duration in seconds, or 0 if not recording
        """
        if not self.is_recording or not self.recording_frames:
            return 0.0
        
        if not self.recording_frames:
            return 0.0
        
        # The last frame contains the current elapsed time
        return self.recording_frames[-1][1]
    
    def get_recorded_frame_count(self) -> int:
        """
        Return the number of recorded frames.

        Returns:
            Frame count
        """
        return len(self.recording_frames)
    
    def delete_temp_recording(self) -> bool:
        """
        Delete temporarily recorded frames.
        (Called when the user selects delete.)

        Returns:
            True on success, otherwise False
        """
        try:
            self.recording_frames = []
            self.recording_file = None
            self.is_recording = False
            logger.info("Temporary recording deleted")
            return True
        except Exception as e:
            logger.error(f"Error while deleting recording: {e}")
            return False
    
    def save_manual_recording(self, output_file: str) -> Optional[str]:
        """
        Save manually stopped recording to specified file.

        Args:
            output_file: target file

        Returns:
            Path to saved file or None on error
        """
        return self._save_recording_to_file(output_file)
    
    def get_status(self) -> dict:
        """
        Return status of camera, LED, and recording.

        Returns:
            Dictionary with status information
        """
        return {
            'serial_connected': self.serial_connection is not None,
            'com_port': self.com_port,
            'camera_connected': self.capture is not None,
            'current_camera': str(self.current_camera_index) if self.current_camera_index is not None else None,
            'is_recording': self.is_recording,
            'recording_file': self.recording_file,
            'cameras_available': len(self.list_cameras()),
            'has_opencv': HAS_OPENCV,
            'has_serial': HAS_SERIAL
        }
    
    def disconnect(self):
        """Cleanup: disconnect all connections."""
        # Stop recording if active
        if self.is_recording:
            self.stop_recording()
        
        # Disconnect camera
        self.disconnect_camera()
        
        # Disconnect seriell
        if self.serial_connection:
            try:
                # Turn LED off
                self.led_off()
                self.serial_connection.close()
                self.serial_connection = None
                logger.info("Serial connection closed")
            except Exception as e:
                logger.error(f"Error while closing serial connection: {e}")


# Example / test code
if __name__ == "__main__":
    import time
    
    print("\n" + "=" * 60)
    print("Camera Controller Test")
    print("=" * 60)
    
    # Initialize controller
    print("\n1. Initializing camera controller...")
    controller = CameraController(com_port='COM3')
    
    # Show status
    print("\n2. Showing status...")
    status = controller.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # List available cameras
    print("\n3. Searching USB cameras...")
    cameras = controller.list_cameras()
    if cameras:
        for camera in cameras:
            print(f"   {camera}")
    else:
        print("   No cameras found")
    
    # Test LED (if serial connection exists)
    print("\n4. LED Test...")
    print("   LED an...")
    controller.led_on()
    time.sleep(1)
    
    print("   LED aus...")
    controller.led_off()
    time.sleep(1)
    
    # Connect to first available camera
    if cameras:
        print("\n5. Verbinde zur Kamera...")
        if controller.connect_camera(0):
            print("   Verbunden!")
            
            # Frame test
            print("   Hole Frame...")
            frame = controller.get_frame()
            if frame:
                print(f"   Frame received!")
            else:
                print("   No frame")
            
            # Test recording
            print("\n6. Recording Test...")
            if controller.start_recording():
                print("   Recording gestartet...")
                time.sleep(2)
                controller.stop_recording()
                print("   Recording gestoppt")
            
            # Cleanup
            print("\n7. Cleanup...")
            controller.disconnect()
            print("   Disconnected")
    else:
        print("\n5. No cameras available - skipping camera test")
        controller.disconnect()
    
    print("\n" + "=" * 60)
    print("Test finished")
    print("=" * 60 + "\n")
