import os
import re
import json
import shutil
import asyncio
import datetime
import email.utils
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

def _xml_escape(s: str) -> str:
    """转义 XML 特殊字符，保证 RSS 合法"""
    if not s:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


def _strip_html_text(text: str) -> str:
    """把 Markdown/HTML 内容压成纯文本，用于播客描述"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[#*_`>|]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def write_podcast_xml(reports: list) -> None:
    """
    生成播客订阅 RSS（podcast.xml），可订阅到 Apple Podcasts / 小宇宙 / 喜马拉雅。
    音频 enclosure 用绝对 URL，方便播客 App 直接下载。
    """
    base_url = os.environ.get("PODCAST_BASE_URL", "https://cherrieant-z.github.io/newscast/").rstrip("/") + "/"
    icon_url = base_url + "static/icons/icon.svg"

    items = []
    for r in reports:
        audio_rel = r.get("audio_url", "").split("?")[0]
        audio_abs = base_url + audio_rel.lstrip("/")
        title = r.get("title", "")
        desc = _strip_html_text(r.get("markdown_content", ""))[:400]
        pub = r.get("created_at", "")
        try:
            pub_rfc = email.utils.format_datetime(datetime.datetime.strptime(pub, "%Y-%m-%d %H:%M:%S"))
        except Exception:
            pub_rfc = email.utils.format_datetime(datetime.datetime.utcnow())
        guid = r.get("date_str", "")
        dur = r.get("audio_duration", 0) or 0
        size = r.get("file_size_bytes", 0) or 0
        items.append(
            f"""    <item>\n      <title>{_xml_escape(title)}</title>\n      <description>{_xml_escape(desc)}</description>\n      <enclosure url="{_xml_escape(audio_abs)}" length="{size}" type="audio/mpeg"/>\n      <guid isPermaLink="false">{_xml_escape(guid)}</guid>\n      <pubDate>{pub_rfc}</pubDate>\n      <itunes:duration>{dur}</itunes:duration>\n    </item>"""
        )

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>搞钱情报 · 每日 AI 与一人公司早报</title>
  <link>{base_url}</link>
  <description>每天早晨，用大白话给你讲全球 AI 动态、一人公司搞钱案例与权威要闻，助力你迅速搞钱。</description>
  <language>zh-cn</language>
  <itunes:author>搞钱情报</itunes:author>
  <itunes:explicit>false</itunes:explicit>
  <itunes:image href="{icon_url}"/>
  <itunes:category text="Technology"/>
  <image>
    <url>{icon_url}</url>
    <title>搞钱情报</title>
    <link>{base_url}</link>
  </image>
{chr(10).join(items)}
</channel>
</rss>
"""
    (DOCS_DIR / "podcast.xml").write_text(rss, encoding="utf-8")
    print(f"  播客 RSS 已生成: {DOCS_DIR / 'podcast.xml'}，共 {len(items)} 期")


def build_case_html(md_text: str) -> str:
    m = re.search(r'## 💰 一人公司搞钱案例深度拆解\s+### 【本期课题】(.*?)(?=---\s*\n## |\n## 🤖|$)', md_text, re.DOTALL)
    if not m:
        return ""
    text = m.group(1).strip()
    sections = re.split(r'\n####\s*', text)
    cards = []
    badges = [
        ('bg-sky-500/20 text-sky-300 border-sky-500/40', '痛点洞察'),
        ('bg-emerald-500/20 text-emerald-300 border-emerald-500/40', '商业模式'),
        ('bg-purple-500/20 text-purple-300 border-purple-500/40', '工具链 SOP'),
        ('bg-amber-500/20 text-amber-300 border-amber-500/40', '变现闭环'),
        ('bg-rose-500/20 text-rose-300 border-rose-500/40', '实操建议')
    ]
    for i, sec in enumerate(sections[1:]):
        lines = sec.strip().split('\n', 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ''
        badge_style, badge_name = badges[i] if i < len(badges) else ('bg-slate-700 text-slate-300 border-slate-600', '拆解')
        body_html = '<br>'.join(line.strip() for line in body.split('\n') if line.strip())
        cards.append(f'''<div class="rounded-2xl bg-slate-900/90 border border-slate-700/80 p-4 space-y-2.5 shadow-sm">
  <div class="flex items-center justify-between gap-2">
    <h4 class="text-[15px] sm:text-[16px] font-semibold text-slate-100 flex items-center gap-1.5 leading-snug">
      <span class="w-1.5 h-1.5 rounded-full bg-sky-400 flex-shrink-0"></span>
      {title}
    </h4>
    <span class="text-[11.5px] px-2 py-0.5 rounded-full border whitespace-nowrap font-medium flex-shrink-0 {badge_style}">{badge_name}</span>
  </div>
  <p class="text-[15px] text-slate-200 leading-[1.8] font-normal">{body_html}</p>
</div>''')
    return '\n'.join(cards)

async def build_today_report():
    # 获取北京时间（UTC+8）当前日期
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    cst_now = utc_now + datetime.timedelta(hours=8)

    # 早报归属日：以北京时间 19:00 为日界。
    # 定时任务实际在凌晨 2~5 点跑，若直接取当天日期，凌晨跑出来的会被记成「当天」，
    # 而它其实是给「今天早上的听众」准备的，一晚生成的内容必须记到次日，
    # 否则用户早上打开看到的是昨天的日期，会以为没更新。
    report_day = cst_now + datetime.timedelta(hours=5)
    date_str = report_day.strftime("%Y-%m-%d")

    print(f"==================================================")
    print(f"  [GitHub Actions Pipeline] 开始生成今日早报与音频")
    print(f"  实际生成时刻: {cst_now.strftime('%Y-%m-%d %H:%M:%S')}（北京时间）")
    print(f"  本期归属日期: {date_str}")
    print(f"  触发方式: {os.getenv('GITHUB_EVENT_NAME', 'local')}")
    print(f"==================================================")

    # 先读取既有存档：判断本期是否已经生成过，避免三个兜底时间点重复合成音频
    reports_file = DOCS_DATA_DIR / "reports.json"
    existing_reports = []
    if reports_file.exists():
        try:
            with open(reports_file, "r", encoding="utf-8") as f:
                existing_reports = json.load(f)
        except Exception:
            existing_reports = []

    # 手动触发（workflow_dispatch / 本地运行）永远强制重生成；定时触发才做幂等跳过
    force = os.getenv("GITHUB_EVENT_NAME", "").strip() in ("", "workflow_dispatch")
    if not force:
        done_rec = next((r for r in existing_reports if r.get("date_str") == date_str), None)
        if done_rec:
            done_audio = Path(str(done_rec.get("audio_url", "")).split("?")[0]).name
            if done_audio and (DOCS_AUDIO_DIR / done_audio).exists():
                print(f"  {date_str} 的早报已于 {done_rec.get('created_at')} 生成且音频完好，本次跳过。")
                return
            print(f"  {date_str} 有记录但音频缺失，继续重新生成。")

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

    # 过滤掉同日期的旧记录
    existing_reports = [r for r in existing_reports if r.get("date_str") != date_str]

    # 提取今日金句（正文里是 `🌟 **「…」**` 格式，需跳过加粗符号等再匹配）
    quote_match = re.search(r'🌟[^「]*「([^」]+)」', markdown_content)
    # 兜底优先用 summarizer 已算好的正确金句，避免正则失配时退回到写死的固定句
    quote = (
        quote_match.group(1)
        if quote_match
        else ((cat_summary or {}).get("今日金句") or "未来属于懂得指挥 AI 军队、把真实问题解决到底的超级个体。")
    )

    # 生成案例卡片 HTML
    case_html = build_case_html(markdown_content)

    # 插入今日新记录到首位
    new_record = {
        "id": int(report_day.strftime("%Y%m%d")),
        "date_str": date_str,
        "title": title,
        "lead_title": lead_title,
        "quote_of_the_day": quote,
        "summary_text": tts_script[:300] + "...",
        "case_html": case_html,
        "markdown_content": markdown_content,
        "audio_url": f"audio/{audio_filename}?v={int(cst_now.timestamp())}",
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
    valid_audio_files = {Path(r["audio_url"].split("?")[0]).name for r in kept_reports if "audio_url" in r}
    for mp3_file in DOCS_AUDIO_DIR.glob("*.mp3"):
        if mp3_file.name not in valid_audio_files:
            try:
                mp3_file.unlink()
                print(f"  已清理超期历史音频: {mp3_file.name}")
            except Exception:
                pass

    # 生成播客订阅 RSS（podcast.xml），支持订阅到 Apple Podcasts / 小宇宙 / 喜马拉雅
    print("\n[5/5] 正在生成播客订阅 RSS (podcast.xml)...")
    write_podcast_xml(kept_reports)

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
