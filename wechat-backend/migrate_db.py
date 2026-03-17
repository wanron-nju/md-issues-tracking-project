import sqlite3
import os
from datetime import datetime

db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if submitted_at column already exists
cursor.execute("PRAGMA table_info(issues)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Current columns: {columns}")

if 'submitted_at' not in columns:
    print("\nAdding submitted_at column...")
    # Add the new submitted_at column
    cursor.execute("ALTER TABLE issues ADD COLUMN submitted_at DATETIME")
    
    # Migrate data from submit_date to submitted_at
    # Parse submit_date and combine with time from created_at
    cursor.execute("SELECT id, submit_date, created_at FROM issues")
    rows = cursor.fetchall()
    
    for row in rows:
        issue_id, submit_date, created_at = row
        try:
            # Parse the submit_date (format: YYYYMMDD or YYYY-MM-DD)
            submit_date = submit_date.strip()
            if len(submit_date) == 8:  # YYYYMMDD format
                date_str = f"{submit_date[:4]}-{submit_date[4:6]}-{submit_date[6:8]}"
            else:
                date_str = submit_date
            
            # Get time from created_at
            if created_at and len(str(created_at)) >= 19:
                time_str = str(created_at)[11:19]
                submitted_at = f"{date_str} {time_str}"
            else:
                # Use current time if created_at is not available
                submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "UPDATE issues SET submitted_at = ? WHERE id = ?",
                (submitted_at, issue_id)
            )
            print(f"  Updated issue {issue_id}: submit_date={submit_date} -> submitted_at={submitted_at}")
        except Exception as e:
            print(f"  Error updating issue {issue_id}: {e}")
    
    conn.commit()
    print("Migration completed!")
else:
    print("\nColumn submitted_at already exists, no migration needed.")

# Verify the result
cursor.execute("PRAGMA table_info(issues)")
columns = cursor.fetchall()
print("\nUpdated columns:")
for col in columns:
    print(f"  {col[1]}: {col[2]}")

cursor.execute("SELECT id, submit_date, submitted_at, created_at FROM issues")
print("\nData after migration:")
for row in cursor.fetchall():
    print(f"  id={row[0]}, submit_date={row[1]}, submitted_at={row[2]}, created_at={row[3]}")

conn.close()
