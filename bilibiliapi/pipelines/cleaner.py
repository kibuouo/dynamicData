import pandas as pd


class Cleaner:
    """负责把解析后的列表转成 DataFrame，并做基础清洗。"""

    @staticmethod
    def clean_videos(parsed_data):
        """接收视频列表，返回清洗后的 DataFrame。"""
        if not parsed_data:
            return pd.DataFrame()

        df = pd.DataFrame(parsed_data)

        df["pub_date"] = pd.to_datetime(
            df["pub_date"],
            unit="s",
            errors="coerce",
        )
        df = df.drop_duplicates(subset=["bvid"])
        df = df[df["播放量"].fillna(0) > 0]

        return df
