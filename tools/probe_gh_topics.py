"""
探测 GitHub topic 的有效性。

新增选题领域前必须先跑这个：topic 名字写错（比如 topic:document 实际不存在）
时，搜索接口不报错，只是返回 0 条——看起来像「这个领域没项目」，实际是
拼错了。这份清单就是用来把「真没有」和「拼错了」分开。

只查 stars:>1000 一档就够判断名字对不对。不带 token 有限速，
二十个 topic 要跑两分钟，所以默认只跑前十个；要全测加 --all。

用法：python tools/probe_gh_topics.py [--all]
"""
import asyncio
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CANDIDATES = [
    "ai-agents", "self-hosted", "knowledge-base", "scraper", "document",
    "productivity", "marketing", "pdf", "translation", "note-taking",
    "local-first", "no-code", "writing", "summarization", "workflow",
    "vibe-coding", "content-creation", "ebook", "newsletter", "telegram-bot",
]

QUERY = "stars:>1000"


async def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    gap = 0.8 if token else 6.2
    names = CANDIDATES if "--all" in sys.argv else CANDIDATES[:10]
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
        for i, tp in enumerate(names):
            if i:
                await asyncio.sleep(gap)
            try:
                r = await c.get(
                    "https://api.github.com/search/repositories",
                    params={"q": f"topic:{tp} {QUERY}", "per_page": 1},
                    headers=headers)
            except Exception as e:
                print(f"{tp:22s} ERR {e}")
                continue
            if r.status_code != 200:
                print(f"{tp:22s} HTTP {r.status_code}")
                continue
            n = (r.json() or {}).get("total_count", 0)
            print(f"{tp:22s} {n:>6d}  {'可用' if n else '无结果（可能拼错）'}")


asyncio.run(main())
