#!/usr/bin/env python3
"""
Analyze TBI_Headset Database Schema
Reads the patient_database.db and prints table structure
"""

import sqlite3
from pathlib import Path

db_path = Path(r'c:\Users\cmbwa\Downloads\TBI_Headset_Export_1756736359460 2\database\patient_database.db')

if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("=" * 60)
print("TBI_HEADSET DATABASE SCHEMA")
print("=" * 60)

for table in tables:
    table_name = table[0]
    print(f"\nTABLE: {table_name}")
    print("-" * 60)
    
    # Get columns for this table
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = cur.fetchall()
    
    for col in columns:
        col_id, col_name, col_type, not_null, default, pk = col
        nullable = "NOT NULL" if not_null else "NULLABLE"
        pk_str = "PRIMARY KEY" if pk else ""
        print(f"  {col_name:<30} {col_type:<15} {nullable:<10} {pk_str}")
    
    # Sample data
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    print(f"\nRows: {count}")

conn.close()
print("\n" + "=" * 60)
