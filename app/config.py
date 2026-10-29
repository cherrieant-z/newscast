import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "audio_storage"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = BASE_DIR / "newscast.db"

# 确保必要目录存在
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "每日调查新闻与语音播报"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DB_PATH}"
    
    # 调度器触发时间：每天早上 06:00
    SCHEDULE_HOUR: int = 6
    SCHEDULE_MINUTE: int = 0
    
    # TTS 语音配置 (默认选用微软高品质新闻解说男声 云希 或 甜美播报女声 晓晓)
    # 可选: "zh-CN-YunxiNeural" (质感/沉稳调查播音), "zh-CN-XiaoxiaoNeural" (自然/亲切), "zh-CN-YunjianNeural" (新闻联播风)
    TTS_VOICE: str = "zh-CN-YunxiNeural"
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"
    
    # 外部 LLM / 模拟调查分析（若配置了 OpenAI/Gemini Key 则调用高级智能体，否则使用智能调查合成引擎）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
