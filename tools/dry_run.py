# -*- coding: utf-8 -*-
"""
干跑一次完整流程，只出文稿不出音频。

    python tools/dry_run.py 2026-11-14

检查「新加一块拼进整期之后听感如何」用它：块数对不对、编号有没有断、
总字数落在几分钟。不合成音频、不写任何文件、不发任何东西。

比 build_daily.py 轻的地方只有一步——跳过 TTS。采集和写作是同一套代码，
所以文稿长什么样，线上就是什么样。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.collector import collector, SeenHistory
from app.summarizer import summarizer


async def main(date_str: str) -> None:
    hist = SeenHistory()
    data = await collector.collect_all(date_str, hist, hist)
    for k, v in data.items():
        if isinstance(v, list):
            print(f"{k}: {len(v)} 条")

    title, lead, md, tts, sources, cs = await summarizer.generate_report(
        date_str, data, [], [])
    print("\n===== 播报稿 =====")
    print(tts)
    est = len(tts) / 5.86 / 60
    print(f"\n===== {len(tts)} 字，预计 {est:.1f} 分钟 =====")
    print("===== 章节 =====")
    for ch in summarizer.last_chapters:
        print(f"- {ch['label']}（{len(ch['text'])} 字）")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "2026-11-14"))
