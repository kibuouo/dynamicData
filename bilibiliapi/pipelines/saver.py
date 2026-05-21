import logging
import sqlite3
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAVE_DIR = PROJECT_ROOT / "data" / "cleaned"


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

    def _ensure_table_columns(self, conn, table_name, columns):
        """已有表缺少新字段时，自动补充字段。"""
        quoted_table = self._quote_identifier(table_name)
        cursor = conn.execute(f"PRAGMA table_info({quoted_table})")
        existing_columns = {row[1] for row in cursor.fetchall()}

        for column in columns:
            if column not in existing_columns:
                quoted_column = self._quote_identifier(column)
                conn.execute(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} TEXT")

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
                    quoted_table = self._quote_identifier(table_name)
                    quoted_bvid = self._quote_identifier("bvid")
                    index_name = self._quote_identifier(f"idx_{table_name}_bvid_unique")
                    tmp_table_name = f"__tmp_{table_name}_upsert"
                    quoted_tmp_table = self._quote_identifier(tmp_table_name)
                    quoted_columns = ", ".join(
                        self._quote_identifier(col) for col in write_df.columns
                    )
                    update_columns = [col for col in write_df.columns if col != "bvid"]

                    if update_columns:
                        update_clause = "DO UPDATE SET " + ", ".join(
                            f"{self._quote_identifier(col)} = "
                            f"excluded.{self._quote_identifier(col)}"
                            for col in update_columns
                        )
                    else:
                        update_clause = "DO NOTHING"

                    # 先创建目标表结构，再清理历史重复 bvid。
                    write_df.head(0).to_sql(table_name, conn, if_exists="append", index=False)
                    self._ensure_table_columns(conn, table_name, write_df.columns)
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

                    # 给 bvid 建唯一索引，后续插入时才能按 bvid 更新已有记录。
                    conn.execute(
                        f"""
                        CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
                        ON {quoted_table} ({quoted_bvid})
                        WHERE {quoted_bvid} IS NOT NULL
                        """
                    )

                    # 用临时表承接 pandas 写入结果，再合并到正式表。
                    conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")
                    write_df.to_sql(tmp_table_name, conn, if_exists="replace", index=False)
                    conn.execute(
                        f"""
                        INSERT INTO {quoted_table} ({quoted_columns})
                        SELECT {quoted_columns}
                        FROM {quoted_tmp_table}
                        WHERE TRUE
                        ON CONFLICT({quoted_bvid}) WHERE {quoted_bvid} IS NOT NULL
                        {update_clause}
                        """
                    )
                    conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")

            logging.info("已写入 SQLite: %s -> %s，共 %s 条", db_name, table_name, len(write_df))
        except Exception as error:
            logging.error("写入 SQLite 失败: %s", error)
