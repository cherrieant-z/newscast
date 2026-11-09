import os
import re
import asyncio
from pathlib import Path
from typing import Tuple
import edge_tts
from app.config import settings, STORAGE_DIR

def _make_en_pattern(word: str) -> str:
    # 采用前后零宽断言，确保即使紧贴中文字符（如 全球AI、10月PMI为）也能精准匹配
    escaped = re.escape(word)
    return rf'(?i)(?<![a-zA-Z]){escaped}(?![a-zA-Z])'

# 英文缩写与特定概念中英对照转换词典（注意分寸：只转换念字母别扭的缩写与宏观概念，知名工具与模型名称如 Claude、OpenAI、Dify、Shopify 完整保留原汁原味）
ENGLISH_TO_CHINESE_MAP = [
    # 完整通用概念
    ('One Person Company', '一人公司'),
    ('Quote of the Day', '今日金句'),
    ('Computer Use', '计算机控制操作'),
    ('Open Source', '开源技术'),
    ('AI Agent', '人工智能智能体'),
    ('AI Agents', '人工智能智能体'),

    # 宏观经济与金融商业缩写（听众听英文缩写费解，转换为规范中文）
    ('PMI', '采购经理指数'),
    ('GDP', '国内生产总值'),
    ('CPI', '居民消费价格指数'),
    ('PPI', '工业生产者出厂价格指数'),
    ('IPO', '首次公开募股'),
    ('CEO', '首席执行官'),
    ('CTO', '首席技术官'),
    ('CFO', '首席财务官'),
    ('COO', '首席运营官'),
    ('FED', '美联储'),
    ('Fed', '美联储'),
    ('SEC', '美国证券交易委员会'),
    ('OPEC', '石油输出国组织'),
    ('WTO', '世界贸易组织'),
    ('WHO', '世界卫生组织'),
    ('IMF', '国际货币基金组织'),
    ('NATO', '北约'),
    ('EVs', '电动汽车'),
    ('EV', '电动汽车'),
    ('ARR', '年度经常性收入'),
    ('MRR', '月度经常性收入'),
    ('GMV', '成交总额'),
    ('ROI', '投资回报率'),
    ('DAU', '日活跃用户数'),
    ('MAU', '月活跃用户数'),

    # 常见行业通用缩写（避免朗读逐字母拼读产生违和感）
    ('AI', '人工智能'),
    ('AGI', '通用人工智能'),
    ('Agent', '智能体'),
    ('Agents', '智能体'),
    ('SOP', '标准实操流程'),
    ('APIs', '应用程序接口'),
    ('API', '接口'),
    ('SaaS', '软件服务'),
    ('PaaS', '平台服务'),
    ('IaaS', '基础设施服务'),
    ('OPC', '一人公司'),
    ('LLMs', '大语言模型'),
    ('LLM', '大语言模型'),
    ('Prompt', '提示词'),
    ('Prompts', '提示词'),
    ('Tokens', '字符单元'),
    ('Token', '字符单元'),
    ('Apps', '客户端应用'),
    ('App', '客户端'),
    ('APP', '客户端'),
    ('GPUs', '图形算力芯片'),
    ('GPU', '图形算力芯片'),
    ('CPUs', '中央处理器'),
    ('CPU', '中央处理器'),
    ('PC', '电脑'),
    ('OS', '操作系统'),
    ('UI', '用户界面'),
    ('UX', '交互体验'),
    ('WiFi', '无线网络'),
    ('Wi-Fi', '无线网络'),
    ('5G', '五代移动通信'),
    ('4G', '四代移动通信'),
    ('B2B', '企业端业务'),
    ('B2C', '消费者业务'),
    ('A股', '国内A股'),
    ('B站', '哔哩哔哩'),
]

COMPILED_PATTERNS = [(re.compile(_make_en_pattern(word)), repl) for word, repl in ENGLISH_TO_CHINESE_MAP]


class TTSFailure(RuntimeError):
    """音频没能生成出可用产物。调用方必须把它当失败，不能当成功。"""

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
        # 单次合成上限。6 分钟稿子正常 15~40 秒能出，给到 240 秒已经很宽松；
        # 超过这个时间基本就是连接半开，继续等没有意义。
        self.synth_timeout = 240.0

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

        # 先渲染到临时文件，验收通过了才替换正式文件。
        # 这样「重跑时 TTS 恰好挂了」不会把早上已经能听的那一版覆盖成静音——
        # 旧文件原地不动，进程以失败退出，人还能再点一次重跑。
        tmp_path = dest_path.with_suffix(".part.mp3")

        errors = []
        for voice in (self.default_voice, self.backup_voice):
            for attempt in (1, 2):
                try:
                    print(f"[TTS] 音色 [{voice}] 第 {attempt} 次渲染...")
                    await self._run_edge_tts(cleaned_text, str(tmp_path), voice)
                except Exception as e:
                    errors.append(f"{voice}#{attempt} 渲染异常: {type(e).__name__}: {e}")
                    continue

                ok, reason = self._verify_audio(str(tmp_path), cleaned_text)
                if ok:
                    os.replace(tmp_path, dest_path)
                    voice_used = voice
                    print(f"[TTS] 渲染完成并通过验收（音色 {voice}）")
                    break
                errors.append(f"{voice}#{attempt} 产物不合格: {reason}")
                print(f"[TTS] 产物不合格，重试：{reason}")
            else:
                continue
            break
        else:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            detail = "；".join(errors[-3:]) or "未知原因"
            raise TTSFailure(f"两个音色共 {len(errors)} 次尝试均未产出可用音频：{detail}")

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
        # edge-tts 已知的故障模式是 WebSocket 半开：连上了、不返回、也不断开。
        # 不设超时，整个 job 会一直挂到 Actions 的 6 小时上限，
        # 期间还占着 concurrency 锁，把后面两趟兜底一起拖死。
        await asyncio.wait_for(communicate.save(output_path), timeout=self.synth_timeout)

    def _verify_audio(self, path: str, text: str) -> Tuple[bool, str]:
        """
        产物验收。这是全流程唯一能区分「合成成功」和「合成出一坨垃圾」的地方。

        Edge-TTS 是 48kbps（约 6000 字节/秒），中文播报约 3.7 字/秒，
        所以字节数大致可以拿字数反推。低于预期一半就是截断，
        几万字节以内基本可以断定是静音占位或空壳。
        """
        p = Path(path)
        if not p.exists():
            return False, "临时文件不存在"
        size = p.stat().st_size
        if size < 8000:
            return False, f"只有 {size} 字节，是空壳"
        chars = len(re.sub(r"\s+", "", text)) or 1
        expected = chars / 3.7 * 6000
        if size < expected * 0.5:
            return False, f"{size} 字节，仅为预期 {int(expected)} 的 {size / expected:.0%}，像是念到一半断了"
        return True, ""

    def _optimize_text_for_podcast(self, text: str) -> str:
        """
        为播客式朗读优化文本：
        1. 移除 Markdown 杂音标记（星号、方括号、井号、反引号等）与 URL
        2. 将别扭的缩写与宏观概念（如 PMI、AI、SOP、API 等）转换为地道中文，知名工具模型名称（如 Claude, Shopify, Dify 等）自然保留
        3. 优化断句标点，让长句自然分段，产生如主播呼吸般的生活感停顿
        """
        t = text
        # 1. 移除 Markdown 格式字符与链接
        t = self._strip_urls(t)
        t = re.sub(r'&nbsp;?', ' ', t)
        t = re.sub(r'[*#_`~>\[\]\(\)]', '', t)
        
        # 2. 预处理常见含数字与英文字符的表达
        t = re.sub(r'(?i)7\s*[x*×]\s*24\s*小时?', '全天候24小时', t)
        
        # 3. 批量缩写与概念精准转换（知名品牌与工具如 Claude, OpenAI, Dify, Shopify 适度保留原汁原味）
        for pattern, repl in COMPILED_PATTERNS:
            t = pattern.sub(repl, t)

        # 4. 将冒号转换为停顿逗号，优化自然分句停顿
        t = t.replace("：", "，").replace(":", "，").replace(";", "；")
        
        # 5. 规整多余空白与换行
        lines = [line.strip() for line in t.split("\n") if line.strip()]
        cleaned = "\n\n".join(lines)
        return cleaned

    def _strip_urls(self, text: str) -> str:
        """
        处理链接。以前是一刀切成空字符串，于是「地址在：https://xxx 目前支持三端同步」
        念出来就断在「地址在，」——半句话悬在那儿，听的人会以为音频坏了。

        现在按句处理：先摘掉「地址在/链接是 + URL」这种残段，剩下的 URL 念作「官网」，
        去掉链接后整句不足 10 个字就直接丢弃（那种句子本来也只是在报网址）。
        """
        out = []
        for sent in re.split(r'(?<=[。！？!?\n])', text):
            if "http://" not in sent and "https://" not in sent:
                out.append(sent)
                continue
            s = re.sub(r'(地址|链接|网址|入口|报名)(在|是)?[：:，,]?\s*https?://\S+', '', sent)
            s = re.sub(r'https?://\S+', '官网', s)
            s = re.sub(r'[，,、]?\s*官网\s*[，,、]?', '官网', s)
            # 「最近把 Ginkgo 发出来了：官网。」这种，链接就是句尾，念「官网」没意义，收成句号
            s = re.sub(r'[：:]\s*官网[。]?$', '。', s)
            s = re.sub(r'[ \t]{2,}', ' ', s).strip()
            if len(re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9]', '', s)) < 6:
                continue
            out.append(s)
        return "".join(out)

    def _calc_audio_duration(self, text: str, file_path: str) -> int:
        """
        计算实际播报时长：
        播客主播正常中速语速约为 230 ~ 245 字/分钟（约 3.8 ~ 4.0 字/秒）。
        同时结合生成 MP3 文件大小校验。
        """
        char_count = len(re.sub(r'\s+', '', text))
        # 中文播客语速加标点停顿约每秒 3.7 字
        estimated_sec = int(char_count / 3.7)
        
        # 优先从真实生成的 MP3 文件大小与码率计算真实精准时长（Edge-TTS 为 24kHz 48kbps，即 6000 字节/秒）
        if os.path.exists(file_path):
            file_size_bytes = os.path.getsize(file_path)
            if file_size_bytes > 50000:
                return int(file_size_bytes / 6000)

        return max(estimated_sec, 60)

tts_engine = TTSEngine()
