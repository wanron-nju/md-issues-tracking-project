import sqlite3
import os

def fetch_absolute_all_fields():
    # Database path relative to your project structure
    db_path = os.path.join('wechat-backend', 'data', 'issues.db')
    
    if not os.path.exists(db_path):
        # Fallback for if you are running from inside the wechat-backend folder
        db_path = os.path.join('data', 'issues.db')

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM issues")
        rows = cursor.fetchall()
        
        if not rows:
            print("ℹ️ No records found.")
            return

        print(f"--- Printing ALL fields for {len(rows)} records ---\n")
        
        for row in rows:
            # Convert to dict to ensure we see every key-value pair
            data = dict(row)
            print(f"ENTRY [ID: {data['id']}]")
            
            # Iterate through every column in the schema
            for key, value in data.items():
                # Formatting for alignment
                print(f"  {key:<15}: {value}")
            
            print("-" * 40)
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fetch_absolute_all_fields()