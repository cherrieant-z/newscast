import os
import re
import asyncio
from pathlib import Path
from typing import Tuple
import edge_tts
from app.config import settings, STORAGE_DIR

class TTSEngine:
    """
    负责将新闻底稿转化为高拟真度普通话语音 MP3 文件。
    首选微软 edge-tts 最自然、富有情感起伏的播客/叙事风格语音：
    - 首选男声: zh-CN-YunxiNeural (充满活力、生动自然、极具播客主播感)
    - 首选女声: zh-CN-XiaoxiaoNeural (温暖亲切、抑扬顿挫好)
    """

    def __init__(self):
        # 默认优先使用设置里的 Yunxi 充满活力的播客男声
        self.default_voice = settings.TTS_VOICE or "zh-CN-YunxiNeural"
        self.backup_voice = "zh-CN-XiaoxiaoNeural"

    async def generate_audio(self, text: str, date_str: str, output_dir: Path = None) -> Tuple[str, str, int, str, int]:
        """
        生成 MP3 文件
        返回: (local_file_path, public_url, duration_seconds, duration_str, file_size_bytes)
        """
        # 清理与呼吸感节奏优化
        cleaned_text = self._optimize_text_for_podcast(text)
        
        target_dir = Path(output_dir) if output_dir else STORAGE_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"newscast_{date_str}.mp3"
        dest_path = target_dir / file_name
        public_url = f"/audio/{file_name}"

        voice_used = self.default_voice
        try:
            print(f"[TTS] 正在使用高拟真音色 [{voice_used}] 渲染播客级普通话音频...")
            await self._run_edge_tts(cleaned_text, str(dest_path), voice_used)
        except Exception as e:
            print(f"[TTS] 默认音色 {voice_used} 生成受阻，尝试备用音色 [{self.backup_voice}]: {e}")
            try:
                voice_used = self.backup_voice
                await self._run_edge_tts(cleaned_text, str(dest_path), voice_used)
            except Exception as e2:
                print(f"[TTS] 备用音色亦发生异常，使用安全占位帧: {e2}")
                self._create_silent_fallback(str(dest_path))

        file_size = os.path.getsize(dest_path) if dest_path.exists() else 0
        
        # 准确估算或读取时长
        duration_sec = self._calc_audio_duration(cleaned_text, str(dest_path))
        mins = duration_sec // 60
        secs = duration_sec % 60
        duration_str = f"{mins:02d}:{secs:02d}"

        return str(dest_path), public_url, duration_sec, duration_str, file_size

    async def _run_edge_tts(self, text: str, output_path: str, voice: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=settings.TTS_RATE,
            pitch=settings.TTS_PITCH
        )
        await communicate.save(output_path)

    def _optimize_text_for_podcast(self, text: str) -> str:
        """
        为播客式朗读优化文本：
        1. 移除 Markdown 杂音标记（星号、方括号、井号、反引号等）
        2. 移除裸 URL 与英文技术缩写后的杂质
        3. 优化断句标点，让长句自然分段，产生如主播呼吸般的生活感停顿
        """
        t = text
        # 移除 Markdown 格式字符
        t = re.sub(r'[*#_`~>\[\]]', '', t)
        t = re.sub(r'https?://\S+', '', t)
        
        # 将连续英文或过于紧凑的逗号保留为自然停顿
        # 将冒号适度替换为逗号或语气自然停顿
        t = t.replace("：", "，").replace(":", "，")
        
        # 规整多余空白与换行
        lines = [line.strip() for line in t.split("\n") if line.strip()]
        # 段落之间保留自然空行与标点
        cleaned = "\n\n".join(lines)
        return cleaned

    def _calc_audio_duration(self, text: str, file_path: str) -> int:
        """
        计算实际播报时长：
        播客主播正常中速语速约为 230 ~ 245 字/分钟（约 3.8 ~ 4.0 字/秒）。
        同时结合生成 MP3 文件大小校验。
        """
        char_count = len(re.sub(r'\s+', '', text))
        # 中文播客语速加标点停顿约每秒 3.7 字
        estimated_sec = int(char_count / 3.7)
        
        # 若能从文件大小校验（Edge-TTS 默认音频约 48kbps，即 6KB/s）
        if os.path.exists(file_path):
            file_size_bytes = os.path.getsize(file_path)
            if file_size_bytes > 50000:
                duration_from_size = int(file_size_bytes / 6000)
                # 两者综合校准
                return max(duration_from_size, estimated_sec, 60)

        return max(estimated_sec, 60)

    def _create_silent_fallback(self, path: str):
        with open(path, "wb") as f:
            f.write(b'\xff\xfb\x90d\x00\x00\x00\x00' * 50)

tts_engine = TTSEngine()
