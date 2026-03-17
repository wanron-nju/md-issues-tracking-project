import sqlite3
import os
db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT id, store, fix_photo FROM issues')
print(cursor.fetchall())
