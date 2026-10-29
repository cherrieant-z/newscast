import os
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

# 确保目录结构存在
DOCS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
(DOCS_STATIC_DIR / "icons").mkdir(parents=True, exist_ok=True)

async def build_today_report():
    # 获取北京时间（UTC+8）当前日期
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    cst_now = utc_now + datetime.timedelta(hours=8)
    date_str = cst_now.strftime("%Y-%m-%d")
    print(f"==================================================")
    print(f"  [GitHub Actions Pipeline] 开始生成今日早报与音频")
    print(f"  北京时间日期: {date_str}")
    print(f"==================================================")

    # 1. 采集资讯
    print("\n[1/4] 正在抓取 AI, OPC, 国际经济, YouTube, X, TikTok 重点资讯...")
    collected_data = await collector.collect_all()

    # 2. 生成调查报道与播客文稿
    print("\n[2/4] 正在生成深度调查与通俗播客聊天风讲稿...")
    title, lead_title, markdown_content, tts_script, sources, cat_summary = await summarizer.generate_report(date_str, collected_data)

    # 3. 合成高保真 Edge-TTS 音频 (直接写入 docs/audio)
    print("\n[3/4] 正在调用 Edge-TTS 合成普通话高保真播客音频...")
    audio_filename = f"newscast_{date_str}.mp3"
    target_mp3_path = DOCS_AUDIO_DIR / audio_filename
    
    _, audio_url, duration_sec, duration_str, file_size = await tts_engine.generate_audio(
        tts_script, date_str, output_dir=DOCS_AUDIO_DIR
    )
    print(f"  音频生成成功！时长: {duration_str}, 大小: {file_size / 1024:.1f} KB")

    # 4. 更新 docs/data/reports.json
    print("\n[4/4] 正在更新静态站点数据源...")
    reports_file = DOCS_DATA_DIR / "reports.json"
    existing_reports = []
    if reports_file.exists():
        try:
            with open(reports_file, "r", encoding="utf-8") as f:
                existing_reports = json.load(f)
        except Exception:
            existing_reports = []

    # 过滤掉同日期的旧记录
    existing_reports = [r for r in existing_reports if r.get("date_str") != date_str]

    # 插入今日新记录到首位
    new_record = {
        "id": int(cst_now.strftime("%Y%m%d")),
        "date_str": date_str,
        "title": title,
        "lead_title": lead_title,
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

    # 仅保留最近 14 期记录，避免 GitHub 仓库无限膨胀
    MAX_KEEP = 14
    kept_reports = existing_reports[:MAX_KEEP]

    with open(reports_file, "w", encoding="utf-8") as f:
        json.dump(kept_reports, f, ensure_ascii=False, indent=2)

    # 自动清理 14 天之前的旧 MP3 文件
    valid_audio_files = {Path(r["audio_url"]).name for r in kept_reports if "audio_url" in r}
    for mp3_file in DOCS_AUDIO_DIR.glob("*.mp3"):
        if mp3_file.name not in valid_audio_files:
            try:
                mp3_file.unlink()
                print(f"  已清理超期历史音频: {mp3_file.name}")
            except Exception:
                pass

    # 同步静态前端与 PWA 资源到 docs/
    sync_static_assets()
    print("\n 全流程构建完成！静态站点已准备好部署至 GitHub Pages。")

def sync_static_assets():
    # 复制前端 HTML、PWA 文件和图标
    shutil.copy(BASE_DIR / "static" / "index.html", DOCS_DIR / "index.html")
    shutil.copy(BASE_DIR / "static" / "manifest.json", DOCS_DIR / "manifest.json")
    shutil.copy(BASE_DIR / "static" / "sw.js", DOCS_DIR / "sw.js")
    
    icon_src = BASE_DIR / "static" / "icons" / "icon.svg"
    icon_dst = DOCS_STATIC_DIR / "icons" / "icon.svg"
    if icon_src.exists():
        shutil.copy(icon_src, icon_dst)

if __name__ == "__main__":
    asyncio.run(build_today_report())
