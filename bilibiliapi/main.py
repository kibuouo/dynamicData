from core.Myfetch import Fetch
from core.Myfetch import Spider
#from spiders.bilibili import BilibiliSpider
from pipelines.Myparser import Parser
from pipelines.cleaner import Cleaner
from pipelines.saver import Saver  # <--- 引入你的存储员
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
def run():
    print("🚀 爬虫任务启动...")
    
    # 1. 组装零件
    #my_fetcher = Fetch(config_path="setting.yaml")
    spider = Spider(config_path="setting.yaml")  # <--- 直接用 Spider 就行了，它继承了 Fetch 的能力
    saver = Saver()  # <--- 实例化存储员
    
    # 2. 流水线作业
    raw_data = spider.get_all_popular(max_items=200)
    parsed_list = Parser.parser_popular_items(raw_data)
    clean_df = Cleaner.clean_videos(parsed_list)
    
    # 3. 数据落盘 (不再直接写 pandas 代码，而是呼叫存储员)
    saver.save_to_csv(clean_df, filename="bilibili_popular_top200")
    saver.save_to_json(clean_df, filename="bilibili_popular_top200.json")
    # 如果将来要存数据库，只需要加一行：
    saver.save_to_sqlite(clean_df, db_name="bilibili_data.db", table_name="popular_videos")

if __name__ == "__main__":
    run()