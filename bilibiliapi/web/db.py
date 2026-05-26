import logging
import sqlite3
from contextlib import closing
from bilibiliapi.database import DB_PATH, get_connection


LATEST_SNAPSHOT_CTE = """
WITH latest_times AS (
    SELECT
        bvid,
        MAX("抓取时间") AS latest_time
    FROM popular_video_snapshots
    WHERE bvid IS NOT NULL
    GROUP BY bvid
),
latest_snapshots AS (
    SELECT snapshots.*
    FROM popular_video_snapshots AS snapshots
    JOIN latest_times AS latest
      ON snapshots.bvid = latest.bvid
     AND snapshots."抓取时间" = latest.latest_time
)
"""

def _snapshot_table_exists(conn):
    cursor = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'popular_video_snapshots'
        """
    )
    return cursor.fetchone() is not None


def _get_table_columns(conn, table_name):
    quoted_table = '"' + table_name.replace('"', '""') + '"'
    return [row[1] for row in conn.execute(f"PRAGMA table_info({quoted_table})")]


def _optional_snapshot_column(snapshot_columns, column):
    quoted_column = '"' + column.replace('"', '""') + '"'
    if column in snapshot_columns:
        return f"snapshots.{quoted_column}"
    return f"NULL AS {quoted_column}"


def _latest_video_select(snapshot_columns):
    return f"""
    SELECT
        videos."aid",
        videos."bvid",
        videos."cid",
        videos."视频标题",
        videos."UP主",
        videos."分区",
        videos."pub_date",
        videos."视频链接",
        videos."封面链接",
        videos."时长",
        snapshots."播放量",
        snapshots."弹幕数",
        snapshots."点赞数",
        snapshots."投币数",
        snapshots."收藏数",
        {_optional_snapshot_column(snapshot_columns, "综合热度")},
        {_optional_snapshot_column(snapshot_columns, "疑似异常")},
        snapshots."抓取时间"
    FROM popular_videos AS videos
    LEFT JOIN latest_snapshots AS snapshots
      ON videos.bvid = snapshots.bvid
    """


def _snapshot_order_by(snapshot_columns, order_by):
    if order_by == "综合热度" and "综合热度" in snapshot_columns:
        return """
        COALESCE(snapshots."综合热度", 0) DESC,
        COALESCE(snapshots."播放量", 0) DESC
        """
    return 'COALESCE(snapshots."播放量", 0) DESC'


def _main_table_order_by(conn, order_by):
    video_columns = _get_table_columns(conn, "popular_videos")
    if order_by == "综合热度" and "综合热度" in video_columns:
        return '"综合热度" DESC'
    return '"播放量" DESC'


def query_all_videos(limit=200, order_by="播放量"):
    """查询热门视频数据，返回字典列表。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    try:
        with closing(get_connection()) as conn:
            if _snapshot_table_exists(conn):
                snapshot_columns = _get_table_columns(conn, "popular_video_snapshots")
                sql = f"""
                {LATEST_SNAPSHOT_CTE}
                {_latest_video_select(snapshot_columns)}
                ORDER BY {_snapshot_order_by(snapshot_columns, order_by)}
                LIMIT ?
                """
            else:
                sql = """
                SELECT *
                FROM popular_videos
                ORDER BY {order_sql}
                LIMIT ?
                """.format(order_sql=_main_table_order_by(conn, order_by))

            cursor = conn.execute(
                sql,
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
            if _snapshot_table_exists(conn):
                sql = f"""
                {LATEST_SNAPSHOT_CTE}
                SELECT
                    COUNT(videos.bvid) AS video_count,
                    COALESCE(SUM(snapshots."播放量"), 0) AS total_views,
                    COALESCE(AVG(snapshots."播放量"), 0) AS avg_views,
                    COALESCE(MAX(snapshots."播放量"), 0) AS max_views,
                    COALESCE(SUM(snapshots."点赞数"), 0) AS total_likes,
                    COALESCE(SUM(snapshots."收藏数"), 0) AS total_favorites
                FROM popular_videos AS videos
                LEFT JOIN latest_snapshots AS snapshots
                  ON videos.bvid = snapshots.bvid
                """
            else:
                sql = """
                SELECT
                    COUNT(*) AS video_count,
                    COALESCE(SUM("播放量"), 0) AS total_views,
                    COALESCE(AVG("播放量"), 0) AS avg_views,
                    COALESCE(MAX("播放量"), 0) AS max_views,
                    COALESCE(SUM("点赞数"), 0) AS total_likes,
                    COALESCE(SUM("收藏数"), 0) AS total_favorites
                FROM popular_videos
                """

            cursor = conn.execute(sql)
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
            if _snapshot_table_exists(conn):
                sql = f"""
                {LATEST_SNAPSHOT_CTE}
                SELECT
                    videos."分区" AS category,
                    COUNT(videos.bvid) AS video_count,
                    COALESCE(SUM(snapshots."播放量"), 0) AS total_views,
                    COALESCE(AVG(snapshots."播放量"), 0) AS avg_views
                FROM popular_videos AS videos
                LEFT JOIN latest_snapshots AS snapshots
                  ON videos.bvid = snapshots.bvid
                GROUP BY videos."分区"
                ORDER BY total_views DESC
                LIMIT ?
                """
            else:
                sql = """
                SELECT
                    "分区" AS category,
                    COUNT(*) AS video_count,
                    COALESCE(SUM("播放量"), 0) AS total_views,
                    COALESCE(AVG("播放量"), 0) AS avg_views
                FROM popular_videos
                GROUP BY "分区"
                ORDER BY total_views DESC
                LIMIT ?
                """

            cursor = conn.execute(
                sql,
                (limit,),
            )
            rows = cursor.fetchall()
    except sqlite3.OperationalError as error:
        logging.error("查询分区统计失败: %s", error)
        return []

    return [dict(row) for row in rows]
