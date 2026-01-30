"""
Camera Controller für USB-Kameras und LED-Steuerung über Raspberry Pi
Architektur:
- USB-Kamera: Wird vom Pi als uvc-gadget exportiert, pyuvc erkennt sie
- LED: Steuerung über Serial-Befehle an den Pi (raspi-gpio)
- Video: Speichern lokal auf Windows PC
- Kommunikation: Serial über COM-Port
"""

import logging
import serial
import time
from typing import Optional, List
from pathlib import Path

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import mit Error-Handling für fehlende Libraries
try:
    from uvc import get_devices, Capture
    HAS_UVC = True
except ImportError:
    HAS_UVC = False
    logger.warning("pyuvc nicht installiert. USB-Kamera-Funktionalität deaktiviert.")

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
    - Kamera: USB-Gerät (vom Pi als uvc-gadget exportiert)
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
        self.current_camera = None
        self.capture = None
        
        # Video-Aufnahme
        self.is_recording = False
        self.recording_file = None
        
        # Versuche Serial-Verbindung
        self._connect_serial()
    
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
        Sende Befehl zum Pi über Serial
        
        Args:
            command: Shell-Befehl (z.B. 'raspi-gpio set 18 op dh')
        
        Returns:
            True wenn erfolgreich gesendet
        """
        if not self.serial_connection:
            logger.warning("Keine Serial-Verbindung - Befehl nicht gesendet")
            return False
        
        try:
            # Sende Befehl mit Newline
            cmd_bytes = (command + '\n').encode('utf-8')
            self.serial_connection.write(cmd_bytes)
            logger.debug(f"Befehl gesendet: {command}")
            
            # Warte auf kurze Verarbeitung
            time.sleep(0.2)
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Senden des Befehls: {e}")
            return False
    
    def list_cameras(self) -> List[str]:
        """
        Listet alle verfügbaren USB-Kameras auf
        Die Kamera vom Pi sollte hier auftauchen als uvc-Gerät
        
        Returns:
            List von Kamera-Geräten
        """
        if not HAS_UVC:
            logger.warning("pyuvc nicht verfügbar - Kamera-Erkennung nicht möglich")
            return []
        
        try:
            devices = get_devices()
            camera_info = []
            
            for i, device in enumerate(devices):
                # Versuche Namen zu extrahieren
                try:
                    name = device.name if hasattr(device, 'name') else str(device)
                except:
                    name = str(device)
                
                info = f"[{i}] {name}"
                camera_info.append(info)
                logger.info(f"Kamera gefunden: {info}")
            
            return camera_info if camera_info else []
            
        except Exception as e:
            logger.error(f"Fehler beim Erkennen von Kameras: {e}")
            return []
    
    def connect_camera(self, device_index: int = 0) -> bool:
        """
        Verbindet zu einer USB-Kamera
        
        Args:
            device_index: Index der Kamera (default: 0 = erste Kamera)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not HAS_UVC:
            logger.error("pyuvc nicht verfügbar - Kann nicht zu Kamera verbinden")
            return False
        
        try:
            devices = get_devices()
            
            if not devices:
                logger.error("Keine USB-Kameras gefunden")
                return False
            
            if device_index >= len(devices):
                logger.error(f"Kamera-Index {device_index} außerhalb des Bereichs (max: {len(devices)-1})")
                return False
            
            # Bestehende Verbindung schließen
            if self.capture:
                self.disconnect_camera()
            
            # Neue Verbindung
            self.capture = Capture(devices[device_index])
            self.current_camera = devices[device_index]
            
            logger.info(f"Verbunden zu Kamera: {self.current_camera}")
            self.led_on()  # LED anschalten bei Verbindung
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Verbinden zur Kamera: {e}")
            return False
    
    def disconnect_camera(self):
        """Trennt Kameraverbindung"""
        if self.capture:
            try:
                self.capture.close()
                self.capture = None
                logger.info("Kamera-Verbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Kamera: {e}")
    
    def get_frame(self):
        """
        Holt einen Video-Frame von der verbundenen Kamera
        
        Returns:
            Frame-Objekt oder None bei Fehler
        """
        if not self.capture:
            logger.debug("Keine Kamera verbunden")
            return None
        
        try:
            frame = self.capture.get_frame()
            return frame
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Frames: {e}")
            return None
    
    def led_on(self) -> bool:
        """
        Schaltet LED (GPIO 18) auf dem Pi ein
        Befehl: raspi-gpio set 18 op dh (dh = digital high)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        return self._send_serial_command('raspi-gpio set 18 op dh')
    
    def led_off(self) -> bool:
        """
        Schaltet LED (GPIO 18) auf dem Pi aus
        Befehl: raspi-gpio set 18 op dl (dl = digital low)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        return self._send_serial_command('raspi-gpio set 18 op dl')
    
    def start_recording(self, output_file: Optional[str] = None) -> bool:
        """
        Startet Video-Aufnahme von der Kamera
        Videos werden lokal auf Windows PC gespeichert
        
        Args:
            output_file: Pfad zur Output-Datei (default: data/recordings/recording_<timestamp>.mp4)
        
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
            # Erzeuge Output-Datei wenn nicht angegeben
            if not output_file:
                recordings_dir = Path("data/recordings")
                recordings_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
                output_file = str(recordings_dir / f"recording_{timestamp}.mp4")
            
            self.recording_file = output_file
            self.is_recording = True
            
            logger.info(f"Aufnahme gestartet: {output_file}")
            
            # TODO: Implementiere eigentliches Video-Recording mit OpenCV/pyuvc
            # Für jetzt: Platzhalter
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Starten der Aufnahme: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self) -> bool:
        """
        Stoppt Video-Aufnahme
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.is_recording:
            logger.warning("Keine Aufnahme aktiv")
            return False
        
        try:
            self.is_recording = False
            logger.info(f"Aufnahme gestoppt: {self.recording_file}")
            
            # TODO: Implementiere Speichern und Finalisieren der Datei
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Stoppen der Aufnahme: {e}")
            return False
    
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
            'current_camera': str(self.current_camera) if self.current_camera else None,
            'is_recording': self.is_recording,
            'recording_file': self.recording_file,
            'cameras_available': len(self.list_cameras()),
            'has_uvc': HAS_UVC,
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
            print("   ✅ Verbunden!")
            
            # Frame-Test
            print("   Hole Frame...")
            frame = controller.get_frame()
            if frame:
                print(f"   ✅ Frame erhalten!")
            else:
                print("   ❌ Kein Frame")
            
            # Recording testen
            print("\n6. Recording Test...")
            if controller.start_recording():
                print("   Recording gestartet...")
                time.sleep(2)
                controller.stop_recording()
                print("   ✅ Recording gestoppt")
            
            # Cleanup
            print("\n7. Cleanup...")
            controller.disconnect()
            print("   ✅ Getrennt")
    else:
        print("\n5. Keine Kameras verfügbar - überspringe Kamera-Test")
        controller.disconnect()
    
    print("\n" + "=" * 60)
    print("Test beendet")
    print("=" * 60 + "\n")
