import sqlite3
import os
from datetime import datetime

db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')

# Connect and check current schema
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(issues)")
columns = cursor.fetchall()
print("Current columns in issues table:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# Get current data
cursor.execute("SELECT * FROM issues")
rows = cursor.fetchall()
print(f"\nCurrent data ({len(rows)} rows):")
for row in rows:
    print(f"  {row}")

conn.close()
