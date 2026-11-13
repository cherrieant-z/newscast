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
    # --- 在用：案例第三路（Reddit 长正文）---
    # 2026-11-13 起接入。实测 r/SideProject 稳定 200，25 条里 22 条正文超
    # 300 字，中位数 978 字——是 HN story_text 的两三倍，且天然第一人称。
    ("Reddit·SideProject", "https://www.reddit.com/r/SideProject/.rss"),
    # 轮换板块：一周轮一圈，每天只多付一次请求。连着拉必 429。
    ("Reddit·创业同行", "https://www.reddit.com/r/EntrepreneurRideAlong/.rss"),
    ("Reddit·小微SaaS", "https://www.reddit.com/r/microsaas/.rss"),
    ("Reddit·苦活起家", "https://www.reddit.com/r/sweatystartup/.rss"),
    # --- 候选：还没接，先留着看 ---
    ("HN·MRR", "https://hn.algolia.com/api/v1/search_by_date?query=MRR&tags=story&hitsPerPage=25"),
    ("HN·paying customers",
     "https://hn.algolia.com/api/v1/search_by_date?query=paying%20customers&tags=story&hitsPerPage=25"),
    ("HN·收入帖(已上线)",
     "https://hn.algolia.com/api/v1/search_by_date?query=paying%20customers"
     "&tags=story&numericFilters=points%3E3&hitsPerPage=30"),
    ("HN·pricing",
     "https://hn.algolia.com/api/v1/search_by_date?query=pricing%20experiment"
     "&tags=story&numericFilters=points%3E3&hitsPerPage=30"),
    # YouTube 频道 RSS：不需要 API key，也不吃配额，返回最近 15 条
    # 含标题 + 描述（实测 400~700 字）。链接放这里是为了留个活口：
    # 接不接另说，能不能拿到得先看得见。
    ("YT·IndieHackers", "https://www.youtube.com/feeds/videos.xml"
                        "?channel_id=UCW5YeuERMmlnqo4oq8vwUpg"),
]

# ============================================================
# 已证伪，别再试（2026-11-13 实测）
#
# 小红书  https://www.xiaohongshu.com/explore  200 但整页是登录墙。
#         它没有对外的搜索接口，网页端要登录态 + 每次请求带签名，
#         风控专门盯「不是手机 App 发来的请求」；服务器 IP 抓几次就要验证码，
#         账号还有被封的风险。**自动发现新笔记这条路走不通**，别在上面耗。
#
#         但被分享出来的单条是开放的，这是唯一一条缝：
#         xhslink.cn/o/xxxx → 详情页 → og:description 里就是全文，
#         不用登录，前提是 UA 装成手机（桌面 UA 会掉登录页）。
#         所以小红书走人工投喂：人给链接，tools/xhs_shot.py 负责读全文。
#         2026-11-13 实测一条 973 字的笔记，一次就拿到了。
#
# B站      api.bilibili.com/x/web-interface/search/type  412。
#         要 wbi 签名（两个 key 按时间戳混淆），签名算法会变，
#         维护成本高于它能提供的内容。
#
# Indie Hackers  /feed 和 /rss 都是 404。
#
# Reddit .json  403。.rss 能过，但连着拉第二个板块就 429，
#               所以案例侧改成「固定一个 + 按天轮换一个」。
# ============================================================


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
        one_line = re.sub(r"\s+", " ", t)
        print(f"    · {one_line[:70]}")


async def main() -> None:
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True) as client:
        for name, url in CANDIDATES:
            await probe(client, name, url)


if __name__ == "__main__":
    asyncio.run(main())
