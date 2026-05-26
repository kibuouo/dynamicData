import logging
import sqlite3
from contextlib import closing

import pandas as pd

from bilibiliapi.analysis.metrics import rate_metrics
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


def _latest_category_data_sql(conn):
    snapshot_columns = _get_table_columns(conn, "popular_video_snapshots")
    return f"""
    {LATEST_SNAPSHOT_CTE}
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


def analyze_category(df):
    """按分区统计视频数量、播放量和平均点赞率。"""
    if df.empty:
        return pd.DataFrame()

    analysis_df = rate_metrics(df)
    result = (
        analysis_df.groupby("分区").agg(
            视频数量=("bvid", "count"),
            总播放量=("播放量", "sum"),
            平均播放量=("播放量", "mean"),
            平均点赞率=("点赞率", "mean"),
        ).sort_values("总播放量", ascending=False).reset_index()
    )
    return result


def query_category_analysis():
    """从数据库读取视频数据，并返回分区分析结果。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    try:
        with closing(get_connection()) as conn:
            if _snapshot_table_exists(conn):
                sql = _latest_category_data_sql(conn)
            else:
                sql = """
                SELECT *
                FROM popular_videos
                """

            df = pd.read_sql_query(
                sql,
                conn,
            )
    except sqlite3.OperationalError as error:
        logging.error("查询分区分析数据失败: %s", error)
        return []

    result = analyze_category(df)
    return result.to_dict(orient="records")
