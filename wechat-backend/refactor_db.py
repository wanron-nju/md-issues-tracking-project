"""
Database Refactor Script
========================
1. Remove "submit_date" column
2. Keep "submitted_at" column (already exists)
3. Remove "created_at" column

This will clean up duplicate/redundant fields in the issues table.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current schema
cursor.execute("PRAGMA table_info(issues)")
columns_before = {col[1]: col[2] for col in cursor.fetchall()}
print("=== BEFORE REFACTOR ===")
print(f"Columns: {list(columns_before.keys())}")

# Get data count
cursor.execute("SELECT COUNT(*) FROM issues")
count = cursor.fetchone()[0]
print(f"Records: {count}")

# SQLite doesn't support DROP COLUMN directly in some versions
# We need to recreate the table

print("\n=== REFACTORING DATABASE ===")

# Step 1: Create new table without submit_date and created_at
cursor.execute("""
CREATE TABLE IF NOT EXISTS issues_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_at DATETIME NOT NULL,
    store VARCHAR NOT NULL,
    content TEXT NOT NULL,
    issue_photo VARCHAR NOT NULL,
    fix_photo VARCHAR,
    fix_date DATETIME,
    status VARCHAR NOT NULL DEFAULT 'pending'
)
""")

# Step 2: Copy data from old table to new table
# submitted_at already has the correct data
cursor.execute("""
INSERT INTO issues_new (id, submitted_at, store, content, issue_photo, fix_photo, fix_date, status)
SELECT id, submitted_at, store, content, issue_photo, fix_photo, fix_date, status
FROM issues
""")

# Step 3: Drop old table
cursor.execute("DROP TABLE issues")

# Step 4: Rename new table to original name
cursor.execute("ALTER TABLE issues_new RENAME TO issues")

conn.commit()

# Verify result
cursor.execute("PRAGMA table_info(issues)")
columns_after = {col[1]: col[2] for col in cursor.fetchall()}
print("\n=== AFTER REFACTOR ===")
print(f"Columns: {list(columns_after.keys())}")

# Show sample data
cursor.execute("SELECT id, submitted_at, store, content, fix_photo, fix_date, status FROM issues LIMIT 3")
print("\nSample data:")
for row in cursor.fetchall():
    print(f"  id={row[0]}, submitted_at={row[1]}, store={row[2]}, content={row[3][:20]}...")

conn.close()
print("\n✅ Database refactor completed!")
