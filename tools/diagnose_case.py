"""案例诊断：在生产出口上跑一遍真实采集，看今天会挑出什么案例、为什么。

本地抓 V2EX 走代理经常 502，而生产（GitHub Actions）是直连，两边看到的东西
不一样。「明天案例会不会好」这个问题，只有生产侧的数据能回答。

只读：不写 docs、不合成音频、不提交。
用法：python tools/diagnose_case.py 2026-11-12
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.collector import SeenHistory, collector  # noqa: E402
from app.llm import llm  # noqa: E402
from app.summarizer import (  # noqa: E402
    NewsSummarizer,
    _case_has_substance,
    _case_kind,
    _case_ok,
    _has_ops_number,
    _payer_signal,
    _spoken_len,
)


async def main(date_str: str) -> None:
    print(f"=== 案例诊断 {date_str} ===")
    print(f"模型可用: {llm.enabled}")

    data = await collector.collect_all(date_str, SeenHistory(), SeenHistory())
    items = data.get("一人公司") or []
    print(f"\n一人公司候选 {len(items)} 条：")
    for it in items:
        raw = it.get("raw_text") or ""
        summary = it.get("summary") or ""
        print(f"- {it.get('title', '')[:44]}")
        print(f"    payer={_payer_signal(raw)}  有运营数字={_has_ops_number(raw)}  "
              f"raw={len(raw)}字  summary={len(summary)}字")

    print("\n--- 挑选过程 ---")
    s = NewsSummarizer()
    case = await s._pick_case(date_str, [], items)

    if not case:
        print(">>> 今天没有案例")
        return

    kind = _case_kind(case)
    has_material = _case_has_substance(
        case.get("pain_point", ""), case.get("model", ""),
        rev=case.get("revenue", ""), kind=kind)
    print(f">>> 选中: {case.get('title')}")
    print(f"    口径: {'赚钱案例' if kind == 'money' else '反面样本'}")
    print(f"    第一句合格: {_case_ok(case)}")
    print(f"    有实料: {has_material}")
    for key in ("what", "who_made", "pain_point", "model", "revenue",
                "startup", "barrier", "guide"):
        value = case.get(key) or ""
        print(f"    {key}({_spoken_len(value)}): {value}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "2026-11-12"))
