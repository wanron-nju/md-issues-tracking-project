# 本生产数据库初始化脚本可以在完全重新创建数据库表结构（生产升级时可完全抛弃旧数据）的情形下直接执行

import sqlite3
import os

# 数据库路径保持一致
db_path = os.path.join(os.path.dirname(__file__), 'data', 'issues.db')

# 如果 data 文件夹不存在则创建
os.makedirs(os.path.dirname(db_path), exist_ok=True)

def init_db():
    print(f"正在初始化生产环境数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 直接创建符合 Phase 3 标准的 10 列架构表
    # 包含了 issue_owner 和 fix_comments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        submitted_at DATETIME NOT NULL,
        store VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        content TEXT NOT NULL,
        issue_photo VARCHAR NOT NULL,
        issue_owner VARCHAR NOT NULL DEFAULT '<由营运组分派>',
        fix_comments TEXT,
        fix_photo VARCHAR,
        fix_date DATETIME
    )
    """)

    conn.commit()

    # 验证表结构
    cursor.execute("PRAGMA table_info(issues)")
    cols = cursor.fetchall()
    print("\n✅ 数据库初始化成功！当前架构：")
    for col in cols:
        print(f" - {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    # 运行前检查：如果文件已存在，提醒用户
    if os.path.exists(db_path):
        print(f"⚠️ 警告: {db_path} 已存在。")
        print("请手动先将其改名备份，再运行此脚本以创建全新库。")
    else:
        init_db()