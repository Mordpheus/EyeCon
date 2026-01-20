#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/eyecon.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print('Tables in database:', tables)

# Check for old measurement table
if 'measurement' in tables:
    print('  Old measurement table exists - needs migration')
    cur.execute("SELECT COUNT(*) FROM measurement")
    count = cur.fetchone()[0]
    print(f'   Records: {count}')
else:
    print(' No old measurement table (database is fresh)')

# Check for new recording table
if 'recording' in tables:
    print(' New recording table exists')
    cur.execute("SELECT COUNT(*) FROM recording")
    count = cur.fetchone()[0]
    print(f'   Records: {count}')
else:
    print('  No recording table')

conn.close()
