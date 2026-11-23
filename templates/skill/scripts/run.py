"""〔このスクリプトが何をするか。1 文〕

    python -I <このスキルのフォルダ>/scripts/run.py 〔引数〕

入力: 〔読むもの〕
出力: 〔書くもの、または標準出力に出すもの〕
失敗したとき: 理由を出して、終了コード 1 で止まる。
追加のライブラリは使わない (Python 3.9 以上の標準ライブラリだけ)。
ファイル名は何をするかが分かる名前に変える (例: parse_map.py)。
"""
import argparse
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="〔入力のファイル〕")
    args = parser.parse_args()
    path = pathlib.Path(args.path)
    if not path.is_file():
        # 失敗は AI に任せず、ここで理由を出して止める
        sys.exit(f"入力のファイルがない: {path}")
    # 〔ここに処理を書く。決まった数値には、なぜその値かをコメントで書く〕


if __name__ == "__main__":
    main()
