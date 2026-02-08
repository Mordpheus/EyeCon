"""
Camera Controller für USB-Webcam
Nutzt OpenCV (cv2) für USB-Webcam Erfassung
LED-Steuerung über Serial COM3
"""

import cv2
from PIL import Image
import threading
import logging
import serial
import time
import numpy as np

logger = logging.getLogger(__name__)


class CameraController:
    """
    Controller für USB-Webcam mit OpenCV
    LED-Steuerung über Serial COM3
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton Pattern - nur eine Instanz"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, com_port: str = 'COM3', baud_rate: int = 9600, mock_mode: bool = False):
        """
        Initialisiert Camera Controller
        
        Args:
            com_port: Serial Port für LED-Steuerung
            baud_rate: Baud-Rate für Serial
            mock_mode: True = Mock-Frames, False = echte USB-Webcam
        """
        if self._initialized:
            return
        
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_conn = None
        self.camera = None
        self.current_frame = None
        self.mock_mode = mock_mode
        
        # LED-Status
        self.led_on_state = False
        
        # Serial verbinden
        self._connect_serial()
        
        # Kamera initialisieren
        if not self.mock_mode:
            self._connect_camera()
        
        self._initialized = True
        mode_str = "MOCK" if mock_mode else "LIVE (USB-Webcam)"
        logger.info(f"CameraController initialisiert: [{mode_str}]")
    
    def _connect_serial(self):
        """Verbindet mit Serial COM Port"""
        try:
            self.serial_conn = serial.Serial(
                port=self.com_port,
                baudrate=self.baud_rate,
                timeout=1,
                write_timeout=1
            )
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            logger.info(f"Serial verbunden: {self.com_port}@{self.baud_rate}")
            return True
        except Exception as e:
            logger.error(f"Serial-Fehler: {e}")
            self.serial_conn = None
            return False
    
    def _connect_camera(self):
        """Verbindet mit USB-Webcam"""
        try:
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                logger.info(f"USB-Webcam verbunden")
                return True
            else:
                logger.error("USB-Webcam konnte nicht geöffnet werden")
                self.camera = None
                return False
        except Exception as e:
            logger.error(f"Camera-Fehler: {e}")
            self.camera = None
            return False
    
    def _send_command(self, command: str) -> str:
        """
        Sendet Befehl über Serial an Pi
        
        Args:
            command: Befehl (z.B. "pinctrl set 18 op dh")
            
        Returns:
            Antwort vom Pi
        """
        if self.serial_conn is None or not self.serial_conn.is_open:
            logger.error("Serial nicht verbunden!")
            return ""
        
        try:
            # Puffer clearen
            self.serial_conn.reset_input_buffer()
            
            # Befehl senden
            self.serial_conn.write((command + '\n').encode())
            
            # Auf Antwort warten
            time.sleep(0.2)
            response = self.serial_conn.read_all().decode(errors='ignore')
            
            return response
        except Exception as e:
            logger.error(f"Command-Fehler: {e}")
            return ""
    
    def led_on(self):
        """LED anschalten (GPIO 18 high)"""
        if not self.led_on_state:
            response = self._send_command("pinctrl set 18 op dh")
            self.led_on_state = True
            logger.info(f"LED AN: {response}")
            return True
        return False
    
    def led_off(self):
        """LED ausschalten (GPIO 18 low)"""
        if self.led_on_state:
            response = self._send_command("pinctrl set 18 op dl")
            self.led_on_state = False
            logger.info(f"LED AUS: {response}")
            return True
        return False
    
    def list_cameras(self):
        """
        Listet verfügbare Kameras auf
        Für USB-Webcam: Versucht cv2.VideoCapture Indizes
        """
        cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                cameras.append({
                    "index": i,
                    "name": f"USB-Webcam {i} ({width}x{height})"
                })
                cap.release()
        return cameras
    
    def connect_camera(self, index: int = 0) -> bool:
        """
        Verbindet mit USB-Webcam
        
        Args:
            index: Kamera-Index (Standard: 0)
            
        Returns:
            True wenn erfolgreich
        """
        try:
            if self.camera is None or not self.camera.isOpened():
                self.camera = cv2.VideoCapture(index)
                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                    logger.info(f"Mit Webcam {index} verbunden")
                    return True
        except Exception as e:
            logger.error(f"Camera-Verbindungsfehler: {e}")
        return False
    
    def get_frame(self) -> Image.Image:
        """
        Holt einen Frame
        - Mock-Mode: Generiert schwarzen Frame
        - Live-Mode: Von USB-Webcam mit OpenCV
        
        Returns:
            Frame als PIL Image oder None
        """
        if self.mock_mode:
            from PIL import ImageDraw
            frame = Image.new('RGB', (640, 480), color='black')
            draw = ImageDraw.Draw(frame)
            text = "MOCK MODE\n\nWaiting for Camera..."
            draw.text((320, 240), text, fill='white', anchor='mm')
            return frame
        
        # Live-Mode: Von USB-Webcam
        if self.camera is None or not self.camera.isOpened():
            if not self._connect_camera():
                return None
        
        try:
            ret, frame = self.camera.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                self.current_frame = pil_image
                return pil_image
        except Exception as e:
            logger.warning(f"Frame-Fehler: {e}")
        
        return None
    
    def start_recording_with_pupillometry(self, duration: int = 8, 
                                          led_on_delay: float = 1.0,
                                          output_video: str = "recording.mp4"):
        """
        Startet Recording mit LED-Stimulus
        
        Args:
            duration: Dauer in Sekunden
            led_on_delay: Verzögerung bis LED angeht (Sekunden)
            output_video: Ausgabe-Dateiname
        """
        logger.info(f"Starte Recording: {duration}s mit LED-Stimulus bei t={led_on_delay}s")
        
        frames = []
        frame_count = 0
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # LED-Stimulus auslösen
                elapsed = time.time() - start_time
                if led_on_delay < elapsed < led_on_delay + 0.5 and not self.led_on_state:
                    self.led_on()
                elif elapsed >= led_on_delay + 0.5 and self.led_on_state:
                    self.led_off()
                
                # Frame capturen
                frame = self.get_frame()
                if frame:
                    frames.append(frame)
                    frame_count += 1
                
                time.sleep(0.05)  # ~20 FPS
            
            # LED ausschalten
            self.led_off()
            
            logger.info(f"Recording fertig: {frame_count} Frames capturt")
            # TODO: Frames zu Video speichern
            
        except Exception as e:
            logger.error(f"Recording-Fehler: {e}")
            self.led_off()
    
    def disconnect(self):
        """Trennt die Verbindung"""
        if self.camera:
            self.camera.release()
            logger.info("Webcam geschlossen")
        if self.serial_conn:
            self.serial_conn.close()
            logger.info("Serial geschlossen")
    
    def __del__(self):
        """Cleanup"""
        try:
            self.disconnect()
        except:
            pass
