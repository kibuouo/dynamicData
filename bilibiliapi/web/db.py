import logging
import sqlite3
import pandas as pd
from contextlib import closing
from pathlib import Path
from bilibiliapi.analysis.category import analyze_category

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
                ORDER BY "播放量" DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    except sqlite3.OperationalError as error:
        logging.error("查询数据库失败: %s", error)
        return []

    return [dict(row) for row in rows]


def query_video_summary():
    """查询看板顶部需要的汇总指标。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return {}

    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) AS video_count,
                    COALESCE(SUM("播放量"), 0) AS total_views,
                    COALESCE(AVG("播放量"), 0) AS avg_views,
                    COALESCE(MAX("播放量"), 0) AS max_views,
                    COALESCE(SUM("点赞数"), 0) AS total_likes,
                    COALESCE(SUM("收藏数"), 0) AS total_favorites
                FROM popular_videos
                """
            )
            row = cursor.fetchone()
    except sqlite3.OperationalError as error:
        logging.error("查询汇总指标失败: %s", error)
        return {}

    return dict(row) if row else {}


def query_category_summary(limit=10):
    """按分区统计视频数量和播放量。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    try:
        with closing(get_connection()) as conn:
            cursor = conn.execute(
                """
                SELECT
                    "分区" AS category,
                    COUNT(*) AS video_count,
                    COALESCE(SUM("播放量"), 0) AS total_views,
                    COALESCE(AVG("播放量"), 0) AS avg_views
                FROM popular_videos
                GROUP BY "分区"
                ORDER BY total_views DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    except sqlite3.OperationalError as error:
        logging.error("查询分区统计失败: %s", error)
        return []

    return [dict(row) for row in rows]
def query_category_analysis():
    """查询分区分析数据，返回 DataFrame 格式。"""

    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return pd.DataFrame()

    try:
        with closing(get_connection()) as conn:
            df = pd.read_sql_query(
                """
                SELECT *
                FROM popular_videos
                """,
                conn,
            )
    except sqlite3.OperationalError as error:
        logging.error("查询分区分析数据失败: %s", error)
        return pd.DataFrame()
    result = analyze_category(df)
    return result.to_dict(orient="records")