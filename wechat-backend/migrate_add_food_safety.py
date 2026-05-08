"""
Migration script to add is_food_safety column to the issues table.
This is a one-time migration that adds the non-nullable is_food_safety column with default False.
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
    
    if "is_food_safety" in columns:
        print("Column 'is_food_safety' already exists. No migration needed.")
        conn.close()
        return
    
    # Add the is_food_safety column (BOOLEAN NOT NULL DEFAULT 0)
    print("Adding 'is_food_safety' column to 'issues' table...")
    cursor.execute("ALTER TABLE issues ADD COLUMN is_food_safety BOOLEAN NOT NULL DEFAULT 0;")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()