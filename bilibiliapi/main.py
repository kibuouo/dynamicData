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
    logging.info("raw_data 数量: %s", len(raw_data))

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parsed_list = Parser.parse_popular_items(raw_data)
    logging.info("parsed_list 数量: %s", len(parsed_list))

    raw_ranking_groups = spider.get_all_ranking()
    ranking_list = []
    for group in raw_ranking_groups:
        ranking_list.extend(
            Parser.parse_ranking_items(
                group.get("list", []),
                rid=group.get("rid", 0),
                ranking_type=group.get("ranking_type", spider.ranking_type),
                fetched_at=fetched_at,
            )
        )
    logging.info("ranking_list 数量: %s", len(ranking_list))

    parsed_list.extend(ranking_list)
    parsed_list = sorted(
        parsed_list,
        key=get_video_views,
        reverse=True,
    )
    clean_df = Cleaner.clean_videos(parsed_list)
    logging.info("clean_df shape: %s", clean_df.shape)
    logging.info("clean_df columns: %s", list(clean_df.columns))

    if clean_df.empty:
        logging.warning("没有抓取到有效视频数据，跳过指标计算和保存。")
        return

    clean_df["抓取时间"] = fetched_at
    analysis_df = rate_metrics(clean_df)

    saver.save_to_csv(analysis_df, filename="bilibili_popular.csv")
    saver.save_to_json(analysis_df, filename="bilibili_popular.json")
    saver.save_to_sqlite(
        analysis_df,
        db_name="bilibili_data.db",
        table_name="popular_videos",
    )

    if ranking_list:
        ranking_df = Cleaner.clean_videos(ranking_list)
        if not ranking_df.empty:
            saver.save_ranking_snapshots(
                ranking_df,
                db_name="bilibili_data.db",
            )


if __name__ == "__main__":
    run()
