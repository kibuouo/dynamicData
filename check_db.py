import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "data" / "cleaned" / "bilibili_data.db"


def quote_identifier(identifier):
    return '"' + str(identifier).replace('"', '""') + '"'


def main():
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        print("请先运行: python -m bilibiliapi")
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print("数据库中的表：")
        for table in tables:
            print(table[0])

        for table in tables:
            table_name = table[0]
            print(f"\n表 {table_name} 的字段：")
            cursor.execute(f"PRAGMA table_info({quote_identifier(table_name)});")
            columns = cursor.fetchall()

            for col in columns:
                print(col)


if __name__ == "__main__":
    main()
