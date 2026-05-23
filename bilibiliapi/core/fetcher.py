"""通用数据获取模块：读取配置并发送 HTTP 请求。"""

import logging
from pathlib import Path

import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "settings.yaml"


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

    def fetch_json(self, url, headers=None, params=None, timeout=10):
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
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            logging.error("请求发生错误: %s", error)
            return None
