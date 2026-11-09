import os
import re
import json
import shutil
import asyncio
import datetime
import email.utils
import httpx
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


# 快照用的腾讯代码：机房 IP 用 Python 访问东财会被拒，腾讯这组稳定，
# 而且境外指数、A股指数一次就能取全（黄金腾讯不提供，用新浪补）
TENCENT_QUOTES = [
    ("usDJI", "道琼斯"),
    ("usIXIC", "纳斯达克"),
    ("usINX", "标普500"),
    ("sh000001", "上证指数"),
    ("sz399006", "创业板指"),
]
MARKET_ORDER = ["道琼斯", "纳斯达克", "标普500", "上证指数", "创业板指", "黄金"]


def _parse_tencent_quotes(text: str) -> list:
    """v_usDJI="200~道琼斯~.DJI~51285.73~...~-0.46~..."，3 是现价、32 是涨跌幅"""
    items = []
    for code, name in TENCENT_QUOTES:
        m = re.search(rf'v_{code}="([^"]*)"', text or "")
        if not m:
            continue
        f = m.group(1).split("~")
        try:
            price = float(f[3])
            pct = float(f[32])
        except (ValueError, IndexError):
            continue
        items.append({"name": name, "price": round(price, 2), "pct": round(pct, 2)})
    return items


async def _fetch_gold(client: httpx.AsyncClient) -> dict:
    """腾讯没有黄金，用新浪的 hf_GC（0 现价、7 昨结算），自己算涨跌幅"""
    try:
        resp = await client.get("https://hq.sinajs.cn/list=hf_GC",
                                headers={"Referer": "https://finance.sina.com.cn"})
        m = re.search(r'hq_str_hf_GC="([^"]*)"', resp.text)
        if not m:
            return {}
        f = m.group(1).split(",")
        price = float(f[0])
        prev = float(f[7]) if len(f) > 7 and f[7] else price
        pct = (price - prev) / prev * 100 if prev else 0.0
        return {"name": "黄金", "price": round(price, 2), "pct": round(pct, 2)}
    except Exception:
        return {}


async def write_market_snapshot() -> None:
    """
    生成一份收盘行情快照（docs/data/market.json）。
    页面优先实时拉接口；接口连不上就退回这份快照，
    不至于让「唯一需要看」的行情模块整个消失。
    """
    items = []
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            codes = ",".join(c for c, _ in TENCENT_QUOTES)
            resp = await client.get(f"https://qt.gtimg.cn/q={codes}")
            items = _parse_tencent_quotes(resp.content.decode("gbk", "ignore"))
            gold = await _fetch_gold(client)
            if gold:
                items.append(gold)
    except Exception as e:
        print(f"  行情快照抓取失败（不影响早报生成）: {type(e).__name__}")

    if not items:
        print("  行情快照为空，跳过写入")
        return

    by_name = {it["name"]: it for it in items}
    ordered = [by_name[n] for n in MARKET_ORDER if n in by_name]

    cst = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    payload = {"updated": cst.strftime("%Y-%m-%d %H:%M"), "items": ordered}
    (DOCS_DATA_DIR / "market.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  行情快照已写入（{len(ordered)} 个品种）")


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

    # 无论本期是否重跑，都刷新一次收盘行情快照，给页面做兜底
    await write_market_snapshot()

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
    # 跨期去重：把最近几期已经播过的条目喂给采集器，避免「昨天念过的今天再念一遍」。
    # 只回看 5 期：再往前的内容对「今天的新闻」已无参考价值，反而可能把可用素材滤空。
    history_episodes = 5
    hist_titles, hist_urls = [], []
    for rec in existing_reports[:history_episodes]:
        if rec.get("date_str") == date_str:
            continue  # 当天重跑时不排除自己，否则重跑会把自己全部滤掉
        for s in (rec.get("sources") or []):
            if s.get("title"):
                hist_titles.append(s["title"])
            if s.get("url"):
                hist_urls.append(s["url"])

    from app.collector import SeenHistory
    history = SeenHistory(hist_titles, hist_urls)

    # 兜底观点、案例、金句这三样是「会反复出现」的东西，判断有没有用过必须看全部历史。
    # 只看最近 5 期的话，第 6 天就会把同一句话原样端上来——这正是听众说「似曾相识」的来源之一。
    all_titles, all_urls, all_leads, all_quotes = [], [], [], []
    for rec in existing_reports:
        if rec.get("date_str") == date_str:
            continue
        for s in (rec.get("sources") or []):
            if s.get("title"):
                all_titles.append(s["title"])
            if s.get("url"):
                all_urls.append(s["url"])
        if rec.get("lead_title"):
            all_leads.append(rec["lead_title"])
        q = (rec.get("category_summary") or {}).get("今日金句")
        if q:
            all_quotes.append(q)
    all_history = SeenHistory(all_titles, all_urls)

    print(f"\n[1/4] 正在抓取 AI、一人公司、时政与财经要闻"
          f"（已载入最近 {history_episodes} 期共 {len(hist_titles)} 条历史标题做跨期去重；"
          f"另有 {len(all_titles)} 条全量历史用于避免旧观点、旧案例重播）...")
    collected_data = await collector.collect_all(date_str, history, all_history)

    # 打印各板块实际取到的条数，便于在 Actions 日志里一眼看出「今天到底是真没新闻还是被滤空了」
    for cat, items in collected_data.items():
        names = sorted({it.get("source_name", "") for it in items})
        print(f"    {cat}: {len(items)} 条 {names if names else ''}")

    # 2. 生成调查报道与播客文稿
    print("\n[2/4] 正在生成深度调查与通俗播客聊天风讲稿...")
    title, lead_title, markdown_content, tts_script, sources, cat_summary = await summarizer.generate_report(
        date_str, collected_data, all_leads, all_quotes
    )
    print(f"    本期主推案例: {lead_title or '（今日无真实新案例，已跳过该段）'}")

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

    # 章节时间轴：TTS 是整段一次合成的，拿不到逐段真实时间戳，
    # 按各段字数占比换算成秒，误差在几秒内，够用来做章节跳转。
    chapters = []
    raw_chapters = getattr(summarizer, "last_chapters", []) or []
    if raw_chapters:
        total_chars = sum(len(re.sub(r"\s+", "", c["text"])) for c in raw_chapters) or 1
        cursor = 0
        for c in raw_chapters:
            chars = len(re.sub(r"\s+", "", c["text"]))
            chapters.append({
                "label": c["label"],
                "start": int(round(duration_sec * cursor / total_chars)),
            })
            cursor += chars
        if chapters:
            chapters[0]["start"] = 0

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
        "chapters": chapters,
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
