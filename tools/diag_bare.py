# -*- coding: utf-8 -*-
"""
诊断「裸标题」：一条 AI / 一人公司新闻，播出去只有标题、没有事实。

    python tools/diag_bare.py 2026-11-23

输出每条的三层原料（summary / detail / raw_text）长度，以及
描述句、事实句两层兜底各自能不能捞到东西。用来回答一个问题：
裸标题是因为「源头没正文」，还是「正文里有，被判据刷掉了」。
两种原因对应两种改法，猜错方向改一年也改不好。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.collector import collector, SeenHistory
from app import summarizer as S


async def main(date_str: str) -> None:
    hist = SeenHistory()
    data = await collector.collect_all(date_str, hist, hist)

    rows = []
    for cat in ("AI Agent", "一人公司"):
        for it in data.get(cat, []) or []:
            if not (it.get("title") or "").strip():
                continue
            if it.get("is_fallback"):
                continue
            t_raw = it["title"]
            s_raw = (it.get("summary") or "").strip()
            d_raw = (it.get("detail") or "").strip()
            r_raw = (it.get("raw_text") or "").strip()
            s_ok = bool(s_raw) and not S._summary_echoes_title(t_raw, s_raw) \
                and not S._summary_offtopic(t_raw, s_raw)
            if not s_ok:
                desc = S._describe_from_raw(it)
            else:
                desc = "-"
            facts = S._facts_from_raw(it) if not d_raw else "-"
            rows.append({
                "cat": cat, "title": t_raw, "src": it.get("source_name", ""),
                "s": len(s_raw), "d": len(d_raw), "r": len(r_raw),
                "s_ok": s_ok, "desc": desc, "facts": facts,
                "reading": S.targeted_reading(cat, t_raw, s_raw),
            })

    bare = [r for r in rows if not r["s_ok"] and not r["desc"] and not r["facts"]]
    print(f"总条目 {len(rows)}，其中三层全空（裸标题） {len(bare)}")
    no_raw = [r for r in bare if r["r"] < 60]
    has_raw = [r for r in bare if r["r"] >= 60]
    print(f"  其中 raw_text<60 字（源头没正文）: {len(no_raw)}")
    print(f"  其中 raw_text>=60 字（有正文但没捞到）: {len(has_raw)}")

    print("\n--- 裸标题明细 ---")
    for r in bare:
        flag = "无正文" if r["r"] < 60 else f"正文{r['r']}字"
        print(f"[{r['cat']}] {r['title'][:40]} | {r['src']} | {flag} | "
              f"reading={'有' if r['reading'] else '无'}")

    print("\n--- 有正文却没捞到（改造重点）---")
    for r in has_raw[:12]:
        print(f"* {r['title'][:36]} | {r['src']} | raw {r['r']} 字")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "2026-11-24"))
