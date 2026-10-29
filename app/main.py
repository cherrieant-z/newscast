import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uvicorn

from app.config import settings, STORAGE_DIR, STATIC_DIR
from app.database import init_db, get_db_session, DailyReport
from app.scheduler import setup_scheduler, run_daily_pipeline, is_generating

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    await init_db()
    # 启动 06:00 定时任务调度器
    setup_scheduler()
    
    # 检查数据库是否为空，若为空则在后台自动合成首期简报，开箱即有内容体验
    async with (await get_db_session().__anext__()) as session:
        result = await session.execute(select(DailyReport).limit(1))
        first_record = result.scalar_one_or_none()
        if not first_record:
            print("[Lifespan] 数据库无记录，将在后台自动生成初始首期简报...")
            import asyncio
            asyncio.create_task(run_daily_pipeline())

    yield
    print("[Lifespan] 服务关闭中...")

app = FastAPI(
    title=settings.APP_NAME,
    description="每日自动抓取 AI、OPC、国际经济、YouTube、X、TikTok 重点资讯，生成深度调查报道与普通话高保真语音播报",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载音频存储目录（流式播放）与静态目录
app.mount("/audio", StaticFiles(directory=str(STORAGE_DIR)), name="audio")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "NewsCast API running. Static frontend not found."}

@app.get("/manifest.json")
async def serve_manifest():
    manifest_file = STATIC_DIR / "manifest.json"
    if manifest_file.exists():
        return FileResponse(manifest_file, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest not found")

@app.get("/sw.js")
async def serve_sw():
    sw_file = STATIC_DIR / "sw.js"
    if sw_file.exists():
        return FileResponse(sw_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="service worker not found")

@app.get("/api/reports/latest")
async def get_latest_report(session: AsyncSession = Depends(get_db_session)):
    stmt = select(DailyReport).order_by(desc(DailyReport.date_str)).limit(1)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        return JSONResponse(status_code=202, content={
            "status": "generating" if is_generating else "empty",
            "message": "今日简报正在生成中，请稍候约 10-20 秒刷新..."
        })
    return report.to_dict()

@app.get("/api/reports")
async def list_reports(limit: int = 15, session: AsyncSession = Depends(get_db_session)):
    stmt = select(DailyReport).order_by(desc(DailyReport.date_str)).limit(limit)
    result = await session.execute(stmt)
    reports = result.scalars().all()
    return [r.to_dict() for r in reports]

@app.get("/api/reports/{date_or_id}")
async def get_report(date_or_id: str, session: AsyncSession = Depends(get_db_session)):
    if date_or_id.isdigit():
        stmt = select(DailyReport).where(DailyReport.id == int(date_or_id))
    else:
        stmt = select(DailyReport).where(DailyReport.date_str == date_or_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.to_dict()

@app.post("/api/reports/trigger")
async def trigger_generate(background_tasks: BackgroundTasks):
    global is_generating
    if is_generating:
        return {"status": "in_progress", "message": "已有生成任务正在运行中，无需重复触发"}
    
    background_tasks.add_task(run_daily_pipeline, force=True)
    return {"status": "started", "message": "已在后台启动抓取、分析与语音生成流水线，预计耗时 10-15 秒"}

@app.get("/api/status")
async def get_system_status():
    return {
        "status": "running",
        "is_generating": is_generating,
        "scheduler_schedule": f"每天 {settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d} (Asia/Shanghai)",
        "tts_voice": settings.TTS_VOICE,
        "storage_dir": str(STORAGE_DIR)
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
