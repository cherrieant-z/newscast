"""把一次真实采集结果落成本地 JSON，方便离线反复调口播稿。

线上每跑一次采集要几分钟、还要网络，调稿子时不可能每次都重抓。
用法：python tools/snap_collect.py 2026-11-11
"""
import asyncio, json, sys
from pathlib import Path

sys.path.insert(0, ".")
from app.collector import collector, SeenHistory  # noqa: E402


async def main(date_str: str, out: str):
    data = await collector.collect_all(date_str, SeenHistory(), SeenHistory())
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in data.items():
        print(f"{k}: {len(v) if isinstance(v, list) else v}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "tools/_snap.json"))
