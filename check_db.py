import sqlite3
from pathlib import Path

DB_PATH = Path("data/cleaned/bilibili_data.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("数据库中的表：")
for table in tables:
    print(table[0])

for table in tables:
    table_name = table[0]
    print(f"\n表 {table_name} 的字段：")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()

    for col in columns:
        print(col)

conn.close()