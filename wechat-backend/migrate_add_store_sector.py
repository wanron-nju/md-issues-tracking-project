"""
Migration script to add store_sector column to the issues table.
This is a one-time migration that adds the nullable store_sector column.
"""
import sqlite3
import os
from pathlib import Path

def migrate():
    # Database is in ./data/ folder relative to the backend directory
    backend_dir = Path(__file__).resolve().parent
    db_path = backend_dir / "data" / "issues.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}. No migration needed.")
        return
    
    # Connect to the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(issues)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "store_sector" in columns:
        print("Column 'store_sector' already exists. No migration needed.")
        conn.close()
        return
    
    # Add the store_sector column (nullable, no default needed)
    print("Adding 'store_sector' column to 'issues' table...")
    cursor.execute("ALTER TABLE issues ADD COLUMN store_sector VARCHAR;")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
