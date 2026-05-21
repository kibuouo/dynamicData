"""数据获取模块：请求 B站 热门视频 API。"""

import json
import logging
from pathlib import Path

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "settings.yaml"
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw_popular.json"


class Fetch:
    """负责配置读取、会话管理和通用 HTTP 请求。"""

    def __init__(self, config_path=DEFAULT_CONFIG_PATH):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        })
        self.config = self._load_config(config_path)

    @staticmethod
    def _load_config(config_path):
        """读取 YAML 配置文件，失败时返回空字典。"""
        config_path = Path(config_path)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path

        try:
            with config_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
                logging.info("配置文件加载成功: %s", config_path)
                return config
        except FileNotFoundError:
            logging.error("配置文件不存在: %s", config_path)
        except yaml.YAMLError as error:
            logging.error("配置文件格式错误: %s", error)

        return {}

    def fetch_json(self, url, headers=None, params=None):
        """
        发送 GET 请求并返回 JSON 数据。

        请求失败时返回 None，由调用方决定是否继续。
        """
        headers = headers or {}
        params = params or {}

        try:
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logging.error("请求发生错误: %s", error)
            return None


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
        self.page_size = spider_config.get("page_size", 20)
        self.max_pages = spider_config.get("max_pages", 100)

    def get_popular_page(self, pn=1):
        """获取单页热门视频数据。"""
        url = f"{self.base_url}{self.popular_endpoint}"
        params = {
            "ps": self.page_size,
            "pn": pn,
            "rid": 0,
        }
        return self.fetch_json(url, params=params)

    def get_all_popular(self, max_items=None, max_pages=None):
        """
        翻页获取热门视频列表。

        max_items 控制最多保留多少条数据，max_pages 用来避免无限翻页。
        """
        max_pages = max_pages or self.max_pages
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
