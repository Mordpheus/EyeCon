"""
Test-Programm: Prüft ob der Raspberry Pi auf COM3 antwortet
"""

import serial
import time

def test_serial():
    print("=" * 50)
    print("Serial Connection Test")
    print("=" * 50)
    
    try:
        # Verbindung zu COM3 öffnen
        print("\nVerbinde zu COM3...")
        ser = serial.Serial('COM3', 9600, timeout=2)
        time.sleep(1)
        
        print("✅ Verbindung zu COM3 erfolgreich!")
        print(f"Port: {ser.port}")
        print(f"Baudrate: {ser.baudrate}")
        
        # Test 1: Schau ob was kommt
        print("\n--- Test 1: Auf Daten warten (3 Sekunden) ---")
        ser.timeout = 3
        data = ser.readline()
        
        if data:
            print(f"✅ Daten empfangen: {data}")
            print(f"   Dekodiert: {data.decode('utf-8', errors='ignore')}")
        else:
            print("❌ Keine Daten empfangen (Timeout)")
        
        # Test 2: Sende Befehl und warte auf Antwort
        print("\n--- Test 2: Sende Test-Befehl ---")
        test_commands = [
            b'HELLO\n',
            b'TEST\n',
            b'STATUS\n',
            b'LED_STATUS\n'
        ]
        
        for cmd in test_commands:
            print(f"Sende: {cmd.decode('utf-8', errors='ignore').strip()}")
            ser.write(cmd)
            time.sleep(0.5)
            
            response = ser.readline()
            if response:
                print(f"  → Antwort: {response.decode('utf-8', errors='ignore').strip()}")
            else:
                print(f"  → Keine Antwort")
        
        # Schließen
        ser.close()
        print("\n✅ Test abgeschlossen")
        
    except serial.SerialException as e:
        print(f"❌ Fehler: Kann nicht zu COM3 verbinden")
        print(f"   {e}")
        print("\n   Mögliche Gründe:")
        print("   - Pi ist nicht angeschlossen")
        print("   - Pi antwortet nicht (Firmware nicht installiert)")
        print("   - COM3 wird von anderem Programm benutzt")
    
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    test_serial()
