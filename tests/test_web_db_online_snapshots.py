import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from bilibiliapi.web import db


class OnlineSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "bilibili_data.db"

        with closing(sqlite3.connect(db.DB_PATH)) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE popular_videos (
                        aid INTEGER,
                        bvid TEXT,
                        cid INTEGER,
                        "视频标题" TEXT,
                        "UP主" TEXT,
                        "分区" TEXT,
                        pub_date TEXT,
                        "视频链接" TEXT,
                        "封面链接" TEXT,
                        "时长" INTEGER
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO popular_videos
                    (aid, bvid, cid, "视频标题", "UP主", "分区", pub_date, "视频链接", "封面链接", "时长")
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (1, "BV_LOW", 11, "旧高在线视频", "UP A", "动画", "", "", "", 120),
                        (2, "BV_HIGH", 22, "最新高在线视频", "UP B", "音乐", "", "", "", 160),
                        (3, "BV_MID", 33, "最新中在线视频", "UP C", "游戏", "", "", "", 180),
                    ],
                )

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_query_online_ranking_uses_latest_snapshot_batch(self):
        db.save_online_snapshots(
            [
                {"bvid": "BV_LOW", "cid": 11, "aid": 1, "count": 999},
            ],
            fetched_at="2026-06-02 10:00:00",
        )
        inserted = db.save_online_snapshots(
            [
                {"bvid": "BV_HIGH", "cid": 22, "aid": 2, "count": 88},
                {"bvid": "BV_MID", "cid": 33, "aid": 3, "count": 55},
                {"bvid": "BV_BAD", "cid": 44, "aid": 4, "count": None},
            ],
            fetched_at="2026-06-02 10:05:00",
        )

        ranking = db.query_online_ranking(limit=5)

        self.assertEqual(inserted, 2)
        self.assertEqual([item["bvid"] for item in ranking], ["BV_HIGH", "BV_MID"])
        self.assertEqual(ranking[0]["在线人数"], 88)
        self.assertEqual(ranking[0]["视频标题"], "最新高在线视频")


if __name__ == "__main__":
    unittest.main()
