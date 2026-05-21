import logging
import sqlite3
from contextlib import closing
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "cleaned" / "bilibili_data.db"


def get_connection():
    """创建 SQLite 连接，并让查询结果可以转成字典。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_all_videos(limit=200):
    """查询热门视频数据，返回字典列表。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                SELECT *
                FROM popular_videos
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    except sqlite3.OperationalError as error:
        logging.error("查询数据库失败: %s", error)
        return []

    return [dict(row) for row in rows]
