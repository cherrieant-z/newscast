import asyncio
import datetime
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal, DailyReport
from app.collector import collector
from app.summarizer import summarizer
from app.tts_engine import tts_engine

scheduler = AsyncIOScheduler()
is_generating = False

async def run_daily_pipeline(force: bool = False) -> DailyReport:
    """
    全流程执行：数据采集 -> 深度调查分析与格式化 -> TTS 语音合成 -> 数据库归档
    """
    global is_generating
    if is_generating and not force:
        print("[Scheduler] 任务正在进行中，跳过重复执行。")
        return None

    is_generating = True
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    print(f"\n[Pipeline] 开始执行每日调查新闻与语音生成任务: 日期 = {date_str}")

    try:
        # 1. 采集数据
        print("[Pipeline Step 1/4] 正在抓取 AI, OPC, 国际经济, YouTube, X, TikTok 重点资讯...")
        collected = await collector.collect_all()

        # 2. 生成调查报道与 Markdown 摘要
        print("[Pipeline Step 2/4] 正在生成深度调查报道与结构化 Markdown...")
        title, lead_title, md_content, tts_script, sources, cat_summary = await summarizer.generate_report(date_str, collected)

        # 3. 高保真普通话语音合成
        print(f"[Pipeline Step 3/4] 正在调用 TTS 引擎合成语音播报 (音色: {settings.TTS_VOICE})...")
        audio_path, audio_url, duration_sec, duration_str, file_size = await tts_engine.generate_audio(tts_script, date_str)
        print(f"[Pipeline] 音频生成完毕: 耗时约 {duration_str}, 大小 {file_size / 1024:.1f} KB")

        # 4. 写入 SQLite 数据库
        print("[Pipeline Step 4/4] 正在持久化元数据至 SQLite 数据库...")
        async with AsyncSessionLocal() as session:
            # 检查当日是否已存在，存在则更新，不存在则新建
            stmt = select(DailyReport).where(DailyReport.date_str == date_str)
            result = await session.execute(stmt)
            report = result.scalar_one_or_none()

            if report:
                report.title = title
                report.lead_title = lead_title
                report.summary_text = tts_script[:300] + "..."
                report.markdown_content = md_content
                report.audio_path = audio_path
                report.audio_url = audio_url
                report.audio_duration = duration_sec
                report.audio_duration_str = duration_str
                report.file_size_bytes = file_size
                report.category_summary_json = json.dumps(cat_summary, ensure_ascii=False)
                report.sources_json = json.dumps(sources, ensure_ascii=False)
                report.status = "completed"
                report.created_at = datetime.datetime.utcnow()
            else:
                report = DailyReport(
                    date_str=date_str,
                    title=title,
                    lead_title=lead_title,
                    summary_text=tts_script[:300] + "...",
                    markdown_content=md_content,
                    audio_path=audio_path,
                    audio_url=audio_url,
                    audio_duration=duration_sec,
                    audio_duration_str=duration_str,
                    file_size_bytes=file_size,
                    category_summary_json=json.dumps(cat_summary, ensure_ascii=False),
                    sources_json=json.dumps(sources, ensure_ascii=False),
                    status="completed",
                    created_at=datetime.datetime.utcnow()
                )
                session.add(report)

            await session.commit()
            await session.refresh(report)
            print(f"[Pipeline] 成功完成并已入库！ID: {report.id}, Title: {report.title}")
            return report

    except Exception as e:
        print(f"[Pipeline Error] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        is_generating = False

def setup_scheduler():
    """
    配置每天早上 06:00 自动触发任务
    """
    trigger = CronTrigger(
        hour=settings.SCHEDULE_HOUR,
        minute=settings.SCHEDULE_MINUTE,
        timezone="Asia/Shanghai"
    )
    scheduler.add_job(
        run_daily_pipeline,
        trigger=trigger,
        id="daily_news_job",
        name="每日早晨6点调查新闻与语音生成任务",
        replace_existing=True
    )
    scheduler.start()
    print(f"[Scheduler] 定时调度服务已启动，每天 {settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d} (Asia/Shanghai) 准时执行！")
