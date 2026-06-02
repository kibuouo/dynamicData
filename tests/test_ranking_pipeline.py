import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import pandas as pd

from bilibiliapi.pipelines.parser import Parser
from bilibiliapi.pipelines.saver import Saver
from bilibiliapi.web import db


class RankingParserTests(unittest.TestCase):
    def test_parse_ranking_items_adds_rank_metadata(self):
        raw_items = [
            {
                "aid": 1001,
                "bvid": "BV_RANK_1",
                "cid": 2001,
                "title": "榜单第一",
                "owner": {"name": "UP A"},
                "stat": {
                    "view": 9000,
                    "danmaku": 90,
                    "reply": 35,
                    "like": 800,
                    "coin": 70,
                    "favorite": 60,
                },
                "tname": "动画",
                "pubdate": 1700000000,
                "pic": "https://example.com/cover.jpg",
                "duration": 180,
                "score": 123456,
            }
        ]

        parsed = Parser.parse_ranking_items(
            raw_items,
            rid=0,
            ranking_type="all",
            fetched_at="2026-06-02 12:00:00",
        )

        self.assertEqual(parsed[0]["bvid"], "BV_RANK_1")
        self.assertEqual(parsed[0]["视频标题"], "榜单第一")
        self.assertEqual(parsed[0]["榜单分区ID"], 0)
        self.assertEqual(parsed[0]["榜单类型"], "all")
        self.assertEqual(parsed[0]["榜单排名"], 1)
        self.assertEqual(parsed[0]["榜单分数"], 123456)
        self.assertEqual(parsed[0]["榜单抓取时间"], "2026-06-02 12:00:00")
        self.assertEqual(parsed[0]["评论数"], 35)
        self.assertEqual(parsed[0]["收藏数"], 60)

    def test_parse_ranking_items_uses_rank_score_when_api_score_is_zero(self):
        raw_items = [
            {
                "aid": 1001,
                "bvid": "BV_RANK_1",
                "cid": 2001,
                "title": "榜单第一",
                "owner": {"name": "UP A"},
                "stat": {"view": 9000},
                "tname": "动画",
                "pubdate": 1700000000,
                "duration": 180,
                "score": 0,
            },
            {
                "aid": 1002,
                "bvid": "BV_RANK_2",
                "cid": 2002,
                "title": "榜单第二",
                "owner": {"name": "UP B"},
                "stat": {"view": 7000},
                "tname": "音乐",
                "pubdate": 1700000000,
                "duration": 210,
                "score": 0,
            },
        ]

        parsed = Parser.parse_ranking_items(raw_items)

        self.assertEqual(parsed[0]["榜单分数"], 200)
        self.assertEqual(parsed[1]["榜单分数"], 100)


class RankingStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_dir = Path(self.temp_dir.name)
        self.original_db_path = db.DB_PATH
        db.DB_PATH = self.save_dir / "bilibili_data.db"

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_save_and_query_latest_ranking_videos(self):
        saver = Saver(save_dir=self.save_dir)
        video_df = pd.DataFrame([
            {
                "aid": 1001,
                "bvid": "BV_RANK_1",
                "cid": 2001,
                "视频标题": "榜单第一",
                "UP主": "UP A",
                "分区": "动画",
                "pub_date": "2026-06-01",
                "视频链接": "https://www.bilibili.com/video/BV_RANK_1",
                "封面链接": "",
                "时长": 180,
                "抓取时间": "2026-06-02 12:00:00",
                "播放量": 9000,
                "弹幕数": 90,
                "评论数": 35,
                "点赞数": 800,
                "投币数": 70,
                "收藏数": 60,
                "综合热度": 0.3,
                "疑似异常": 0,
            },
            {
                "aid": 1002,
                "bvid": "BV_RANK_2",
                "cid": 2002,
                "视频标题": "榜单第二",
                "UP主": "UP B",
                "分区": "音乐",
                "pub_date": "2026-06-01",
                "视频链接": "https://www.bilibili.com/video/BV_RANK_2",
                "封面链接": "",
                "时长": 210,
                "抓取时间": "2026-06-02 12:00:00",
                "播放量": 7000,
                "弹幕数": 70,
                "评论数": 28,
                "点赞数": 600,
                "投币数": 50,
                "收藏数": 40,
                "综合热度": 0.2,
                "疑似异常": 0,
            },
        ])
        ranking_df = pd.DataFrame([
            {
                "bvid": "BV_OLD_HIGH",
                "榜单分区ID": 0,
                "榜单类型": "all",
                "榜单排名": 1,
                "榜单分数": 999999,
                "榜单抓取时间": "2026-06-02 11:00:00",
            },
            {
                "bvid": "BV_RANK_1",
                "榜单分区ID": 0,
                "榜单类型": "all",
                "榜单排名": 1,
                "榜单分数": 123456,
                "榜单抓取时间": "2026-06-02 12:00:00",
            },
            {
                "bvid": "BV_RANK_2",
                "榜单分区ID": 0,
                "榜单类型": "all",
                "榜单排名": 2,
                "榜单分数": 65432,
                "榜单抓取时间": "2026-06-02 12:00:00",
            },
        ])

        saver.save_to_sqlite(video_df, db_name="bilibili_data.db", table_name="popular_videos")
        saver.save_ranking_snapshots(ranking_df, db_name="bilibili_data.db")

        rows = db.query_ranking_videos(limit=5)
        summary = db.query_ranking_summary()

        self.assertEqual([row["bvid"] for row in rows], ["BV_RANK_1", "BV_RANK_2"])
        self.assertEqual(rows[0]["视频标题"], "榜单第一")
        self.assertEqual(rows[0]["榜单排名"], 1)
        self.assertEqual(rows[0]["评论数"], 35)
        self.assertEqual(rows[0]["收藏数"], 60)
        self.assertEqual(summary["ranking_video_count"], 2)
        self.assertEqual(summary["max_ranking_score"], 123456)

        with closing(sqlite3.connect(db.DB_PATH)) as conn:
            snapshot_columns = [
                row[1]
                for row in conn.execute("PRAGMA table_info(popular_video_snapshots)")
            ]

        self.assertIn("评论数", snapshot_columns)
        self.assertIn("收藏数", snapshot_columns)


if __name__ == "__main__":
    unittest.main()
