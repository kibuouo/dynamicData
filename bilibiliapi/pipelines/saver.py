import os
import pathlib
import logging
#import pandas as pd
import sqlite3
class Saver:
    """
    【第六层：数据持久化层 (Load)】
    职责：只负责把清洗好的数据安全地落盘（存入文件或数据库）。
    """
    def __init__(self,save_dir='data/cleaned'):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
    def save_to_csv(self, df, filename='popular_cleaned.csv'):
        """把清洗好的 DataFrame 存成 CSV 文件"""
        save_path = pathlib.Path(self.save_dir) / filename
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        logging.info(f"数据已保存到 {save_path}")
    def save_to_json(self, df, filename='popular_cleaned.json'):
        """把清洗好的 DataFrame 存成 JSON 文件"""
        save_path = pathlib.Path(self.save_dir) / filename
        df.to_json(save_path, orient='records', force_ascii=False)
        logging.info(f"数据已保存到 {save_path}")
    def save_to_sqlite(self, df, db_name='bilibili_data.db', table_name='popular_videos'):
        """把清洗好的 DataFrame 存入 SQLite 数据库"""
        if df.empty:
            logging.warning("DataFrame 为空，未保存到数据库")
            return
        db_path = pathlib.Path(self.save_dir) / db_name

        try:
            # 【防御性编程】使用 with 语句，彻底杜绝数据库死锁！
            with sqlite3.connect(db_path) as conn:
                # 建议根据业务需求评估使用 append 还是 replace
                df.to_sql(table_name, conn, if_exists='append', index=False)
            # 日志写在 with 外面，代表真的成功执行完了
            logging.info(f"✅ 数据已安全保存到 SQLite: {db_name} -> 表: {table_name}")
        except Exception as e:
            # 捕获异常，防止一个数据库错误导致整个主程序崩溃
            logging.error(f"❌ 写入 SQLite 失败: {e}")
