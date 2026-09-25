import unittest
from unittest.mock import Mock, patch

from bilibiliapi.cloud_sync import build_capture, collect_capture, upload_capture


def video(bvid="BV1234567890"):
    return {"bvid": bvid, "aid": 1, "cid": 2, "title": "测试", "owner": {"name": "UP"},
            "stat": {"view": 1000, "like": 100, "coin": 10, "favorite": 20, "danmaku": 5, "reply": 2},
            "tname": "科技", "pubdate": 1700000000, "duration": 30}


class CloudSyncTests(unittest.TestCase):
    def test_capture_deduplicates_and_keeps_real_rank_without_inventing_score(self):
        capture = build_capture([video()], [video()], "2026-09-20T00:00:00.000Z")
        self.assertEqual(len(capture["videos"]), 1)
        self.assertEqual(capture["videos"][0]["rank"], 1)
        self.assertIsNone(capture["videos"][0]["score"])
        self.assertAlmostEqual(capture["videos"][0]["heat"], 0.045)

    def test_page_rejection_saves_earlier_pages_as_a_clear_partial_capture(self):
        spider = Mock(page_size=1)
        spider.get_popular_page.side_effect = [{"code": 0, "data": {"list": [video()]}}, {"code": -412}]
        spider.get_ranking.return_value = {"code": 0, "data": {"list": [video()]}}
        capture = collect_capture(2, spider=spider, sleep=lambda _: None)
        self.assertFalse(capture["popularComplete"])
        self.assertTrue(capture["rankingAvailable"])
        self.assertEqual(capture["videos"][0]["rank"], 1)
        self.assertIn("partial 1/200", capture["source"])
        spider.get_ranking.assert_called_once()

    def test_first_page_rejection_preserves_existing_cloud_data(self):
        spider = Mock(page_size=1)
        spider.get_popular_page.return_value = {"code": -352}
        with self.assertRaises(RuntimeError):
            collect_capture(2, spider=spider, sleep=lambda _: None)
        spider.get_ranking.assert_not_called()

    def test_unavailable_ranking_is_explicit_and_no_rank_is_invented(self):
        capture = build_capture([video()], [], "2026-09-20T00:00:00.000Z")
        self.assertFalse(capture["rankingAvailable"])
        self.assertIsNone(capture["videos"][0]["rank"])
        self.assertIn("ranking unavailable", capture["source"])

    @patch("bilibiliapi.cloud_sync.requests.post")
    def test_upload_checks_acknowledgement_and_never_follows_redirects(self, post):
        capture = build_capture([video()], [video()], "2026-09-20T00:00:00.000Z")
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"id": "wrong", "videoCount": 1}
        with self.assertRaises(RuntimeError):
            upload_capture(capture, "https://example.com", "test-secret")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

