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
    pool = data.get("案例候选") or []
    print(f"\n案例专用池 {len(pool)} 条：")
    for it in pool:
        print(f"- [{it.get('published', '')[:10]}] {it.get('title', '')[:70]}")
        print(f"    payer={_payer_signal(it.get('raw_text') or '')}  "
              f"raw={len(it.get('raw_text') or '')}字")

    print(f"\n一人公司候选 {len(items)} 条：")
    for it in items:
        raw = it.get("raw_text") or ""
        summary = it.get("summary") or ""
        print(f"- {it.get('title', '')[:44]}")
        print(f"    payer={_payer_signal(raw)}  有运营数字={_has_ops_number(raw)}  "
              f"raw={len(raw)}字  summary={len(summary)}字")

    print("\n--- 挑选过程（正常：案例池 + 资讯条目）---")
    s = NewsSummarizer()
    case = await s._pick_case(date_str, [], list(items), pool)
    _report(case)

    # 第二遍：假装今天既没有案例池、连那条被选中的译稿也不在，
    # 看会降到哪一档。这一遍回答的是「收入帖断供那天，节目还有没有案例」。
    print("\n--- 假如案例池为空、且没有收入类条目（断供的那天）---")
    picked_url = (case.get("url") or "").split("?")[0].rstrip("/") if case else ""
    rest = [it for it in items
            if not (picked_url and (it.get("url") or "").split("?")[0].rstrip("/") == picked_url)]
    print(f"    剩余候选 {len(rest)} 条")
    case2 = await s._pick_case(date_str, [], rest, [])
    _report(case2)


def _report(case) -> None:
    if not case:
        print(">>> 今天没有案例（三档全空）")
        return

    kind = _case_kind(case)
    label = {"money": "有人付钱", "sample": "没做成", "howto": "讲做法"}.get(kind, kind)
    has_material = _case_has_substance(
        case.get("pain_point", ""), case.get("model", ""),
        rev=case.get("revenue", ""), kind=kind)
    if kind == "howto":
        # 做法档的判据在主流程里多两条：难在哪、今天能做什么。
        # 这里必须用同一套，否则诊断说「没实料」而实际会播，白查一轮。
        has_material = has_material or _spoken_len(case.get("barrier") or "") >= 12 \
            or _spoken_len(case.get("guide") or "") >= 12
    print(f">>> 选中: {case.get('title')}")
    print(f"    口径: {label}")
    print(f"    第一句合格: {_case_ok(case)}")
    print(f"    有实料: {has_material}")
    # 段数比字数更能说明「讲不讲得清」：一期案例段要撑四五分钟，
    # 至少得有六段有内容，光看总字数会被一件事写得很长骗过去。
    filled = 0
    for key in ("what", "who_made", "origin", "how", "pain_point", "model",
                "revenue", "turning", "today", "barrier", "guide"):
        value = case.get(key) or ""
        if _spoken_len(value) >= 12:
            filled += 1
        print(f"    {key}({_spoken_len(value)}): {value}")
    print(f"    有内容的栏位: {filled}/11")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "2026-11-12"))
