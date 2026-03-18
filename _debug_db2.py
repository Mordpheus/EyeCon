import sqlite3
conn = sqlite3.connect('data/eyecon.db')
conn.row_factory = sqlite3.Row

# Marcel Schepelmann
patients = conn.execute("SELECT * FROM patient WHERE last_name LIKE '%Schepelmann%'").fetchall()
for p in patients:
    pid = p["id"]
    print(f"Patient: id={pid}, first={p['first_name']}, last={p['last_name']}")
    recs = conn.execute("SELECT id, date, baseline FROM recording WHERE patientId = ?", (pid,)).fetchall()
    for r in recs:
        bl = "BASELINE" if r["baseline"] == 1 else "scan"
        print(f"  {bl}: id={r['id']}, date={r['date']}")

# Patient 4064 (eigene Aufnahme)
print()
print("=== Patient 4064 ===")
patients2 = conn.execute("SELECT * FROM patient WHERE id LIKE '%4064%'").fetchall()
for p in patients2:
    pid = p["id"]
    print(f"Patient: id={pid}, first={p['first_name']}, last={p['last_name']}")
    recs = conn.execute("SELECT id, date, baseline FROM recording WHERE patientId = ?", (pid,)).fetchall()
    for r in recs:
        bl = "BASELINE" if r["baseline"] == 1 else "scan"
        print(f"  {bl}: id={r['id']}, date={r['date']}")

conn.close()
