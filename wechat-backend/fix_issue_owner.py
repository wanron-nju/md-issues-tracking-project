import sqlite3
conn = sqlite3.connect('d:/projects/md-issues-tracking-project/wechat-backend/data/issues.db')
conn.execute("UPDATE issues SET issue_owner = '门店' WHERE issue_owner IS NULL")
conn.commit()
print("Updated", conn.total_changes, "records")
conn.close()
