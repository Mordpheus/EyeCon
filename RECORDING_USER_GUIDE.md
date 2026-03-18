# Recording-Funktion - Benutzerhandbuch & FAQ

## Verwendung

### 1. Recording Starten
1. Klicke auf **"🔴 REC STARTEN"** Button
2. Die App zeigt: **"🔴 RECORDING: 8-Sekunden-Protokoll läuft..."**
3. LED wird automatisch gesteuert:
   - 0.0-1.0s: **OFF** (Baseline)
   - 1.0-1.5s: **ON** (Kontraktion/Stimulus)
   - 1.5-8.0s: **OFF** (Recovery)
4. Nach **8 Sekunden** stoppt die Aufnahme automatisch
5. Die Datei wird automatisch gespeichert:
   - Pfad: `data/recordings/recording_YYYY-MM-DD_HH-MM-SS.mp4`
   - Format: MP4 (H.264, 20 FPS, 640x480px)
6. Die App zeigt: **"✓ Recording erfolgreich gespeichert: recording_XXX.mp4 (1.23MB)"**

### 2. Recording Vorzeitig Stoppen (manuell)
**ACHTUNG:** Das 8-Sekunden-Protokoll ist erforderlich für gültige Messungen!

1. Klicke auf **"⏹ REC STOPP"** Button vor 8 Sekunden
2. Die App zeigt einen Dialog:
   ```
   ⚠️ Unvollständiges Recording
   Recording ist nur X.X Sekunden lang.
   Das Protokoll erfordert 8 Sekunden für gültige Messungen.
   Möchten Sie diese Datei speichern oder verwerfen?
   ```
3. Wähle eine Option:

#### Option A: **"🗑️ Verwerfen"** (Empfohlen für ungültige Messungen)
- Die Aufnahme wird GELÖSCHT
- KEINE Datei auf der Festplatte
- Ideal wenn Benutzer blinzelt oder sich zu viel bewegt

#### Option B: **"💾 Speichern"** (Falls Benutzer Recording trotzdem speichern möchte)
- Öffnet Windows Explorer-Dialog
- Standard-Pfad: `data/recordings/`
- Du kannst einen beliebigen Dateinamen eingeben
- Datei wird gespeichert als MP4 (z.B. `meine_messung.mp4`)

---

## Häufig Gestellte Fragen

### F: Was passiert wenn die Kamera während Recording getrennt wird?
A: Die Recording-Schleife stoppt mit einem Error-Log. Der Buffer wird geleert und "✗ Fehler beim Recording!" wird angezeigt.

### F: Kann ich mehrere Recordings hintereinander machen?
A: Ja! Nach jedem Recording können Sie sofort "REC STARTEN" klicken für die nächste Aufnahme. Die Dateien werden automatisch mit Timestamps unterschieden.

### F: Wie groß sind die MP4-Dateien?
A: Typischerweise **1.2-1.5 MB** für 8 Sekunden @ 20 FPS, 640x480px. Das hängt von der Bewegung ab.

### F: Kann ich die Aufnahmen abspielen?
A: Ja! Die MP4-Dateien sind Standard-Videos. Du kannst sie mit Windows Media Player, VLC, oder jedem Video-Player abspielen.

### F: Was ist wenn ich versehentlich auf "Verwerfen" klicke?
A: Die Aufnahme ist GELÖSCHT und kann nicht wiederhergestellt werden. Die Messung muss wiederholt werden.

### F: Wo werden die Dateien gespeichert?
A: 
- Auto-Speicher: `c:\Uni\EyeCon\data\recordings\recording_YYYY-MM-DD_HH-MM-SS.mp4`
- Manuell mit Explorer: Wo du im Dialog wählst (Standard: `c:\Uni\EyeCon\data\recordings\`)

### F: Wie lange dauert das Speichern?
A: Das Speichern dauert **1-2 Sekunden** nach Auto-Stop. Die Frames werden zu H.264-Video enkodiert.

### F: Kann ich den Dateinamen anpassen?
A: Ja! Nur wenn du **"💾 Speichern"** wählst bei vorzeitigem Stop. Dann können Sie einen beliebigen Namen eingeben.

### F: Was ist mit der LED-Steuerung?
A: Die LED wird **automatisch** nach dem Protokoll gesteuert:
- Sie müssen sich um Timing NICHT kümmern
- LED schaltet automatisch ON/OFF nach Protokoll
- Falls kein Raspberry Pi verbunden ist (z.B. Windows): LED-Befehle sind No-Op

### F: Kann ich die 8 Sekunden verkürzen?
A: Nur für Testing. Im Production-Mode ist 8 Sekunden fix. Falls nötig, können Sie den Code ändern:
```python
duration=8.0  # Ändern Sie diese Zeile in start_recording_with_pupillometry()
```

### F: Was passiert mit den Aufnahmen später?
A: Die Dateien bleiben in `data/recordings/` erhalten. Sie können später:
- In andere Studien-Software importiert werden
- Mit anderen Analyse-Tools verarbeitet werden
- Backup auf USB/Cloud gespeichert werden

---

## Fehlerbehebung

### Problem: "✗ Fehler: Keine Kamera verbunden!"
**Ursache**: Kamera wurde vor START REC nicht gescannt
**Lösung**:
1. Gehe zum **"Kamera"** Tab
2. Klicke auf **"KAMERAS SCANNEN"**
3. Warte bis Kamera erkannt wird (grüne Checkmark)
4. Gehe zurück zum **"Recording"** Tab
5. Versuche erneut **"REC STARTEN"**

### Problem: "✗ Fehler beim Recording!"
**Ursache**: Kamera wurde während Recording getrennt
**Lösung**:
1. Überprüfe USB-Kabel-Verbindung
2. Starten Sie die App neu
3. Scannen Sie Kamera erneut
4. Versuchen Sie Recording erneut

### Problem: Dialog erscheint nicht bei vorzeitigem Stop
**Ursache**: Zu schnell auf Stop geklickt (vor <1s Erfassungs-Zeit)
**Lösung**:
1. Versuchen Sie erneut Recording
2. Warten Sie mindestens 1 Sekunde vor Stop

### Problem: Datei wird nicht im Explorer-Dialog angezeigt
**Ursache**: Falsche Eingabe des Dateinamens
**Lösung**:
1. Dateiname muss mit `.mp4` enden
2. Beispiel: `patient_001.mp4` ✓
3. Nicht: `patient_001` (fehlt .mp4 Erweiterung)

### Problem: "Datei schon vorhanden" Fehlermeldung
**Ursache**: Eine Datei mit gleichem Namen existiert bereits
**Lösung**:
1. Ändern Sie den Dateinamen
2. Beispiel: `patient_001_retry.mp4`
3. Oder: `patient_001_v2.mp4`
4. Der Dialog fragt: "Überschreiben?" - Klicken Sie "Nein" und wählen anderen Namen

---

## LED-Stimulus Timing (Wissenschaftliche Info)

```
ZEIT:        0s         1.0s       1.5s        8.0s
             |          |           |           |
STATUS:     [BASELINE] [STIMULUS]  [RECOVERY]
             |          |           |
LED:        OFF   →    ON   →      OFF
            ◯         ●         ◯
Pupille:    Normal   Kontraktion  Erholung
```

### Warum dieses Timing?
- **0-1.0s Baseline**: Pupille auf Ruhe-Größe stabilisieren
- **1.0-1.5s LED ON**: Helles Licht stimuliert Pupillenreflex (Kontraktion)
- **1.5-8.0s Recovery**: Pupille kehrt zur Normalform zurück

Diese Zeiten sind in der ophthalmologischen Literatur standardisiert.

---

## Beispiel-Workflow für Patientenmessung

```
1. Patient sitzt vor Kamera
2. Augen ruhen sich 30 Sekunden aus
3. Öffne EyeCon App
4. Wechsle zum "Recording" Tab
5. Klicke "🔴 REC STARTEN"
6. Bild zeigt: "🔴 RECORDING: 8-Sekunden-Protokoll läuft..."
7. Sage Patient: "Schauen Sie auf die LED, blinzeln Sie nicht"
8. Warte 8 Sekunden (LED schaltet sich automatisch um)
9. Nach 8s zeigt App: "✓ Recording erfolgreich gespeichert"
10. Speichere Patient-ID im Dateinamen: "patient_001_messung_1.mp4"
11. Wiederhole für weitere Messungen bei gleichen Patient (2-3 mal)
```

---

## Technische Spezifikationen

| Eigenschaft | Wert |
|------------|------|
| **Aufnahmedauer** | 8 Sekunden (fix) |
| **Auflösung** | 640 × 480 Pixel |
| **Bildhäufigkeit** | 30 FPS (Capture), 20 FPS (Export) |
| **Videocodec** | H.264 (mp4v) |
| **Audio** | Keine |
| **Dateigröße** | ~1.2-1.5 MB pro Aufnahme |
| **LED Stimulus** | 1.0-1.5s (500ms ON) |
| **LED Wavelength** | IR (880nm) Falls Raspberry Pi konfiguriert |
| **Speicherort** | `data/recordings/` |
| **Dateiformat** | MPEG-4 (.mp4) |

---

## Datenschutz & Speicherung

- Alle Aufnahmen werden LOKAL auf Ihrem Computer gespeichert
- KEINE Cloud-Übertragung
- KEINE automatische Sicherung
- **Sie sind verantwortlich für Backup!**
- Empfehlung: Tägliche Backups auf externe Festplatte

---

**Version**: 1.0 - February 2, 2026
