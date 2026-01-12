import sqlite3
import json

db_path = r"C:\Users\cmbwa\Downloads\TBI_Headset_Export_1756736359460 2\database"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Alle Tabellen auslesen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("=" * 60)
    print("DATENBANK-STRUKTUR")
    print("=" * 60)
    
    for table in tables:
        print(f"\n### Tabelle: {table}")
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        for col in columns:
            cid, name, type_, notnull, dflt_value, pk = col
            print(f"  - {name}: {type_} (PK: {pk}, NOT NULL: {notnull})")
        
        # Anzahl Zeilen
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"  Zeilen: {count}")
        
        # Erste Zeile als Beispiel
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 1;")
            first_row = cursor.fetchone()
            print(f"  Beispiel: {first_row}")
    
    conn.close()
    print("\n" + "=" * 60)

except Exception as e:
    print(f"Fehler: {e}")
