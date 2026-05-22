import logging
import time
from datetime import datetime

from bilibiliapi.pipelines.cleaner import Cleaner
from bilibiliapi.pipelines.parser import Parser
from bilibiliapi.pipelines.saver import Saver
from bilibiliapi.spiders.popular_spider import Spider


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def add_online_total(parsed_list, spider):
    """给视频列表补充实时在线人数。"""
    limit = min(spider.online_total_limit, len(parsed_list))

    for index, item in enumerate(parsed_list):
        if index >= limit:
            item["在线人数"] = None
            continue

        online_data = spider.get_video_online_total(
            bvid=item.get("bvid"),
            cid=item.get("cid"),
            aid=item.get("aid"),
        )
        item["在线人数"] = online_data.get("count") if online_data else None

        if spider.online_total_delay > 0 and index < limit - 1:
            time.sleep(spider.online_total_delay)

    return parsed_list


def get_video_views(item):
    """返回视频播放量，用于按播放量排序。"""
    return item.get("播放量") or 0


def run():
    """运行完整的数据抓取、解析、清洗和保存流程。"""
    print("爬虫任务启动...")

    spider = Spider()
    saver = Saver()

    raw_data = spider.get_all_popular(max_items=spider.max_items)
    parsed_list = Parser.parse_popular_items(raw_data)
    parsed_list = sorted(
        parsed_list,
        key=get_video_views,
        reverse=True,
    )
    parsed_list = add_online_total(parsed_list, spider)
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
