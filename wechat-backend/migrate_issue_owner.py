"""
Migration script to add issue_owner and fix_comments columns to the issues table.

This is a one-time migration script that:
1. Adds issue_owner VARCHAR NOT NULL column with default value "门店"
2. Adds fix_comments TEXT nullable column
3. Sets issue_owner to "门店" for all existing records
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current columns
cursor.execute("PRAGMA table_info(issues)")
columns = {col[1]: col for col in cursor.fetchall()}
print(f"Current columns: {list(columns.keys())}")

# Add issue_owner column if not exists
if 'issue_owner' not in columns:
    print("\nAdding issue_owner column...")
    # SQLite: Add column as nullable first
    cursor.execute("ALTER TABLE issues ADD COLUMN issue_owner VARCHAR DEFAULT '门店'")
    
    # Update all existing records to have "门店" as issue_owner
    cursor.execute("UPDATE issues SET issue_owner = '门店' WHERE issue_owner IS NULL")
    print("  Set issue_owner = '门店' for all existing records")
    
    conn.commit()
    print("  Migration completed for issue_owner!")
else:
    print("\nColumn issue_owner already exists.")

# Add fix_comments column if not exists
if 'fix_comments' not in columns:
    print("\nAdding fix_comments column...")
    cursor.execute("ALTER TABLE issues ADD COLUMN fix_comments TEXT")
    conn.commit()
    print("  Migration completed for fix_comments!")
else:
    print("\nColumn fix_comments already exists.")

# Verify the result
cursor.execute("PRAGMA table_info(issues)")
columns = cursor.fetchall()
print("\n=== Updated columns ===")
for col in columns:
    print(f"  {col[1]}: {col[2]} (nullable={not col[3]}, default={col[4]})")

# Show sample data
cursor.execute("SELECT id, store, issue_owner, status FROM issues LIMIT 5")
print("\n=== Sample data ===")
for row in cursor.fetchall():
    print(f"  id={row[0]}, store={row[1]}, issue_owner={row[2]}, status={row[3]}")

conn.close()
print("\n=== Migration completed successfully! ===")
