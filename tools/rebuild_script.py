# -*- coding: utf-8 -*-
"""把已发布那一期的「语音逐字稿」还原出来。

背景：tts_script 由 summarizer._build_spoken_script 确定性拼装，但它本身没落库，
reports.json 里只留了前 300 字。所以想给谁一份「音频里到底念了什么」，
过去只能靠听写——听写出来的专有名词必然是错的。

这个脚本换个思路：用 markdown_content 里已存的条目标题/摘要/解读，把
collected_data 还原出来，再调同一个拼装函数重放一遍，逐字对齐。
reports.json 里存的前 300 字就是免费的自校验，对不上会直接报 MISMATCH，
不会悄悄给出一份读起来很顺、其实不是当天原稿的东西。

用法：
    python tools/rebuild_script.py                # 最新一期
    python tools/rebuild_script.py 2026-11-10     # 指定日期
    python tools/rebuild_script.py 2026-11-10 -o 逐字稿.md
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.summarizer import NewsSummarizer  # noqa: E402
from app.tts_engine import TTSEngine  # noqa: E402

LABEL2DOMAIN = {
    "钱的价格": "money",
    "你的钱袋子": "market",
    "大家敢不敢花钱": "demand",
    "生意好不好做": "business",
    "技术在往哪走": "tech",
}


def parse_markdown(md: str):
    """从 markdown 报告里还原 AI / 一人公司 / 宏观三组条目。"""
    ai, opc, macro = [], [], []
    for block in re.split(r"\n### ", md):
        head = block.split("\n", 1)[0].strip()

        m = re.match(r"📌\s*【(AI Agent|一人公司)】(.*)", head)
        if m:
            cat, title = m.group(1), m.group(2).strip()
            summ = re.search(r"\*\*① 一句话内容摘要\*\*：(.*)", block)
            read = re.search(r"\*\*② 人话解读\*\*：(.*)", block)
            item = {
                "title": title,
                "summary": (summ.group(1).strip() if summ else ""),
                "is_fallback": False,
            }
            if read:
                # 有解读的条目当初走的是 why_matter 直出，不是规则库
                item["why_matter"] = read.group(1).strip()
                item["is_frontier"] = True
            (ai if cat == "AI Agent" else opc).append(item)
            continue

        m = re.match(r"【(钱的价格|你的钱袋子|大家敢不敢花钱|生意好不好做|技术在往哪走)】(.*)", head)
        if m:
            label, title = m.group(1), m.group(2).strip()
            macro.append({"title": title, "domain": LABEL2DOMAIN[label], "domain_label": label})
    return ai, opc, macro


def build(date_str: str = "") -> tuple:
    data = json.loads((ROOT / "docs/data/reports.json").read_text(encoding="utf-8"))
    rec = next((r for r in data if date_str and r.get("date_str") == date_str), data[0])
    md = rec["markdown_content"]
    ai, opc, macro = parse_markdown(md)

    def count_block(name: str) -> int:
        m = re.search(rf"【{name}[^】]*】（共 (\d+) 条）", md)
        return int(m.group(1)) if m else 0

    collected = {
        "AI Agent": ai,
        "一人公司": opc,
        "宏观大势": macro,
        "权威要闻": [{}] * count_block("权威要闻"),
        "参考消息": [{}] * count_block("参考消息"),
        "新浪财经": [{}] * count_block("新浪财经"),
    }

    s = NewsSummarizer.__new__(NewsSummarizer)
    s.last_chapters = []
    script = s._build_spoken_script(
        rec["date_str"], rec["quote_of_the_day"], rec.get("lead_title") or "",
        "", "", "", "", "",  # 案例段留空：有案例的那天这里会 MISMATCH，见下面说明
        collected,
    )

    # 自校验：前 300 字必须和当初落库的摘要一字不差
    ok = (script[:300] + "...") == rec.get("summary_text")

    # 章节文本再走一遍 TTS 前的清洗（去掉链接、把 API 之类换成中文读法），
    # 这样稿子里印的就是真被念出来的字，而不是带 https:// 的原始素材。
    engine = TTSEngine.__new__(TTSEngine)
    chapters = [
        {"label": c["label"], "text": engine._optimize_text_for_podcast(c["text"])}
        for c in s.last_chapters
    ]
    return rec, chapters, ok


def to_markdown(rec: dict, chapters: list) -> str:
    """按章节切段，前面加时间轴，读起来像一份能对稿的样子。

    时间轴算法与 build_daily 里给前端做章节跳转的算法完全一致：
    TTS 是整段一次合成的，拿不到逐段真实时间戳，按字数占比换算，误差几秒内。
    """
    total_chars = sum(len(re.sub(r"\s+", "", c["text"])) for c in chapters) or 1
    duration = rec.get("audio_duration") or 0
    cursor = 0
    lines = [
        f"# {rec['date_str']} 播报逐字稿（音频全文）",
        "",
        f"> 音频 {rec.get('audio_duration_str', '?')} · {rec.get('created_at', '')} 生成"
        f" · {rec.get('item_count', '?')} 条素材 · {len(chapters)} 个章节",
        "> 以下即 edge-tts 实际朗读的文本，含开场白、过渡句与结尾。",
        "",
    ]
    for ch in chapters:
        chars = len(re.sub(r"\s+", "", ch["text"]))
        start = int(round(duration * cursor / total_chars))
        cursor += chars
        lines.append(f"## {start // 60:02d}:{start % 60:02d} {ch['label']}")
        lines.append("")
        lines.append(ch["text"].strip())
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default="", help="YYYY-MM-DD，默认最新一期")
    ap.add_argument("-o", "--out", default="", help="输出路径，默认只打印")
    args = ap.parse_args()

    rec, chapters, ok = build(args.date)
    if not ok:
        print("[WARN] 前 300 字对不上，当天可能有案例段或被手工改过，这份稿子不能当原文用。",
              file=sys.stderr)
    md = to_markdown(rec, chapters)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        chars = sum(len(re.sub(r"\s+", "", c["text"])) for c in chapters)
        state = "通过" if ok else "未通过"
        print(f"已写出 {args.out}（{chars} 字，自校验 {state}）")
    else:
        print(md)


if __name__ == "__main__":
    main()
