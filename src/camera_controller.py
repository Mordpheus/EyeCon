"""
Camera Controller für USB-Kameras und LED-Steuerung
Nutzt pyuvc für USB-Erkennung und gpiozero für GPIO LED-Steuerung
"""

import logging
from typing import Optional, List

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
    from gpiozero import LED
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False
    logger.warning("gpiozero nicht installiert. LED-Funktionalität deaktiviert.")


class CameraController:
    """
    Verwaltet USB-Kamera-Verbindung und LED-Steuerung
    Läuft auf Raspberry Pi mit angeschlossener USB-Kamera
    """
    
    def __init__(self, led_pin: int = 17):
        """
        Initialisiert Camera Controller
        
        Args:
            led_pin: GPIO Pin Nummer für LED (default: 17)
        """
        self.led = None
        self.current_camera = None
        self.capture = None
        
        # LED initialisieren
        if HAS_GPIOZERO:
            try:
                self.led = LED(led_pin)
                logger.info(f"LED initialisiert auf GPIO Pin {led_pin}")
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren der LED: {e}")
        else:
            logger.warning("gpiozero nicht verfügbar - LED-Steuerung nicht möglich")
    
    def list_cameras(self) -> List[str]:
        """
        Listet alle verfügbaren USB-Kameras auf
        
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
                info = f"[{i}] {device.name if hasattr(device, 'name') else str(device)}"
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
                self.disconnect()
            
            # Neue Verbindung
            self.capture = Capture(devices[device_index])
            self.current_camera = devices[device_index]
            
            logger.info(f"Verbunden zu Kamera: {self.current_camera}")
            self.led_on()  # LED anschalten bei Verbindung
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Verbinden zur Kamera: {e}")
            return False
    
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
        Schaltet LED ein
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.led:
            logger.warning("LED nicht verfügbar")
            return False
        
        try:
            self.led.on()
            logger.info("LED eingeschaltet")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Einschalten der LED: {e}")
            return False
    
    def led_off(self) -> bool:
        """
        Schaltet LED aus
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.led:
            logger.warning("LED nicht verfügbar")
            return False
        
        try:
            self.led.off()
            logger.info("LED ausgeschaltet")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Ausschalten der LED: {e}")
            return False
    
    def led_blink(self, on_time: float = 1, off_time: float = 1, n: Optional[int] = None) -> bool:
        """
        Lässt LED blinken
        
        Args:
            on_time: Sekunden LED an
            off_time: Sekunden LED aus
            n: Anzahl Blinks (None = endlos)
        
        Returns:
            True wenn erfolgreich, False sonst
        """
        if not self.led:
            logger.warning("LED nicht verfügbar")
            return False
        
        try:
            self.led.blink(on_time=on_time, off_time=off_time, n=n, background=True)
            logger.info(f"LED blinkt (on={on_time}s, off={off_time}s)")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Blinken der LED: {e}")
            return False
    
    def disconnect(self):
        """Trennt Kameraverbindung und schaltet LED aus"""
        if self.capture:
            try:
                self.capture.close()
                self.capture = None
                logger.info("Kamera-Verbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Kamera: {e}")
        
        self.led_off()
    
    def get_status(self) -> dict:
        """
        Gibt Status von Kamera und LED zurück
        
        Returns:
            Dictionary mit Status-Informationen
        """
        return {
            'camera_connected': self.capture is not None,
            'current_camera': str(self.current_camera) if self.current_camera else None,
            'led_available': self.led is not None,
            'led_is_on': self.led.is_lit if self.led else None,
            'cameras_available': len(self.list_cameras()),
            'has_uvc': HAS_UVC,
            'has_gpiozero': HAS_GPIOZERO
        }


# Beispiel / Test-Code
if __name__ == "__main__":
    import time
    
    # Controller initialisieren
    controller = CameraController()
    
    # Status anzeigen
    print("\n=== Camera Controller Status ===")
    status = controller.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    # Verfügbare Kameras auflisten
    print("\n=== Verfügbare Kameras ===")
    cameras = controller.list_cameras()
    for camera in cameras:
        print(f"  {camera}")
    
    # LED testen
    print("\n=== LED Test ===")
    print("LED an...")
    controller.led_on()
    time.sleep(1)
    
    print("LED aus...")
    controller.led_off()
    time.sleep(1)
    
    print("LED blinkt...")
    controller.led_blink(on_time=0.5, off_time=0.5, n=3)
    time.sleep(4)
    
    # Zur ersten verfügbaren Kamera verbinden
    if cameras:
        print("\n=== Kamera-Verbindung ===")
        if controller.connect_camera(0):
            print("Verbunden!")
            
            # Frame-Test
            frame = controller.get_frame()
            if frame:
                print(f"Frame erhalten: {frame}")
            
            # Cleanup
            controller.disconnect()
            print("Getrennt")
    else:
        print("\nKeine Kameras verfügbar - überspringe Kamera-Test")
    
    print("\n=== Fertig ===")
