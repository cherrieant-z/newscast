# -*- coding: utf-8 -*-
"""从本地采集快照重新拼一遍口播稿，不联网。

调稿子的时候最烦的是「改一行字，等两分钟采集」。这个脚本跳过采集，
直接拿 tools/snap_collect.py 存下的 JSON 重拼，改一句看一眼只要两秒。

    python tools/snap_collect.py 2026-11-24 tools/_snap_1124.json
    python tools/regen.py tools/_snap_1124.json 2026-11-24            # 打全文
    python tools/regen.py tools/_snap_1124.json 2026-11-24 -s 宏观     # 只看某一块

只重拼稿子，不做任何网络请求，也不写任何文件。
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.summarizer import summarizer


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("date", nargs="?", default="")
    ap.add_argument("-s", "--section", default="", help="只看章节名包含这个词的块")
    args = ap.parse_args()

    data = json.loads(open(args.snap, encoding="utf-8").read())
    date_str = args.date or "2026-11-24"
    title, lead, md, tts, sources, cs = await summarizer.generate_report(
        date_str, data, [], [])

    if args.section:
        for ch in summarizer.last_chapters:
            if args.section in ch["label"]:
                print(f"--- {ch['label']}（{len(ch['text'])} 字）---")
                print(ch["text"])
        return

    print(tts)
    print(f"\n===== {len(tts)} 字，预计 {len(tts) / 5.86 / 60:.1f} 分钟 =====")
    for ch in summarizer.last_chapters:
        print(f"- {ch['label']}（{len(ch['text'])} 字）")


if __name__ == "__main__":
    asyncio.run(main())
