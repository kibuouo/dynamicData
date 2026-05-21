import logging
from datetime import datetime

from bilibiliapi.core.fetcher import Spider
from bilibiliapi.pipelines.cleaner import Cleaner
from bilibiliapi.pipelines.parser import Parser
from bilibiliapi.pipelines.saver import Saver


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def run():
    """运行完整的数据抓取、解析、清洗和保存流程。"""
    print("爬虫任务启动...")

    spider = Spider()
    saver = Saver()

    raw_data = spider.get_all_popular(max_items=spider.max_items)
    parsed_list = Parser.parse_popular_items(raw_data)
    clean_df = Cleaner.clean_videos(parsed_list)
    clean_df["抓取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    saver.save_to_csv(clean_df, filename="bilibili_popular_top200.csv")
    saver.save_to_json(clean_df, filename="bilibili_popular_top200.json")
    saver.save_to_sqlite(
        clean_df,
        db_name="bilibili_data.db",
        table_name="popular_videos",
    )


if __name__ == "__main__":
    run()
