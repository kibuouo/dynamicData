import logging
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAVE_DIR = PROJECT_ROOT / "data" / "cleaned"
STABLE_VIDEO_COLUMNS = [
    "aid",
    "bvid",
    "cid",
    "视频标题",
    "UP主",
    "分区",
    "pub_date",
    "视频链接",
    "封面链接",
    "时长",
]
SNAPSHOT_COLUMNS = [
    "bvid",
    "抓取时间",
    "播放量",
    "弹幕数",
    "点赞数",
    "投币数",
    "收藏数",
]
SNAPSHOT_TABLE_NAME = "popular_video_snapshots"
SQLITE_COLUMN_TYPES = {
    "aid": "INTEGER",
    "bvid": "TEXT",
    "cid": "INTEGER",
    "视频标题": "TEXT",
    "UP主": "TEXT",
    "分区": "TEXT",
    "pub_date": "TEXT",
    "视频链接": "TEXT",
    "封面链接": "TEXT",
    "时长": "INTEGER",
    "抓取时间": "TEXT",
    "播放量": "INTEGER",
    "弹幕数": "INTEGER",
    "点赞数": "INTEGER",
    "投币数": "INTEGER",
    "收藏数": "INTEGER",
}


class Saver:
    """把清洗后的数据保存为 CSV、JSON 或 SQLite。"""

    def __init__(self, save_dir=DEFAULT_SAVE_DIR):
        self.save_dir = Path(save_dir)
        if not self.save_dir.is_absolute():
            self.save_dir = PROJECT_ROOT / self.save_dir

        self.save_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _quote_identifier(identifier):
        """安全处理 SQLite 表名、字段名，避免特殊字符导致 SQL 出错。"""
        return '"' + str(identifier).replace('"', '""') + '"'

    def _table_exists(self, conn, table_name):
        cursor = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        )
        return cursor.fetchone() is not None

    def _get_table_columns(self, conn, table_name):
        quoted_table = self._quote_identifier(table_name)
        return [row[1] for row in conn.execute(f"PRAGMA table_info({quoted_table})")]

    def _create_table(self, conn, table_name, columns):
        quoted_table = self._quote_identifier(table_name)
        column_sql = ",\n".join(
            f"{self._quote_identifier(column)} {SQLITE_COLUMN_TYPES.get(column, 'TEXT')}"
            for column in columns
        )
        conn.execute(f"CREATE TABLE IF NOT EXISTS {quoted_table} ({column_sql})")

    def _prepare_columns(self, df, columns):
        table_df = df.copy()
        for column in columns:
            if column not in table_df.columns:
                table_df[column] = None
        return table_df[columns]

    def _ensure_table_schema(self, conn, table_name, columns):
        if not self._table_exists(conn, table_name):
            self._create_table(conn, table_name, columns)
            return

        old_columns = self._get_table_columns(conn, table_name)
        if old_columns == columns:
            return

        quoted_table = self._quote_identifier(table_name)
        tmp_table_name = f"__tmp_{table_name}_rebuild"
        quoted_tmp_table = self._quote_identifier(tmp_table_name)
        quoted_columns = ", ".join(self._quote_identifier(column) for column in columns)
        select_columns = ", ".join(
            self._quote_identifier(column)
            if column in old_columns
            else f"NULL AS {self._quote_identifier(column)}"
            for column in columns
        )

        if "bvid" in old_columns:
            quoted_bvid = self._quote_identifier("bvid")
            dedupe_where = f"""
            WHERE {quoted_bvid} IS NULL
               OR rowid IN (
                   SELECT MAX(rowid)
                   FROM {quoted_table}
                   WHERE {quoted_bvid} IS NOT NULL
                   GROUP BY {quoted_bvid}
               )
            """
        else:
            dedupe_where = ""

        conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")
        self._create_table(conn, tmp_table_name, columns)
        conn.execute(
            f"""
            INSERT INTO {quoted_tmp_table} ({quoted_columns})
            SELECT {select_columns}
            FROM {quoted_table}
            {dedupe_where}
            """
        )
        conn.execute(f"DROP TABLE {quoted_table}")
        conn.execute(f"ALTER TABLE {quoted_tmp_table} RENAME TO {quoted_table}")

    def _remove_duplicate_bvid(self, conn, table_name):
        columns = self._get_table_columns(conn, table_name)
        if "bvid" not in columns:
            return

        quoted_table = self._quote_identifier(table_name)
        quoted_bvid = self._quote_identifier("bvid")
        conn.execute(
            f"""
            DELETE FROM {quoted_table}
            WHERE {quoted_bvid} IS NOT NULL
              AND rowid NOT IN (
                  SELECT MAX(rowid)
                  FROM {quoted_table}
                  WHERE {quoted_bvid} IS NOT NULL
                  GROUP BY {quoted_bvid}
              )
            """
        )

    def _create_bvid_unique_index(self, conn, table_name):
        quoted_table = self._quote_identifier(table_name)
        quoted_bvid = self._quote_identifier("bvid")
        index_name = self._quote_identifier(f"idx_{table_name}_bvid_unique")
        conn.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
            ON {quoted_table} ({quoted_bvid})
            WHERE {quoted_bvid} IS NOT NULL
            """
        )

    def _create_snapshot_unique_index(self, conn, snapshot_table_name):
        quoted_table = self._quote_identifier(snapshot_table_name)
        quoted_bvid = self._quote_identifier("bvid")
        quoted_time = self._quote_identifier("抓取时间")
        index_name = self._quote_identifier(
            f"idx_{snapshot_table_name}_bvid_time_unique"
        )
        conn.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
            ON {quoted_table} ({quoted_bvid}, {quoted_time})
            WHERE {quoted_bvid} IS NOT NULL AND {quoted_time} IS NOT NULL
            """
        )

    def _upsert_by_bvid(self, conn, df, table_name):
        quoted_table = self._quote_identifier(table_name)
        quoted_bvid = self._quote_identifier("bvid")
        tmp_table_name = f"__tmp_{table_name}_upsert"
        quoted_tmp_table = self._quote_identifier(tmp_table_name)
        quoted_columns = ", ".join(self._quote_identifier(col) for col in df.columns)
        update_columns = [col for col in df.columns if col != "bvid"]

        if update_columns:
            update_clause = "DO UPDATE SET " + ", ".join(
                f"{self._quote_identifier(col)} = excluded.{self._quote_identifier(col)}"
                for col in update_columns
            )
        else:
            update_clause = "DO NOTHING"

        conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")
        df.to_sql(tmp_table_name, conn, if_exists="replace", index=False)
        conn.execute(
            f"""
            INSERT INTO {quoted_table} ({quoted_columns})
            SELECT {quoted_columns}
            FROM {quoted_tmp_table}
            WHERE {quoted_bvid} IS NOT NULL
            ON CONFLICT({quoted_bvid}) WHERE {quoted_bvid} IS NOT NULL
            {update_clause}
            """
        )
        conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")

    def _insert_snapshots(self, conn, df, snapshot_table_name):
        quoted_table = self._quote_identifier(snapshot_table_name)
        quoted_bvid = self._quote_identifier("bvid")
        quoted_time = self._quote_identifier("抓取时间")
        tmp_table_name = f"__tmp_{snapshot_table_name}_insert"
        quoted_tmp_table = self._quote_identifier(tmp_table_name)
        quoted_columns = ", ".join(self._quote_identifier(col) for col in df.columns)

        conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")
        df.to_sql(tmp_table_name, conn, if_exists="replace", index=False)
        conn.execute(
            f"""
            INSERT INTO {quoted_table} ({quoted_columns})
            SELECT {quoted_columns}
            FROM {quoted_tmp_table}
            WHERE {quoted_bvid} IS NOT NULL AND {quoted_time} IS NOT NULL
            ON CONFLICT({quoted_bvid}, {quoted_time})
            WHERE {quoted_bvid} IS NOT NULL AND {quoted_time} IS NOT NULL
            DO NOTHING
            """
        )
        conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")

    def _migrate_old_snapshots(self, conn, table_name, snapshot_table_name):
        if not self._table_exists(conn, table_name):
            return

        old_columns = self._get_table_columns(conn, table_name)
        if "bvid" not in old_columns or "播放量" not in old_columns:
            return

        quoted_table = self._quote_identifier(table_name)
        quoted_snapshot_table = self._quote_identifier(snapshot_table_name)
        quoted_columns = ", ".join(
            self._quote_identifier(column) for column in SNAPSHOT_COLUMNS
        )
        time_value = (
            self._quote_identifier("抓取时间")
            if "抓取时间" in old_columns
            else "datetime('now', 'localtime')"
        )
        select_columns = []

        for column in SNAPSHOT_COLUMNS:
            quoted_column = self._quote_identifier(column)
            if column == "抓取时间":
                select_columns.append(
                    f"COALESCE({time_value}, datetime('now', 'localtime')) AS {quoted_column}"
                )
            elif column in old_columns:
                select_columns.append(quoted_column)
            else:
                select_columns.append(f"NULL AS {quoted_column}")

        quoted_bvid = self._quote_identifier("bvid")
        quoted_time = self._quote_identifier("抓取时间")
        conn.execute(
            f"""
            INSERT INTO {quoted_snapshot_table} ({quoted_columns})
            SELECT {", ".join(select_columns)}
            FROM {quoted_table}
            WHERE {quoted_bvid} IS NOT NULL
            ON CONFLICT({quoted_bvid}, {quoted_time})
            WHERE {quoted_bvid} IS NOT NULL AND {quoted_time} IS NOT NULL
            DO NOTHING
            """
        )

    def _save_popular_videos(self, conn, df, table_name):
        source_df = df.copy()
        if "抓取时间" not in source_df.columns:
            source_df["抓取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        video_df = self._prepare_columns(source_df, STABLE_VIDEO_COLUMNS)
        snapshot_df = self._prepare_columns(source_df, SNAPSHOT_COLUMNS)

        self._create_table(conn, SNAPSHOT_TABLE_NAME, SNAPSHOT_COLUMNS)
        self._create_snapshot_unique_index(conn, SNAPSHOT_TABLE_NAME)
        self._migrate_old_snapshots(conn, table_name, SNAPSHOT_TABLE_NAME)

        self._ensure_table_schema(conn, table_name, STABLE_VIDEO_COLUMNS)
        self._remove_duplicate_bvid(conn, table_name)
        self._create_bvid_unique_index(conn, table_name)

        self._upsert_by_bvid(conn, video_df, table_name)
        self._insert_snapshots(conn, snapshot_df, SNAPSHOT_TABLE_NAME)

    def _save_single_table(self, conn, df, table_name):
        df.head(0).to_sql(table_name, conn, if_exists="append", index=False)
        self._remove_duplicate_bvid(conn, table_name)
        self._create_bvid_unique_index(conn, table_name)
        self._upsert_by_bvid(conn, df, table_name)

    def save_to_csv(self, df, filename="popular_cleaned.csv"):
        save_path = self.save_dir / filename
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        logging.info("CSV 已保存: %s", save_path)

    def save_to_json(self, df, filename="popular_cleaned.json"):
        save_path = self.save_dir / filename
        df.to_json(save_path, orient="records", force_ascii=False)
        logging.info("JSON 已保存: %s", save_path)

    def save_to_sqlite(self, df, db_name="bilibili_data.db", table_name="popular_videos"):
        if df.empty:
            logging.warning("DataFrame 为空，未写入 SQLite")
            return

        if "bvid" not in df.columns:
            logging.error("缺少 bvid 字段，无法按视频去重写入 SQLite")
            return

        write_df = df.dropna(subset=["bvid"]).drop_duplicates(
            subset=["bvid"],
            keep="last",
        )
        if write_df.empty:
            logging.warning("没有有效 bvid 的数据，未写入 SQLite")
            return

        db_path = self.save_dir / db_name

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                with conn:
                    if table_name == "popular_videos":
                        self._save_popular_videos(conn, write_df, table_name)
                    else:
                        self._save_single_table(conn, write_df, table_name)

            logging.info("已写入 SQLite: %s -> %s，共 %s 条", db_name, table_name, len(write_df))
        except Exception as error:
            logging.error("写入 SQLite 失败: %s", error)
