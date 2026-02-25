"""
Camera Controller für USB-Kameras und LED-Steuerung über Raspberry Pi

Architektur (Option A - OpenCV):
- USB-Kamera: Wird vom Pi als uvc-gadget exportiert, OpenCV erkennt sie
- LED: Steuerung über Serial-Befehle an den Pi (raspi-gpio)
- Video: Speichern lokal auf Windows PC
- Kommunikation: Serial über COM-Port

OpenCV nutzt Windows DirectShow API zur Kameradetektion.
Kameras werden numerisch indiziert (0, 1, 2, ...).
Nutzerinteraktion mit Live-Vorschau gewährleistet korrekte Auswahl.
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

# Import mit Error-Handling für fehlende Libraries
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV nicht installiert. USB-Kamera-Funktionalität deaktiviert.")

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
    logger.warning("pyserial nicht installiert. LED und RPi-Steuerung deaktiviert.")


class CameraController:
    """
    Verwaltet USB-Kamera und LED-Steuerung über Raspberry Pi
    
    Architektur:
    - Kamera: USB-Gerät (vom Pi als uvc-gadget exportiert, OpenCV via DirectShow)
    - LED: Über Serial-Befehle zum Pi (raspi-gpio)
    - Videos: Lokal auf Windows PC speichern
    """
    
    def __init__(self, com_port: str = 'COM3', baud_rate: int = 9600):
        """
        Initialisiert Camera Controller
        
        Args:
            com_port: Serial COM-Port für Pi Kommunikation (default: COM3)
            baud_rate: Baud-Rate für Serial (default: 9600)
        """
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.serial_connection = None
        
        # Kamera
        self.capture = None
        self.current_camera_index = None
        self.capture_lock = None  # Will import threading.Lock when needed
        
        # Frame buffering - Background thread continuously reads frames
        self.frame_thread = None
        self.frame_thread_running = False
        self.latest_frame = None
        self.frame_lock = None
        
        # Video-Aufnahme
        self.is_recording = False
        self.recording_file = None
        self.video_writer = None
        self.recording_frames = []  # Buffer für Frames während Aufnahme
        self.recording_start_time = None  # Zeitstempel für 8-Sekunden-Zähler
        self.stop_recording_requested = False  # Flag für manuelles Stoppen
        self.manual_stop = False  # True wenn Benutzer Stop drückt, False wenn Auto-Stop nach 8s
        self.recording_is_baseline = False  # True wenn aktuelle Recording als Baseline markiert
        self.baseline_counter = 0  # Counter für Baseline-Nummern
        self.scan_counter = 0  # Counter für Scan-Nummern
        
        # DON'T auto-connect at startup - wait for user to select port in UI
        # This prevents locking the camera/serial when the app starts
        # self._connect_serial()
        logger.info("CameraController initialized - waiting for user to select port")
    
    def disconnect_serial(self) -> bool:
        """
        Trenne Serial-Verbindung zu Raspberry Pi
        
        Returns:
            True wenn erfolgreich
        """
        if not self.serial_connection:
            return True  # Already disconnected
        
        try:
            self.serial_connection.close()
            self.serial_connection = None
            logger.info(f"Serial-Verbindung zu {self.com_port} geschlossen")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Schließen der Serial-Verbindung: {e}")
            return False
    
    def init_serial(self) -> bool:
        """
        Initialisiere Serial-Verbindung: Schließe alte, öffne neue
        
        Returns:
            True wenn erfolgreich, False sonst
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
        Verbinde zu Raspberry Pi über Serial
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not HAS_SERIAL:
            logger.warning("pyserial nicht verfügbar - LED-Steuerung nicht möglich")
            return False
        
        try:
            self.serial_connection = serial.Serial(
                self.com_port, 
                self.baud_rate, 
                timeout=2
            )
            logger.info(f"Serial-Verbindung zu {self.com_port} erfolgreich")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Fehler beim Verbinden zu {self.com_port}: {e}")
            return False
    
    def _send_serial_command(self, command: str) -> bool:
        """
        Sende Befehl zum Pi über Serial und warte auf Antwort
        
        Args:
            command: Shell-Befehl (z.B. 'pinctrl set 18 op dh')
        
        Returns:
            True wenn erfolgreich gesendet und Befehl ausgeführt
        """
        if not self.serial_connection:
            logger.warning("Keine Serial-Verbindung - Befehl nicht gesendet")
            return False
        
        try:
            # Leere den Input- und Output-Buffer zuerst
            self.serial_connection.reset_input_buffer()
            self.serial_connection.reset_output_buffer()
            
            # Sende Befehl mit Newline
            cmd_bytes = (command + '\n').encode('utf-8')
            self.serial_connection.write(cmd_bytes)
            logger.info(f"Befehl gesendet: {command}")
            
            # Warte kurz auf Verarbeitung
            time.sleep(0.2)
            
            # Lese Antwort vom Pi (bis zu 1KB, max 500ms Timeout)
            response = b''
            timeout_counter = 0
            while self.serial_connection.in_waiting > 0 and timeout_counter < 50:
                response += self.serial_connection.read(1)
                timeout_counter += 1
                time.sleep(0.01)
            
            if response:
                response_str = response.decode('utf-8', errors='ignore').strip()
                # Kürze lange Antworten (z.B. Login-Banner)
                if len(response_str) > 200:
                    response_str = response_str[-200:]  # Nur letzte 200 Zeichen
                logger.info(f"Pi-Antwort: {response_str}")
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Senden des Befehls: {e}")
            return False
    
    def list_cameras(self) -> List[str]:
        """
        Listet alle verfügbaren USB-Kameras auf
        HINWEIS: DirectShow unter Windows ist quirky - wir prüfen nur ob die Indices gültig sind
        Das vollständige Frame-Test wird in connect_camera() gemacht
        
        Returns:
            List von Kamera-Beschreibungen
        """
        if not HAS_OPENCV:
            logger.warning("OpenCV nicht verfügbar - Kamera-Erkennung nicht möglich")
            return []
        
        camera_info = []
        
        # Prüfe nur die ersten 5 Indices (normalmente 0 = webcam, 1+ = optional)
        # WICHTIG: Wir lesen NICHT jeden Frame, um OpenCV-Buffer-Konflikte zu vermeiden
        for index in range(5):
            try:
                cap = cv2.VideoCapture(index)
                
                if cap.isOpened():
                    # Nur Existence Check, KEIN Frame-Test
                    # Das verhindert OpenCV-Buffer-Probleme
                    info = f"[{index}] Kamera"
                    camera_info.append(info)
                    logger.info(f"Kamera Index {index} verfügbar")
                    cap.release()
                else:
                    # Keine weitere Kamera ab diesem Index
                    break
                    
            except Exception as e:
                logger.debug(f"Index {index} nicht verfügbar: {e}")
                break
        
        return camera_info if camera_info else []
    
    def connect_camera(self, device_index: int = 0) -> bool:
        """
        Verbindet zu einer USB-Kamera über OpenCV
        
        Args:
            device_index: Index der Kamera (default: 0 = erste Kamera)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not HAS_OPENCV:
            logger.error("OpenCV nicht verfügbar - Kann nicht zu Kamera verbinden")
            return False
        
        try:
            # Initialize the lock for thread-safe capture access
            import threading
            if self.capture_lock is None:
                self.capture_lock = threading.Lock()
            
            # Bestehende Verbindung schließen
            if self.capture:
                self.disconnect_camera()
            
            print(f"[camera_controller] Opening capture device {device_index}...")
            
            # Neue Verbindung
            self.capture = cv2.VideoCapture(device_index)
            
            if not self.capture.isOpened():
                logger.error(f"Konnte Kamera {device_index} nicht öffnen")
                self.capture = None
                return False
            
            print(f"[camera_controller] Capture device opened successfully")
            
            self.current_camera_index = device_index
            
            # Setze Resolution für bessere Performance
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
            logger.info(f"Verbunden zu Kamera: Index {device_index}")
            
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
            logger.error(f"Fehler beim Verbinden zur Kamera: {e}")
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
        """Trennt Kameraverbindung"""
        if self.capture:
            try:
                self.capture.release()
                self.capture = None
                logger.info("Kamera-Verbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Kamera: {e}")
    
    def get_frame(self) -> Optional[Image.Image]:
        """
        Holt einen Video-Frame von der verbundenen Kamera
        Thread-safe mit Lock zum Schutz von OpenCV-Capture
        
        Returns:
            PIL Image (RGB format) oder None bei Fehler
        """
        #print(f"[get_frame] capture={self.capture is not None}, isOpened={self.capture.isOpened() if self.capture else False}")
        
        if not self.capture or not self.capture.isOpened():
            logger.debug("Keine Kamera verbunden")
            #print(f"[get_frame] FAILED: No capture or not open")
            return None
        
        try:
            # Use lock for thread-safe capture access
            if self.capture_lock:
                with self.capture_lock:
                    ret, frame = self.capture.read()
                    #print(f"[get_frame] read result: ret={ret}, frame={'OK' if frame is not None else 'None'}")
                    
                    if ret and frame is not None:
                        # Konvertiere BGR zu RGB und dann zu PIL Image
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        #print(f"[get_frame] returning PIL image: {pil_image.size}")
                        return pil_image
                    else:
                        logger.warning("Fehler beim Lesen des Frames")
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
                    logger.warning("Fehler beim Lesen des Frames")
                    #print(f"[get_frame] FAILED: ret={ret}, frame={frame}")
                    return None
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Frames: {e}")
            return None
    
    def led_on(self) -> bool:
        """
        Schaltet LED (GPIO 18) auf dem Pi ein
        Befehl: pinctrl set 18 op dh (modernes pinctrl, ersetzt deprecated raspi-gpio)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        return self._send_serial_command('pinctrl set 18 op dh')
    
    def led_off(self) -> bool:
        """
        Schaltet LED (GPIO 18) auf dem Pi aus
        Befehl: pinctrl set 18 op dl (modernes pinctrl, ersetzt deprecated raspi-gpio)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        return self._send_serial_command('pinctrl set 18 op dl')
    
    def start_recording(self, output_file: Optional[str] = None, is_baseline: bool = False, patient_id: Optional[str] = None) -> bool:
        """
        Startet Video-Aufnahme von der Kamera (mit 8-Sekunden-Pupillometrie-Protokoll)
        Videos werden lokal auf Windows PC gespeichert
        
        Args:
            output_file: Pfad zur Output-Datei (wird angefordert falls None - für Explorer-Dialog)
            is_baseline: True für Baseline-Aufnahme, False für normale Aufnahme
            patient_id: Patient-Kennung zur Speicherung in korrektem Folder
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.capture:
            logger.error("Keine Kamera verbunden - Aufnahme nicht möglich")
            return False
        
        if self.is_recording:
            logger.warning("Aufnahme läuft bereits")
            return False
        
        try:
            # Starte Recording im Hintergrund
            self.recording_file = output_file if output_file else "pending"  # Wird später abgefragt
            self.recording_is_baseline = is_baseline
            self.is_recording = True
            self.stop_recording_requested = False
            self.manual_stop = False
            self.recording_frames = []
            self.recording_start_time = time.time()
            
            baseline_label = "Baseline" if is_baseline else "Scan"
            logger.info(f"Aufnahme gestartet (8-Sekunden-Protokoll, {baseline_label})")
            
            # Starten Sie die Recording-Schleife
            self._recording_loop(is_baseline, patient_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Starten der Aufnahme: {e}")
            self.is_recording = False
            return False
    
    def _recording_loop(self, is_baseline: bool = False, patient_id: Optional[str] = None):
        """
        Interne Recording-Schleife (wird von start_recording() aufgerufen)
        - 8 Sekunden Recording
        - LED Stimulus bei 1.0-2.0s (BEIDE Baseline UND Normal! Zum Vergleichen nötig)
        - Baseline und Normal differ nur in Datenbankmarkierung, nicht in Aufnahme
        - Speichern zu MP4 am Ende mit Timestamp-Naming
        """
        DURATION = 8.0  # 8 Sekunden
        LED_ON_DELAY = 1.0  # LED AN nach 1s
        LED_ON_DURATION = 1.0  # LED bleibt 1.0s AN (1.0-2.0s total)
        
        logger.info(f"[_recording_loop] Starting: is_baseline={is_baseline}, patient_id={patient_id}")
        
        # Hole Frame-Rate und Auflösung
        fps = int(self.capture.get(cv2.CAP_PROP_FPS)) or 30  # Default 30 FPS
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"Recording mit {fps}FPS, {width}x{height}px, is_baseline={is_baseline}")
        
        # Starte Recording-Thread - PASS is_baseline UND patient_id EXPLICITLY
        recording_thread = threading.Thread(
            target=self._recording_thread,
            args=(DURATION, LED_ON_DELAY, LED_ON_DURATION, fps, width, height, is_baseline, patient_id)
        )
        recording_thread.daemon = False
        recording_thread.start()
        logger.info(f"[_recording_loop] Thread started")
    
    def _recording_thread(self, duration, led_on_delay, led_on_duration, fps, width, height, is_baseline: bool = False, patient_id: Optional[str] = None):
        """
        Thread für Video-Recording mit LED-Stimulus
        
        Args:
            duration: Aufnahmedauer in Sekunden
            led_on_delay: Verzögerung bis LED AN (1.0s)
            led_on_duration: Dauer LED AN (1.0s, also 1.0-2.0s total)
            is_baseline: True wenn Baseline-Aufnahme (GLEICHER LED-Stimulus wie Normal!)
            patient_id: Patient-Kennung für Folder-Speicherung
        """
        try:
            logger.info(f"[_recording_thread START] is_baseline={is_baseline}, patient_id={patient_id}, duration={duration}s")
            frame_count = 0
            start_time = time.time()
            led_activated = False
            
            # LED aus am Start
            self.led_off()
            logger.info(f"[_recording_thread] LED OFF at start, is_baseline={is_baseline}")
            
            while (time.time() - start_time) < duration and not self.stop_recording_requested:
                elapsed = time.time() - start_time
                
                # LED-Stimulus bei 1.0-2.0s für BEIDE Baseline und Normal
                # (Baseline BRAUCHT LED zum Vergleichen mit Normal!)
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
                    # Speichere Frame im RGB-Format (nicht BGR)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.recording_frames.append((frame_rgb, elapsed))
                    frame_count += 1
                    
                    # Logging alle 1s
                    if frame_count % (fps or 30) == 0:
                        logger.debug(f"Recording: {elapsed:.1f}s, {frame_count} frames")
                else:
                    logger.warning("Frame capture fehlgeschlagen")
                    time.sleep(0.01)  # Kurze Pause um CPU zu entlasten
            
            # LED am Ende ausschalten
            self.led_off()
            
            # Speichern Sie die aufgezeichneten Frames
            if self.stop_recording_requested:
                # Manuell gestoppt - wird vom UI-Dialog behandelt
                self.manual_stop = True
                logger.info(f"Recording manuell gestoppt nach {elapsed:.2f}s")
            else:
                # Auto-Stop nach 8s - speichern
                self.manual_stop = False
                logger.info(f"[_recording_thread] Auto-Stop nach {elapsed:.2f}s - speichere {len(self.recording_frames)} frames, is_baseline={is_baseline}, patient_id={patient_id}")
                result = self._save_recording_to_file(is_baseline=is_baseline, patient_id=patient_id)
                logger.info(f"[_recording_thread] Save result: {result}")
            
            self.is_recording = False  # CRITICAL: Always reset flag at end
            logger.info(f"[_recording_thread END] is_baseline={is_baseline}")
            
        except Exception as e:
            logger.error(f"Fehler in Recording-Thread: {e}")
            self.is_recording = False  # CRITICAL: Reset flag on error
            self.led_off()
    
    def _save_recording_to_file(self, output_file: Optional[str] = None, is_baseline: bool = False, patient_id: Optional[str] = None) -> Optional[str]:
        """
        Speichert aufgezeichnete Frames zu MP4-Datei mit Timestamp-basiertem Naming
        
        Naming Schema:
        - Normal: {unix_timestamp}_scan_{number}.mp4
        - Baseline: {unix_timestamp}_baseline.mp4
        
        Args:
            output_file: Zieldatei (wenn None, wird automatisch generiert)
            is_baseline: True wenn Baseline-Aufnahme
            patient_id: Patient-Kennung für Folder, z.B. "patient_001"
            
        Returns:
            Pfad zur gespeicherten Datei oder None bei Fehler
        """
        if not self.recording_frames:
            logger.error("Keine Frames zum Speichern vorhanden")
            return None
        
        try:
            # Erzeuge Output-Datei wenn nicht angegeben
            if not output_file or output_file == "pending":
                # Erstelle Patient-Folder wenn patient_id vorhanden
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
            
            # Hole erste Frame für Dimensionen
            first_frame = self.recording_frames[0][0]
            height, width = first_frame.shape[:2]
            
            # Definiere Codec und VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 20  # Recording-FPS (standardisiert)
            out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error(f"VideoWriter konnte nicht geöffnet werden: {output_file}")
                return None
            
            # Schreibe Frames
            for frame_rgb, elapsed in self.recording_frames:
                # Konvertiere RGB zurück zu BGR für OpenCV
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
            
            out.release()
            
            file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
            recording_type = "Baseline" if is_baseline else "Scan"
            logger.info(f"Recording gespeichert ({recording_type}): {output_file} ({file_size_mb:.2f}MB, {len(self.recording_frames)} frames)")
            
            self.recording_file = output_file
            self.recording_frames = []  # Leere den Buffer
            
            return output_file
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Aufnahme: {e}")
            return None
    
    def start_recording_with_pupillometry(self, duration: float = 8.0, 
                                         led_on_delay: float = 1.0,
                                         output_video: Optional[str] = None,
                                         is_baseline: bool = False,
                                         patient_id: Optional[str] = None) -> Optional[str]:
        """
        Startet Recording mit 8-Sekunden Pupillometrie-Protokoll
        
        Args:
            duration: Aufnahmedauer in Sekunden (default: 8.0)
            led_on_delay: Verzögerung bis LED AN in Sekunden (default: 1.0)
            output_video: Output MP4 Datei (wenn None, wird automatisch generiert)
            is_baseline: True für Baseline-Aufnahme (GLEICHER LED-Stimulus wie Normal!)
            patient_id: Patient-Kennung für Folder-Speicherung
            
        Returns:
            Pfad zur gespeicherten Datei oder None bei Fehler
        """
        if not self.capture:
            logger.error("Keine Kamera verbunden")
            return None
        
        if self.is_recording:
            logger.warning("Aufnahme läuft bereits")
            return None
        
        try:
            self.is_recording = True
            self.recording_is_baseline = is_baseline
            self.stop_recording_requested = False
            self.manual_stop = False
            self.recording_frames = []
            self.recording_start_time = time.time()
            
            # Hole Frame-Rate und Auflösung
            fps = int(self.capture.get(cv2.CAP_PROP_FPS)) or 30
            width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            recording_type = "Baseline" if is_baseline else "Pupillometrie"
            logger.info(f"Starte {recording_type}-Recording: {duration}s (patient_id={patient_id})")
            
            # Recording-Schleife
            LED_ON_DURATION = 1.0  # Korrekt: 1.0-2.0s (nicht 1.0-1.5s)
            frame_count = 0
            start_time = time.time()
            led_activated = False
            
            # LED aus am Start
            self.led_off()
            
            while (time.time() - start_time) < duration and not self.stop_recording_requested:
                elapsed = time.time() - start_time
                
                # LED-Stimulus bei 1.0-2.0s für BEIDE Baseline und Normal
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
            
            # LED am Ende ausschalten
            self.led_off()
            
            # Bestimme ob manuell oder auto gestoppt wurde
            if self.stop_recording_requested:
                self.manual_stop = True
                self.is_recording = False
                return None  # Wird vom UI behandelt
            else:
                # Auto-Stop - speichern
                result = self._save_recording_to_file(output_video, is_baseline=is_baseline, patient_id=patient_id)
                self.is_recording = False  # CRITICAL: Reset flag after save completes
                return result
        
        except Exception as e:
            logger.error(f"Fehler in {recording_type}-Recording: {e}")
            self.is_recording = False
            self.led_off()
            return None
    
    def stop_recording(self) -> bool:
        """
        Stoppt Video-Aufnahme (manuelles Stop vom Benutzer)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.is_recording:
            logger.warning("Keine Aufnahme aktiv")
            return False
        
        try:
            self.stop_recording_requested = True
            self.manual_stop = True
            logger.info("Recording Stop-Anfrage gestellt")
            
            # Gebe dem Thread Zeit zum Stoppen (max 1s)
            elapsed = 0
            while self.is_recording and elapsed < 1.0:
                time.sleep(0.01)
                elapsed += 0.01
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Stoppen der Aufnahme: {e}")
            self.is_recording = False
            return False
    
    def get_recorded_duration(self) -> float:
        """
        Gibt die bisherige Recording-Dauer in Sekunden zurück
        
        Returns:
            Dauer in Sekunden, oder 0 wenn nicht aufnehmend
        """
        if not self.is_recording or not self.recording_frames:
            return 0.0
        
        if not self.recording_frames:
            return 0.0
        
        # Die letzte Frame hat die aktuelle Elapsed-Zeit
        return self.recording_frames[-1][1]
    
    def get_recorded_frame_count(self) -> int:
        """
        Gibt die Anzahl aufgezeichneter Frames zurück
        
        Returns:
            Anzahl der Frames
        """
        return len(self.recording_frames)
    
    def delete_temp_recording(self) -> bool:
        """
        Löscht temporäre aufgezeichnete Frames
        (Wird aufgerufen wenn Benutzer Löschen auswählt)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            self.recording_frames = []
            self.recording_file = None
            self.is_recording = False
            logger.info("Temporäre Recording gelöscht")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Recording: {e}")
            return False
    
    def save_manual_recording(self, output_file: str) -> Optional[str]:
        """
        Speichert manuell gestoppte Recording in angegebene Datei
        
        Args:
            output_file: Zieldatei
            
        Returns:
            Pfad zur gespeicherten Datei oder None bei Fehler
        """
        return self._save_recording_to_file(output_file)
    
    def get_status(self) -> dict:
        """
        Gibt Status von Kamera, LED und Recording zurück
        
        Returns:
            Dictionary mit Status-Informationen
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
        """Cleanup: Trennt alle Verbindungen"""
        # Stoppe Recording falls aktiv
        if self.is_recording:
            self.stop_recording()
        
        # Trenne Kamera
        self.disconnect_camera()
        
        # Trenne Serial
        if self.serial_connection:
            try:
                # Schalte LED aus
                self.led_off()
                self.serial_connection.close()
                self.serial_connection = None
                logger.info("Serial-Verbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Serial-Verbindung: {e}")


# Beispiel / Test-Code
if __name__ == "__main__":
    import time
    
    print("\n" + "=" * 60)
    print("Camera Controller Test")
    print("=" * 60)
    
    # Controller initialisieren
    print("\n1. Initialisiere Camera Controller...")
    controller = CameraController(com_port='COM3')
    
    # Status anzeigen
    print("\n2. Zeige Status...")
    status = controller.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Verfügbare Kameras auflisten
    print("\n3. Suche USB-Kameras...")
    cameras = controller.list_cameras()
    if cameras:
        for camera in cameras:
            print(f"   {camera}")
    else:
        print("   Keine Kameras gefunden")
    
    # LED testen (wenn Serial-Verbindung besteht)
    print("\n4. LED Test...")
    print("   LED an...")
    controller.led_on()
    time.sleep(1)
    
    print("   LED aus...")
    controller.led_off()
    time.sleep(1)
    
    # Zur ersten verfügbaren Kamera verbinden
    if cameras:
        print("\n5. Verbinde zur Kamera...")
        if controller.connect_camera(0):
            print("   Verbunden!")
            
            # Frame-Test
            print("   Hole Frame...")
            frame = controller.get_frame()
            if frame:
                print(f"   Frame erhalten!")
            else:
                print("   Kein Frame")
            
            # Recording testen
            print("\n6. Recording Test...")
            if controller.start_recording():
                print("   Recording gestartet...")
                time.sleep(2)
                controller.stop_recording()
                print("   Recording gestoppt")
            
            # Cleanup
            print("\n7. Cleanup...")
            controller.disconnect()
            print("   Getrennt")
    else:
        print("\n5. Keine Kameras verfügbar - überspringe Kamera-Test")
        controller.disconnect()
    
    print("\n" + "=" * 60)
    print("Test beendet")
    print("=" * 60 + "\n")
