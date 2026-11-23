"""
离线跑一次 GitHub 选品，看「同类压制」到底把票投给了谁。

用法：
    python tools/probe_gh_pick.py                # 用真实今天
    python tools/probe_gh_pick.py 2026-11-25     # 假装那天（只影响轮换领域）

它读 docs/data/reports.json 里近十期的选品，算出「讲过哪些领域」，
然后完整跑一遍 fetch_github_pick（会真调接口和模型，一两分钟）。
"""
import asyncio
import datetime
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app.collector import NewsCollector, _gh_domains  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def recent_domains(window: int = 10):
    path = os.path.join(ROOT, "docs", "data", "reports.json")
    with open(path, encoding="utf-8") as f:
        reports = json.load(f)
    out = []
    for rec in reports[:window]:
        for s in (rec.get("sources") or []):
            if s.get("category") != "GitHub 项目":
                continue
            out.extend(_gh_domains(
                s.get("title", ""),
                (s.get("url") or "").rstrip("/").rsplit("/", 1)[-1]))
    return out


async def main():
    if len(sys.argv) > 1:
        d = datetime.date.fromisoformat(sys.argv[1])
        real = datetime.date
        # fetch_github_pick 内部用 today() 决定档位和轮换，这里临时替换掉
        class _FakeDate(datetime.date):
            @classmethod
            def today(cls):
                return d
        datetime.date = _FakeDate
    doms = recent_domains()
    print(f"近十期领域标签：{doms}")
    col = NewsCollector()
    async with httpx.AsyncClient(headers=col.headers, timeout=20.0, proxy=col.proxy) as c:
        items = await col.fetch_github_pick(c, None, doms)
    if not items:
        print("今天这块不出（返回空）")
        return
    it = items[0]
    print("\n=== 选中 ===")
    for k in ("title", "gh_name_en", "gh_stars", "gh_tag", "gh_domains"):
        print(f"  {k}: {it.get(k)}")
    print(f"  summary: {it.get('summary')}")
    print(f"  detail : {it.get('detail')}")
    print(f"  you    : {it.get('why_matter')}")
    if len(sys.argv) > 1:
        datetime.date = real


asyncio.run(main())
