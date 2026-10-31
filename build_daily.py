import os
import re
import json
import shutil
import asyncio
import datetime
from pathlib import Path
from app.collector import collector
from app.summarizer import summarizer
from app.tts_engine import tts_engine

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
DOCS_AUDIO_DIR = DOCS_DIR / "audio"
DOCS_DATA_DIR = DOCS_DIR / "data"
DOCS_STATIC_DIR = DOCS_DIR / "static"

DOCS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
(DOCS_STATIC_DIR / "icons").mkdir(parents=True, exist_ok=True)

async def build_today_report():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    cst_now = utc_now + datetime.timedelta(hours=8)
    date_str = cst_now.strftime("%Y-%m-%d")
    print(f"==================================================")
    print(f"  [GitHub Actions Pipeline] 开始生成今日早报与音频")
    print(f"  北京时间日期: {date_str}")
    print(f"==================================================")

    print("\n[1/4] 正在抓取 AI Agent, 一人公司, 新浪财经, 参考消息, 学习强国, 喜马拉雅新闻早餐...")
    collected_data = await collector.collect_all(date_str)

    print("\n[2/4] 正在生成深度调查与通俗播客聊天风讲稿...")
    title, lead_title, markdown_content, tts_script, sources, cat_summary = await summarizer.generate_report(date_str, collected_data)

    print("\n[3/4] 正在调用 Edge-TTS 合成普通话高保真播客音频...")
    audio_filename = f"newscast_{date_str}.mp3"
    _, audio_url, duration_sec, duration_str, file_size = await tts_engine.generate_audio(
        tts_script, date_str, output_dir=DOCS_AUDIO_DIR
    )
    print(f"  音频生成成功！时长: {duration_str}, 大小: {file_size / 1024:.1f} KB")

    print("\n[4/4] 正在更新静态站点数据源...")
    reports_file = DOCS_DATA_DIR / "reports.json"
    existing_reports = []
    if reports_file.exists():
        try:
            with open(reports_file, "r", encoding="utf-8") as f:
                existing_reports = json.load(f)
        except Exception:
            existing_reports = []

    # 关键防重：过滤掉当天的旧记录，确保当天只有一条最新数据
    existing_reports = [r for r in existing_reports if r.get("date_str") != date_str]

    quote_match = re.search(r'🌟\s*「([^」]+)」', markdown_content)
    quote = quote_match.group(1) if quote_match else "未来属于懂得指挥 AI 军队、把真实问题解决到底的超级个体。"

    new_record = {
        "id": int(cst_now.strftime("%Y%m%d")),
        "date_str": date_str,
        "title": title,
        "lead_title": lead_title,
        "quote_of_the_day": quote,
        "summary_text": tts_script[:300] + "...",
        "markdown_content": markdown_content,
        "audio_url": f"audio/{audio_filename}",
        "audio_duration": duration_sec,
        "audio_duration_str": duration_str,
        "file_size_bytes": file_size,
        "category_summary": cat_summary,
        "sources": sources,
        "status": "completed",
        "created_at": cst_now.strftime("%Y-%m-%d %H:%M:%S")
    }
    existing_reports.insert(0, new_record)

    MAX_KEEP = 14
    kept_reports = existing_reports[:MAX_KEEP]

    with open(reports_file, "w", encoding="utf-8") as f:
        json.dump(kept_reports, f, ensure_ascii=False, indent=2)

    valid_audio_files = {Path(r["audio_url"]).name for r in kept_reports if "audio_url" in r}
    for mp3_file in DOCS_AUDIO_DIR.glob("*.mp3"):
        if mp3_file.name not in valid_audio_files:
            try:
                mp3_file.unlink()
                print(f"  已清理超期历史音频: {mp3_file.name}")
            except Exception:
                pass

    sync_static_assets()
    print("\n 全流程构建完成！静态站点已准备好部署至 GitHub Pages。")

def sync_static_assets():
    shutil.copy(BASE_DIR / "static" / "index.html", DOCS_DIR / "index.html")
    shutil.copy(BASE_DIR / "static" / "manifest.json", DOCS_DIR / "manifest.json")
    shutil.copy(BASE_DIR / "static" / "sw.js", DOCS_DIR / "sw.js")
    
    icon_src = BASE_DIR / "static" / "icons" / "icon.svg"
    icon_dst = DOCS_STATIC_DIR / "icons" / "icon.svg"
    if icon_src.exists():
        shutil.copy(icon_src, icon_dst)

if __name__ == "__main__":
    asyncio.run(build_today_report())
