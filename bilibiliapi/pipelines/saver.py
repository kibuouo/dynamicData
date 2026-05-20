import logging
import os
import pathlib
import sqlite3
from contextlib import closing


class Saver:
    """
    Persist cleaned data to files or SQLite.
    """

    def __init__(self, save_dir='data/cleaned'):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    @staticmethod
    def _quote_identifier(identifier):
        return '"' + str(identifier).replace('"', '""') + '"'

    def save_to_csv(self, df, filename='popular_cleaned.csv'):
        save_path = pathlib.Path(self.save_dir) / filename
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        logging.info(f"Data saved to {save_path}")

    def save_to_json(self, df, filename='popular_cleaned.json'):
        save_path = pathlib.Path(self.save_dir) / filename
        df.to_json(save_path, orient='records', force_ascii=False)
        logging.info(f"Data saved to {save_path}")

    def save_to_sqlite(self, df, db_name='bilibili_data.db', table_name='popular_videos'):
        if df.empty:
            logging.warning("DataFrame is empty; nothing was saved to SQLite")
            return
        if 'bvid' not in df.columns:
            logging.error("Missing required column 'bvid'; cannot de-duplicate SQLite rows")
            return

        write_df = df.dropna(subset=['bvid']).drop_duplicates(subset=['bvid'], keep='last')
        if write_df.empty:
            logging.warning("No rows with a valid bvid to save")
            return

        db_path = pathlib.Path(self.save_dir) / db_name

        try:
            with closing(sqlite3.connect(db_path)) as conn:
                with conn:
                    quoted_table = self._quote_identifier(table_name)
                    quoted_bvid = self._quote_identifier('bvid')
                    index_name = self._quote_identifier(f'idx_{table_name}_bvid_unique')
                    tmp_table_name = f'__tmp_{table_name}_upsert'
                    quoted_tmp_table = self._quote_identifier(tmp_table_name)
                    quoted_columns = ', '.join(self._quote_identifier(col) for col in write_df.columns)
                    update_columns = [col for col in write_df.columns if col != 'bvid']

                    if update_columns:
                        update_clause = 'DO UPDATE SET ' + ', '.join(
                            f"{self._quote_identifier(col)} = excluded.{self._quote_identifier(col)}"
                            for col in update_columns
                        )
                    else:
                        update_clause = 'DO NOTHING'

                    write_df.head(0).to_sql(table_name, conn, if_exists='append', index=False)
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
                    conn.execute(
                        f"""
                        CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
                        ON {quoted_table} ({quoted_bvid})
                        WHERE {quoted_bvid} IS NOT NULL
                        """
                    )
                    conn.execute(f"DROP TABLE IF EXISTS {quoted_tmp_table}")
                    write_df.to_sql(tmp_table_name, conn, if_exists='replace', index=False)
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

            logging.info(f"Saved {len(write_df)} unique rows to SQLite: {db_name} -> {table_name}")
        except Exception as e:
            logging.error(f"Failed to write SQLite: {e}")
