"""数据获取模块：请求 B站热门视频 API"""
import requests
import logging
import yaml
import json
class Fetch:
    """
    【第一层：底层网络请求引擎】
    职责：只负责管理会话、加载配置、发送 HTTP 请求和捕获网络异常。
    它不关心你要抓B站、淘宝还是知乎。
    """
    def __init__(self,config_path='setting.yaml'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.config = self._load_config(config_path)

    def _load_config(self, config_path):
        """内部方法：读取并解析 YAML 文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logging.info(f"配置文件 '{config_path}' 加载成功")
                return config
        except Exception as e:
            logging.error(f"加载配置文件 '{config_path}' 失败: {e}")
            return {}

    def fetch_json(self, url, headers=None, params=None):
        """
        通用的 GET 请求方法
        :param url: 完整的请求地址
        :param params: URL 里的查询参数（字典格式）
        :param headers: 针对当前请求需要额外添加的 Header
        :return: 成功返回 JSON 字典，失败返回 None
        """
        headers = headers or {}
        params = params or {}
        try:
            response = self.session.get(url, headers=headers, params=params,timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"请求发生错误: {e}")
            return None
class Spider(Fetch):
    """
    【第二层:B站业务爬虫类】
    职责：继承 Fetch 的网络能力，专门处理 B站 相关的接口地址拼接、翻页逻辑和数据提取。
    """
    def __init__(self,config_path='setting.yaml'):
        # 先调用父类初始化方法，把 Session 和 Config 准备好
        super().__init__(config_path)
        # 从配置字典中读取 API 地址（加入 default 后备方案，万一 yaml 里没写也不会报错）
        self.base_url = self.config.get("api", {}).get("base_url", "https://api.bilibili.com")
        self.popular_endpoint = self.config.get("api", {}).get("popular_endpoint", "/x/web-interface/popular")   
        self.page_size = self.config.get("spider", {}).get("page_size", 20)
    
    def get_popular_page(self,pn=1):
        """获取单页热门视频数据"""
        #拼接出完整的 URL
        url=f"{self.base_url}{self.popular_endpoint}"
        params = {
            'ps': self.page_size,
            'pn': pn,
            'rid': 0#全站
        }
        return self.fetch_json(url, params=params)
    def get_all_popular(self,max_items=None,max_pages=100):
        """
        智能翻页获取视频列表
        :param max_items: 期望获取的最大条数（传 None 则一直抓到没数据为止）
        :param max_pages: 安全锁，防止死循环
        """
        items=[]
        for pn in range(1, max_pages + 1):
            logging.info(f"正在获取第 {pn} 页...")
            data = self.get_popular_page(pn)
            if not data or data.get("code") != 0:
                logging.warning(f"第 {pn} 页数据异常，停止抓取")
                break
            page_items = data.get("data", {}).get("list", [])#每页的视频列表
            if not page_items:
                logging.info(f"第 {pn} 页没有数据了，停止抓取")
                break
            items.extend(page_items)
            if max_items and len(items) >= max_items:
                logging.info(f"已达到最大条数 {max_items}，停止抓取")
                break
        with open('data/raw_popular.json', 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        return items
    