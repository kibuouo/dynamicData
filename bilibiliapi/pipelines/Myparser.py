import logging
class Parser:
    """
    【第三层：数据解析类】
    职责：专注于从原始 JSON 数据中提取出我们需要的字段，进行清洗和结构化处理。
    """
    def parser_popular_items(raw_data):
        """
        从原始的热门视频 JSON 数据中提取出我们关心的字段
        :param raw_data: 原始 JSON 数据（字典格式）
        :return: 结构化的热门视频列表，每个视频是一个字典
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
                "发布时间": entry.get("pubdate"),
                "视频链接": f"https://www.bilibili.com/video/{entry.get('bvid')}",
                "封面链接": entry.get("pic"),
                "时长": entry.get("duration"),
                "pub_timestamp": entry.get("pubdate")
            }
            items.append(item)
        return items