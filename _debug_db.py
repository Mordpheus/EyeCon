import sqlite3
conn = sqlite3.connect('data/eyecon.db')
conn.row_factory = sqlite3.Row

# First check what tables exist
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t["name"] for t in tables])
print()

patients = conn.execute("SELECT * FROM patient WHERE name LIKE ?", ('%Schepelmann%',)).fetchall()
for p in patients:
    pid = p["id"]
    pname = p["name"]
    print(f"Patient: id={pid}, name={pname}")
    recs = conn.execute("SELECT id, date, baseline FROM recording WHERE patient_id = ?", (pid,)).fetchall()
    for r in recs:
        rid = r["id"]
        rdate = r["date"]
        bl = "BASELINE" if r["baseline"] == 1 else "scan"
        print(f"  Recording: id={rid}, date={rdate}, {bl}")

# Also check patient 4064
print()
print("=== Patient 4064 (eigene Aufnahme) ===")
patients2 = conn.execute("SELECT * FROM patient WHERE id LIKE ?", ('%4064%',)).fetchall()
for p in patients2:
    pid = p["id"]
    pname = p["name"]
    print(f"Patient: id={pid}, name={pname}")
    recs = conn.execute("SELECT id, date, baseline FROM recording WHERE patient_id = ?", (pid,)).fetchall()
    for r in recs:
        rid = r["id"]
        rdate = r["date"]
        bl = "BASELINE" if r["baseline"] == 1 else "scan"
        print(f"  Recording: id={rid}, date={rdate}, {bl}")

conn.close()
