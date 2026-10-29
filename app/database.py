from datetime import datetime
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, select, desc
from app.config import settings

Base = declarative_base()

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_str: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    lead_title: Mapped[str] = mapped_column(String(255), default="")
    summary_text: Mapped[str] = mapped_column(Text, default="")
    markdown_content: Mapped[str] = mapped_column(Text)
    audio_path: Mapped[str] = mapped_column(String(512), default="")
    audio_url: Mapped[str] = mapped_column(String(512), default="")
    audio_duration: Mapped[int] = mapped_column(Integer, default=0) # 时长(秒)
    audio_duration_str: Mapped[str] = mapped_column(String(32), default="00:00")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    category_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        try:
            cat_summary = json.loads(self.category_summary_json)
        except Exception:
            cat_summary = {}
        try:
            sources = json.loads(self.sources_json)
        except Exception:
            sources = []

        return {
            "id": self.id,
            "date_str": self.date_str,
            "title": self.title,
            "lead_title": self.lead_title,
            "summary_text": self.summary_text,
            "markdown_content": self.markdown_content,
            "audio_url": self.audio_url,
            "audio_duration": self.audio_duration,
            "audio_duration_str": self.audio_duration_str,
            "file_size_bytes": self.file_size_bytes,
            "category_summary": cat_summary,
            "sources": sources,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
