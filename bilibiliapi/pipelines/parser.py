class Parser:
    """把 B站接口返回的原始 JSON 转成项目需要的字段列表。"""

    @staticmethod
    def _parse_video_entry(entry):
        return {
            "aid": entry.get("aid"),
            "bvid": entry.get("bvid"),
            "cid": entry.get("cid"),
            "视频标题": entry.get("title"),
            "UP主": entry.get("owner", {}).get("name"),
            "播放量": entry.get("stat", {}).get("view"),
            "弹幕数": entry.get("stat", {}).get("danmaku"),
            "评论数": entry.get("stat", {}).get("reply"),
            "点赞数": entry.get("stat", {}).get("like"),
            "投币数": entry.get("stat", {}).get("coin"),
            "收藏数": entry.get("stat", {}).get("favorite"),
            "分区": entry.get("tname"),
            "pub_date": entry.get("pubdate"),
            "视频链接": f"https://www.bilibili.com/video/{entry.get('bvid')}",
            "封面链接": entry.get("pic"),
            "时长": entry.get("duration"),
        }

    @staticmethod
    def parse_popular_items(raw_data):
        """
        从热门视频 JSON 数据中提取关心的字段。

        返回值是列表，列表中的每个元素是一条视频记录。
        """
        items = []

        for entry in raw_data:
            items.append(Parser._parse_video_entry(entry))

        return items

    @staticmethod
    def parse_ranking_items(raw_data, rid=0, ranking_type="all", fetched_at=None):
        """从 ranking/v2 返回列表中提取视频字段和榜单字段。"""
        items = []
        total_count = len(raw_data)

        for index, entry in enumerate(raw_data, start=1):
            score = entry.get("score")
            if not score:
                score = (total_count - index + 1) * 100

            item = Parser._parse_video_entry(entry)
            item.update({
                "榜单分区ID": rid,
                "榜单类型": ranking_type,
                "榜单排名": index,
                "榜单分数": score,
                "榜单抓取时间": fetched_at,
            })
            items.append(item)

        return items
