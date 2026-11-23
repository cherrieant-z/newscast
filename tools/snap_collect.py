"""把一次真实采集结果落成本地 JSON，方便离线反复调口播稿。

线上每跑一次采集要几分钟、还要网络，调稿子时不可能每次都重抓。
用法：python tools/snap_collect.py 2026-11-11 [输出路径]

第三个参数给 reports.json 时，会按近十期算出 GitHub 选题的同类压制名单，
跟线上一样——这里不传的话「GitHub 项目」这一段是另一套逻辑选出来的，
照着它调稿子等于在调一个线上不存在的东西。
"""
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, ".")
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
from app.collector import collector, SeenHistory, _gh_domains  # noqa: E402


def recent_domains(exclude_date: str, window: int = 10):
    path = Path("docs/data/reports.json")
    if not path.exists():
        return []
    reports = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for rec in reports[:window]:
        if (rec.get("date_str") or "")[:10] == exclude_date[:10]:
            continue
        for s in (rec.get("sources") or []):
            if s.get("category") != "GitHub 项目":
                continue
            out.extend(_gh_domains(s.get("title", ""),
                                   (s.get("url") or "").rstrip("/").rsplit("/", 1)[-1]))
    return out


async def main(date_str: str, out: str):
    doms = recent_domains(date_str)
    if doms:
        print(f"近十期 GitHub 领域：{doms}")
    data = await collector.collect_all(date_str, SeenHistory(), SeenHistory(),
                                       gh_recent_domains=doms)
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in data.items():
        print(f"{k}: {len(v) if isinstance(v, list) else v}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "tools/_snap.json"))
