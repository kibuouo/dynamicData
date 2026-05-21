class Parser:
    """把 B站接口返回的原始 JSON 转成项目需要的字段列表。"""

    @staticmethod
    def parse_popular_items(raw_data):
        """
        从热门视频 JSON 数据中提取关心的字段。

        返回值是列表，列表中的每个元素是一条视频记录。
        """
        items = []

        for entry in raw_data:
            item = {
                "bvid": entry.get("bvid"),
                "视频标题": entry.get("title"),
                "UP主": entry.get("owner", {}).get("name"),
                "播放量": entry.get("stat", {}).get("view"),
                "弹幕数": entry.get("stat", {}).get("danmaku"),
                "点赞数": entry.get("stat", {}).get("like"),
                "投币数": entry.get("stat", {}).get("coin"),
                "收藏数": entry.get("stat", {}).get("favorite"),
                "分区": entry.get("tname"),
                "pub_date": entry.get("pubdate"),
                "视频链接": f"https://www.bilibili.com/video/{entry.get('bvid')}",
                "封面链接": entry.get("pic"),
                "时长": entry.get("duration"),
            }
            items.append(item)

        return items
