"""設計書 (Markdown) の機械的に決まる検査をして、気になる所を 1 行 1 件で出す。

    python -I <このスキルのフォルダ>/scripts/check_design.py <設計書.md>

入力: レビューする設計書 1 本 (Markdown、UTF-8)
出力: 標準出力に「種類<TAB>行<TAB>章<TAB>内容」を 1 行 1 件。最後に件数の行。
  種類は 3 つ:
    あいまい   あいまいな言葉が出てきた所 (WORDS の一覧で検索する)
    章番号     章番号の飛び、重なり、並びの乱れ
    要求番号   REQ-xxx が 1 つも書いていない
失敗したとき: 理由を出して、終了コード 1 で止まる (ファイルがない、中身がない、見出しが 1 つもない)。
追加のライブラリは使わない (Python 3.9 以上の標準ライブラリだけ)。
"""
import argparse
import pathlib
import re
import sys

# あいまいな言葉の一覧。いつもの進め方のメモにあった 4 語 (適宜、速やかに、必要に応じて、少ない) に、
# よく出る言葉を仮に足した。「少ない」は「少なくなった」も拾えるよう語幹の「少な」で探す。
# 毎回使う一覧が分かったら、ここを書き換える。
WORDS = [
    "適宜", "速やかに", "必要に応じて", "少な",          # メモにあった言葉
    "多い", "多く", "十分", "なるべく", "できるだけ",    # 仮に足した言葉
    "適切", "随時", "柔軟",
]
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")  # 「1. 概要」「2.1 画面」の番号
REQ = re.compile(r"REQ-\d+")
FENCE = re.compile(r"^\s*```")


def numbers(lines):
    """番号付きの見出しを (行, 番号の列, 見出しの文) で返す。コードの囲みの中は見ない。"""
    out, fenced = [], False
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        m = HEADING.match(line)
        if fenced or not m:
            continue
        n = NUMBER.match(m.group(2))
        if n:
            out.append((i, tuple(int(x) for x in n.group(1).split(".")), m.group(2).strip()))
    return out


def check_chapters(heads):
    """同じ親の中で、番号が 1 から 1 ずつ増えているかを見る。"""
    found, last = [], {}
    for line, num, title in heads:
        parent, n = num[:-1], num[-1]
        prev = last.get(parent, 0)
        label = ".".join(map(str, num))
        if n == prev:
            found.append(("章番号", line, title, f"{label} が重なっている"))
        elif n < prev:
            found.append(("章番号", line, title, f"{label} が前の {prev} より小さい (並びが乱れている)"))
        elif n > prev + 1:
            missing = ".".join(map(str, parent + (prev + 1,)))
            found.append(("章番号", line, title, f"{missing} が飛んでいる ({label} の前)"))
        last[parent] = max(n, prev)
        # 上の章が変わったら、その下の番号は数え直す
        for key in [k for k in last if len(k) > len(num)]:
            del last[key]
    return found


def check_words(lines, heads):
    found, fenced = [], False
    chapter = "(章の前)"
    starts = {line: title for line, _, title in heads}
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if i in starts:
            chapter = starts[i]
            continue
        if fenced or HEADING.match(line):
            continue
        for w in WORDS:
            if w in line:
                found.append(("あいまい", i, chapter, f"「{w}」: {line.strip()}"))
    return found


def main():
    # Windows では標準エラーが cp932 になり、止まった理由が文字化けするので、両方 UTF-8 にする
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="レビューする設計書 (Markdown)")
    args = parser.parse_args()
    path = pathlib.Path(args.path)
    if not path.is_file():
        sys.exit(f"設計書のファイルがない: {path}。パスを確かめて渡し直す")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        sys.exit(f"UTF-8 で読めない: {path}。Markdown (UTF-8) に直してから渡す")
    if not text.strip():
        sys.exit(f"中身がない: {path}。レビューする前に、書いた人に中身を確かめる")
    lines = text.splitlines()
    if not any(HEADING.match(l) for l in lines):
        sys.exit(f"見出し (# で始まる行) が 1 つもない: {path}。章が分からないので、Markdown の見出しがあるか確かめる")
    heads = numbers(lines)
    found = check_chapters(heads) + check_words(lines, heads)
    if not REQ.search(text):
        found.append(("要求番号", 0, "(全体)", "REQ-xxx が 1 つも書いていない"))
    if not heads:
        found.append(("章番号", 0, "(全体)", "番号付きの見出しがない。章番号の検査はしていない"))
    print("種類\t行\t章\t内容")
    for kind, line, chapter, note in sorted(found, key=lambda f: f[1]):
        print(f"{kind}\t{line}\t{chapter}\t{note}")
    print(f"# {len(found)} 件 (あいまい {sum(f[0] == 'あいまい' for f in found)}、"
          f"章番号 {sum(f[0] == '章番号' for f in found)}、要求番号 {sum(f[0] == '要求番号' for f in found)})")


if __name__ == "__main__":
    main()
