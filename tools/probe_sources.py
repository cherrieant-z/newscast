# -*- coding: utf-8 -*-
"""候选源探活。只抓不写，不动 docs，不烧模型额度。

为什么要单独一个脚本：加源最怕「以为加上了，其实每天都在静默失败」。
2026-11-09 那次 V2EX 四个源全挂，日志里毫无痕迹，一整天的一人公司板块
只剩两条兜底文案。所以任何新源上线前，先在 Actions 里跑一遍这个探活，
看得见条数、看得见样例标题、看得见有多少条真的提到钱，再决定加不加。

用法（本地或 Actions 都行）：
    python tools/probe_sources.py
"""
import asyncio
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.collector import _parse_feed_items  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 「这条真的在讲钱」——决定它值不值得占播报名额
MONEY = ("mrr", "revenue", "paying", "customer", "subscription", "pricing",
         "收入", "营收", "付费", "定价", "订阅", "赚")

CANDIDATES = [
    # --- 基准：已经在用的，探活结果用来做对照 ---
    ("V2EX·分享创造", "https://www.v2ex.com/feed/create.xml"),
    ("Product Hunt", "https://www.producthunt.com/feed"),
    ("少数派", "https://sspai.com/feed"),
    # --- 候选：独立开发者讲收入的社区 ---
    ("Reddit·SideProject", "https://www.reddit.com/r/SideProject/.rss"),
    ("Reddit·microsaas", "https://www.reddit.com/r/microsaas/.rss"),
    ("Reddit·indiehackers", "https://www.reddit.com/r/indiehackers/.rss"),
    ("Reddit·SaaS", "https://www.reddit.com/r/SaaS/.rss"),
    ("Indie Hackers", "https://www.indiehackers.com/feed"),
    ("Indie Hackers·rss", "https://www.indiehackers.com/rss"),
    ("Uneed", "https://www.uneed.best/rss"),
    ("BetaList", "https://betalist.com/feed"),
    # --- 候选：HN 按关键词捞「收入帖」，比 Show HN 更贴钱 ---
    ("HN·MRR", "https://hn.algolia.com/api/v1/search_by_date?query=MRR&tags=story&hitsPerPage=25"),
    ("HN·paying customers",
     "https://hn.algolia.com/api/v1/search_by_date?query=paying%20customers&tags=story&hitsPerPage=25"),
]


async def probe(client: httpx.AsyncClient, name: str, url: str) -> None:
    try:
        r = await client.get(url, timeout=15.0)
    except Exception as e:
        print(f"{name:22s} 异常 {type(e).__name__}: {e}")
        return
    body = r.text or ""
    if r.status_code != 200:
        print(f"{name:22s} HTTP {r.status_code}  ({len(body)}B)")
        return

    if "hn.algolia.com" in url:
        hits = (r.json().get("hits") or [])
        titles = [(h.get("title") or "").strip() for h in hits]
        texts = [(h.get("story_text") or "")[:200] for h in hits]
    else:
        items = _parse_feed_items(body)
        titles = [i["title"] for i in items]
        texts = [i["summary"] for i in items]

    money = sum(
        1 for t, s in zip(titles, texts)
        if any(k in (t + " " + s).lower() for k in MONEY)
    )
    print(f"{name:22s} HTTP 200  {len(body)/1024:.0f}KB  条目 {len(titles):2d}  提到钱 {money:2d}")
    for t in titles[:3]:
        print(f"    · {re.sub(r'\s+', ' ', t)[:70]}")


async def main() -> None:
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as client:
        for name, url in CANDIDATES:
            await probe(client, name, url)


if __name__ == "__main__":
    asyncio.run(main())
