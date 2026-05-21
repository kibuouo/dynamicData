import sqlite3
from pathlib import Path
'''这个模块定义了数据库路径和连接相关的常量。'''
ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "cleaned" / "bilibili_data.db"
'''提供一个函数来获取数据库连接。这个函数使用 sqlite3 模块连接到指定的数据库路径，并设置 row_factory 以便返回字典形式的结果。'''
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def query_all_videos():
    conn = get_connection()

    cursor = conn.execute("""
        SELECT *
        FROM popular_videos
        LIMIT 200
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]