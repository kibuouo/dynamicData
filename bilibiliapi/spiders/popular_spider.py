"""热门视频爬虫：请求 B站 热门视频和实时在线人数接口。"""

import json
import logging

from bilibiliapi.core.fetcher import DEFAULT_CONFIG_PATH, PROJECT_ROOT, Fetch


RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw_popular.json"
RAW_RANKING_PATH = PROJECT_ROOT / "data" / "raw_ranking.json"


class Spider(Fetch):
    """B站热门视频爬虫，负责接口地址拼接和翻页。"""

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        super().__init__(config_path)

        api_config = self.config.get("api", {})
        spider_config = self.config.get("spider", {})

        self.base_url = api_config.get("base_url", "https://api.bilibili.com")
        self.popular_endpoint = (
            api_config.get("popular_endpoint")
            or api_config.get("popular")
            or "/x/web-interface/popular"
        )
        self.online_total_endpoint = api_config.get(
            "online_total_endpoint",
            "/x/player/online/total",
        )
        self.ranking_endpoint = api_config.get(
            "ranking_endpoint",
            "/x/web-interface/ranking/v2",
        )
        self.page_size = spider_config.get("page_size", 20)
        self.max_items = spider_config.get("max_items", 200)
        self.max_pages = spider_config.get("max_pages", 100)
        self.online_total_limit = spider_config.get("online_total_limit", 50)
        self.online_total_delay = spider_config.get("online_total_delay", 0.2)
        self.ranking_rids = spider_config.get("ranking_rids", [0])
        self.ranking_type = spider_config.get("ranking_type", "all")
        self.ranking_limit = spider_config.get("ranking_limit", 100)

    def get_popular_page(self, pn=1):
        """获取单页热门视频数据。"""
        url = f"{self.base_url}{self.popular_endpoint}"
        params = {
            "ps": self.page_size,
            "pn": pn,
            "rid": 0,
        }
        return self.fetch_json(url, params=params)

    def get_video_online_total(self, bvid=None, cid=None, aid=None):
        """
        查询单个视频的实时在线人数。

        B站这个接口需要 cid，并且需要 bvid 或 aid 其中一个。
        """
        if not cid:
            logging.warning("查询实时在线人数需要 cid")
            return None

        if not bvid and not aid:
            logging.warning("查询实时在线人数需要 bvid 或 aid")
            return None

        url = f"{self.base_url}{self.online_total_endpoint}"
        params = {"cid": cid}

        if bvid:
            params["bvid"] = bvid
        else:
            params["aid"] = aid

        data = self.fetch_json(url, params=params, timeout=3)
        if not data or data.get("code") != 0:
            logging.warning("实时在线人数接口返回异常: %s", data)
            return None

        return data.get("data", {})

    def get_ranking(self, rid=0, ranking_type=None):
        """获取 B站 ranking/v2 榜单数据。"""
        url = f"{self.base_url}{self.ranking_endpoint}"
        params = {
            "rid": rid,
            "type": ranking_type or self.ranking_type,
        }
        return self.fetch_json(url, params=params)

    def get_all_ranking(self, rids=None, ranking_type=None, limit=None):
        """按分区 ID 获取排行榜列表，返回带来源信息的字典列表。"""
        rids = rids or self.ranking_rids
        ranking_type = ranking_type or self.ranking_type
        limit = limit or self.ranking_limit
        items = []

        for rid in rids:
            logging.info("正在获取排行榜 rid=%s type=%s...", rid, ranking_type)
            data = self.get_ranking(rid=rid, ranking_type=ranking_type)

            if not data or data.get("code") != 0:
                logging.warning("排行榜 rid=%s 数据异常，跳过", rid)
                continue

            ranking_items = data.get("data", {}).get("list", [])
            if limit:
                ranking_items = ranking_items[:limit]

            items.append({
                "rid": rid,
                "ranking_type": ranking_type,
                "list": ranking_items,
            })

        RAW_RANKING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RAW_RANKING_PATH.open("w", encoding="utf-8") as file:
            json.dump(items, file, ensure_ascii=False, indent=4)

        return items

    def get_all_popular(self, max_items=None, max_pages=None):
        """
        翻页获取热门视频列表。

        max_items 控制最多保留多少条数据，max_pages 用来避免无限翻页。
        """
        if max_pages is None:
            max_pages = self.max_pages
        items = []

        for pn in range(1, max_pages + 1):
            logging.info("正在获取第 %s 页...", pn)
            data = self.get_popular_page(pn)

            if not data or data.get("code") != 0:
                logging.warning("第 %s 页数据异常，停止抓取", pn)
                break

            page_items = data.get("data", {}).get("list", [])
            if not page_items:
                logging.info("第 %s 页没有数据了，停止抓取", pn)
                break

            items.extend(page_items)

            if max_items and len(items) >= max_items:
                logging.info("已达到最大条数 %s，停止抓取", max_items)
                items = items[:max_items]
                break

        RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RAW_DATA_PATH.open("w", encoding="utf-8") as file:
            json.dump(items, file, ensure_ascii=False, indent=4)

        return items
