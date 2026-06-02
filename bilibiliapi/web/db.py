import logging
import sqlite3
from contextlib import closing
from datetime import datetime
from bilibiliapi.database import DB_PATH


ONLINE_SNAPSHOT_TABLE_NAME = "video_online_snapshots"
RANKING_SNAPSHOT_TABLE_NAME = "ranking_video_snapshots"
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


def _quote_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot_table_exists(conn):
    cursor = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'popular_video_snapshots'
        """
    )
    return cursor.fetchone() is not None


def _online_snapshot_table_exists(conn):
    cursor = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (ONLINE_SNAPSHOT_TABLE_NAME,),
    )
    return cursor.fetchone() is not None


def _ranking_snapshot_table_exists(conn):
    cursor = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (RANKING_SNAPSHOT_TABLE_NAME,),
    )
    return cursor.fetchone() is not None


def _ensure_online_snapshot_table(conn):
    table = _quote_identifier(ONLINE_SNAPSHOT_TABLE_NAME)
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            bvid TEXT,
            cid INTEGER,
            aid INTEGER,
            "抓取时间" TEXT,
            "在线人数" INTEGER
        )
        """
    )
    conn.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{ONLINE_SNAPSHOT_TABLE_NAME}_bvid_time_unique
        ON {table} (bvid, "抓取时间")
        WHERE bvid IS NOT NULL AND "抓取时间" IS NOT NULL
        """
    )


def _get_table_columns(conn, table_name):
    quoted_table = _quote_identifier(table_name)
    return [row[1] for row in conn.execute(f"PRAGMA table_info({quoted_table})")]


def _optional_snapshot_column(snapshot_columns, column):
    quoted_column = '"' + column.replace('"', '""') + '"'
    if column in snapshot_columns:
        return f"snapshots.{quoted_column}"
    return f"NULL AS {quoted_column}"


def save_online_snapshots(items, fetched_at=None):
    """保存一批视频实时在线人数，返回成功写入的条数。"""
    if not items:
        return 0

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    fetched_at = fetched_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for item in items:
        bvid = item.get("bvid")
        count = item.get("count")
        if not bvid or count is None:
            continue

        try:
            count = int(count)
        except (TypeError, ValueError):
            continue

        rows.append((
            bvid,
            item.get("cid"),
            item.get("aid"),
            fetched_at,
            count,
        ))

    if not rows:
        return 0

    table = _quote_identifier(ONLINE_SNAPSHOT_TABLE_NAME)

    try:
        with closing(_get_connection()) as conn:
            with conn:
                _ensure_online_snapshot_table(conn)
                conn.executemany(
                    f"""
                    INSERT INTO {table}
                    (bvid, cid, aid, "抓取时间", "在线人数")
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(bvid, "抓取时间")
                    WHERE bvid IS NOT NULL AND "抓取时间" IS NOT NULL
                    DO UPDATE SET
                        cid = excluded.cid,
                        aid = excluded.aid,
                        "在线人数" = excluded."在线人数"
                    """,
                    rows,
                )
    except sqlite3.OperationalError as error:
        logging.error("保存在线人数快照失败: %s", error)
        return 0

    return len(rows)


def query_online_ranking(limit=10):
    """查询最近一批在线人数快照中在线人数最多的视频。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    limit = min(max(int(limit), 1), 100)

    try:
        with closing(_get_connection()) as conn:
            if not _online_snapshot_table_exists(conn):
                return []

            table = _quote_identifier(ONLINE_SNAPSHOT_TABLE_NAME)
            sql = f"""
            WITH latest_batch AS (
                SELECT MAX("抓取时间") AS latest_time
                FROM {table}
            )
            SELECT
                online.bvid,
                online.cid,
                online.aid,
                online."在线人数",
                online."抓取时间" AS "在线人数抓取时间",
                videos."视频标题",
                videos."UP主",
                videos."分区",
                videos."视频链接",
                videos."封面链接",
                videos."时长"
            FROM {table} AS online
            JOIN latest_batch
              ON online."抓取时间" = latest_batch.latest_time
            LEFT JOIN popular_videos AS videos
              ON online.bvid = videos.bvid
            ORDER BY online."在线人数" DESC
            LIMIT ?
            """
            cursor = conn.execute(sql, (limit,))
            rows = cursor.fetchall()
    except (sqlite3.OperationalError, ValueError) as error:
        logging.error("查询在线人数排行失败: %s", error)
        return []

    return [dict(row) for row in rows]


def query_ranking_summary():
    """查询最新一批 B站排行榜快照的摘要指标。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return {}

    try:
        with closing(_get_connection()) as conn:
            if not _ranking_snapshot_table_exists(conn):
                return {}

            table = _quote_identifier(RANKING_SNAPSHOT_TABLE_NAME)
            cursor = conn.execute(
                f"""
                WITH latest_batch AS (
                    SELECT MAX("榜单抓取时间") AS latest_time
                    FROM {table}
                ),
                latest_rows AS (
                    SELECT *
                    FROM {table}
                    JOIN latest_batch
                      ON {table}."榜单抓取时间" = latest_batch.latest_time
                )
                SELECT
                    COUNT(*) AS ranking_video_count,
                    COALESCE(MAX(
                        CASE
                            WHEN "榜单分数" IS NOT NULL AND "榜单分数" > 0 THEN "榜单分数"
                            ELSE ((SELECT COUNT(*) FROM latest_rows) - "榜单排名" + 1) * 100
                        END
                    ), 0) AS max_ranking_score,
                    MAX("榜单抓取时间") AS ranking_latest_time
                FROM latest_rows
                """
            )
            row = cursor.fetchone()
    except sqlite3.OperationalError as error:
        logging.error("查询榜单摘要失败: %s", error)
        return {}

    return dict(row) if row else {}


def query_ranking_videos(limit=50):
    """查询最新一批 B站排行榜视频，并补充播放、点赞和在线人数。"""
    if not DB_PATH.exists():
        logging.warning("数据库文件不存在: %s", DB_PATH)
        return []

    limit = min(max(int(limit), 1), 200)

    try:
        with closing(_get_connection()) as conn:
            if not _ranking_snapshot_table_exists(conn):
                return []

            ranking_table = _quote_identifier(RANKING_SNAPSHOT_TABLE_NAME)
            online_join = ""
            online_select = "NULL AS \"在线人数\", NULL AS \"在线人数抓取时间\""
            if _online_snapshot_table_exists(conn):
                online_join = f"""
                LEFT JOIN (
                    SELECT online.*
                    FROM {ONLINE_SNAPSHOT_TABLE_NAME} AS online
                    JOIN (
                        SELECT bvid, MAX("抓取时间") AS latest_time
                        FROM {ONLINE_SNAPSHOT_TABLE_NAME}
                        WHERE bvid IS NOT NULL
                        GROUP BY bvid
                    ) AS latest_online
                      ON online.bvid = latest_online.bvid
                     AND online."抓取时间" = latest_online.latest_time
                ) AS online
                  ON ranking.bvid = online.bvid
                """
                online_select = """
                online."在线人数",
                online."抓取时间" AS "在线人数抓取时间"
                """

            snapshot_join = ""
            snapshot_select = """
                NULL AS "播放量",
                NULL AS "弹幕数",
                NULL AS "评论数",
                NULL AS "点赞数",
                NULL AS "投币数",
                NULL AS "收藏数",
                NULL AS "综合热度",
                NULL AS "疑似异常",
                NULL AS "抓取时间"
            """
            if _snapshot_table_exists(conn):
                snapshot_join = f"""
                {LATEST_SNAPSHOT_CTE}
                """
                snapshot_select = """
                latest_snapshots."播放量",
                latest_snapshots."弹幕数",
                latest_snapshots."评论数",
                latest_snapshots."点赞数",
                latest_snapshots."投币数",
                latest_snapshots."收藏数",
                latest_snapshots."综合热度",
                latest_snapshots."疑似异常",
                latest_snapshots."抓取时间"
                """

            sql = f"""
            {snapshot_join}
            {"WITH" if not snapshot_join else ","} latest_ranking_time AS (
                SELECT MAX("榜单抓取时间") AS latest_time
                FROM {ranking_table}
            )
            SELECT
                ranking.bvid,
                ranking."榜单分区ID",
                ranking."榜单类型",
                ranking."榜单排名",
                CASE
                    WHEN ranking."榜单分数" IS NOT NULL AND ranking."榜单分数" > 0 THEN ranking."榜单分数"
                    ELSE ((
                        SELECT COUNT(*)
                        FROM {ranking_table} AS ranking_count
                        JOIN latest_ranking_time
                          ON ranking_count."榜单抓取时间" = latest_ranking_time.latest_time
                    ) - ranking."榜单排名" + 1) * 100
                END AS "榜单分数",
                ranking."榜单抓取时间",
                videos.aid,
                videos.cid,
                videos."视频标题",
                videos."UP主",
                videos."分区",
                videos.pub_date,
                videos."视频链接",
                videos."封面链接",
                videos."时长",
                {snapshot_select},
                {online_select}
            FROM {ranking_table} AS ranking
            JOIN latest_ranking_time
              ON ranking."榜单抓取时间" = latest_ranking_time.latest_time
            LEFT JOIN popular_videos AS videos
              ON ranking.bvid = videos.bvid
            {"LEFT JOIN latest_snapshots ON ranking.bvid = latest_snapshots.bvid" if snapshot_join else ""}
            {online_join}
            ORDER BY ranking."榜单排名" ASC
            LIMIT ?
            """

            cursor = conn.execute(sql, (limit,))
            rows = cursor.fetchall()
    except (sqlite3.OperationalError, ValueError) as error:
        logging.error("查询榜单视频失败: %s", error)
        return []

    return [dict(row) for row in rows]


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
        {_optional_snapshot_column(snapshot_columns, "评论数")},
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
        with closing(_get_connection()) as conn:
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
        with closing(_get_connection()) as conn:
            if _snapshot_table_exists(conn):
                sql = f"""
                {LATEST_SNAPSHOT_CTE}
                SELECT
                    COUNT(videos.bvid) AS video_count,
                    COALESCE(SUM(snapshots."播放量"), 0) AS total_views,
                    COALESCE(AVG(snapshots."播放量"), 0) AS avg_views,
                    COALESCE(MAX(snapshots."播放量"), 0) AS max_views,
                    COALESCE(SUM(snapshots."评论数"), 0) AS total_comments,
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
                    COALESCE(SUM("评论数"), 0) AS total_comments,
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
        with closing(_get_connection()) as conn:
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
