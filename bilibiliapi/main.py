import logging
from datetime import datetime
from bilibiliapi.pipelines.cleaner import Cleaner
from bilibiliapi.pipelines.parser import Parser
from bilibiliapi.pipelines.saver import Saver
from bilibiliapi.spiders.popular_spider import Spider
from bilibiliapi.analysis.metrics import rate_metrics


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


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
    clean_df = Cleaner.clean_videos(parsed_list)
    clean_df["抓取时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    analysis_df = rate_metrics(clean_df)

    saver.save_to_csv(analysis_df, filename="bilibili_popular.csv")
    saver.save_to_json(analysis_df, filename="bilibili_popular.json")
    saver.save_to_sqlite(
        analysis_df,
        db_name="bilibili_data.db",
        table_name="popular_videos",
    )


if __name__ == "__main__":
    run()
