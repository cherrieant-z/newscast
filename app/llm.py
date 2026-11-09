"""
DeepSeek 客户端（OpenAI 兼容协议）。

设计原则只有一条：**模型是加法，不是依赖。**

早报必须在早上六点准时出现，不能因为模型超时、限流、余额不足、或者接口
改了个字段就整期消失。所以这里的每个函数都遵守同一套约定：

- 没配 key → 直接返回 None，调用方走原来的规则逻辑
- 网络/接口出任何问题 → 打一行日志，返回 None，绝不抛异常
- 模型返回的 JSON 不合法 → 尽力修复（去掉 ``` 包裹、截取第一个 {...}），
  再不行就返回 None

调用方一律写成 «能用模型就用，用不了照常跑»，不做 try/except 嵌套。
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


class LLMClient:
    def __init__(self) -> None:
        self.last_error = ""
        # 本地调试时本机代理端口会变，允许用环境变量显式指定，
        # 生产（GitHub 机房）不设这个变量，走直连。
        self.proxy = os.environ.get("NEWSCAST_PROXY") or None

    # ---------------------------------------------------------------- 基础

    @property
    def enabled(self) -> bool:
        return bool((settings.DEEPSEEK_API_KEY or "").strip())

    @property
    def model(self) -> str:
        return settings.DEEPSEEK_MODEL or "deepseek-chat"

    def _url(self) -> str:
        base = (settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com/v1").rstrip("/")
        return f"{base}/chat/completions"

    async def chat(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 90.0,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            # DeepSeek 的 JSON 模式要求提示词里出现 "json" 字样，提示词里都写了。
            payload["response_format"] = {"type": "json_object"}

        last = ""
        for attempt in range(2):
            try:
                kwargs: Dict[str, Any] = {"timeout": timeout}
                if self.proxy:
                    kwargs["proxy"] = self.proxy
                async with httpx.AsyncClient(**kwargs) as client:
                    resp = await client.post(
                        self._url(),
                        headers={
                            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.strip()}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                last = f"HTTP {resp.status_code}: {resp.text[:160]}"
            except Exception as e:  # 网络、超时、解析，全部吞掉
                last = f"{type(e).__name__}: {str(e)[:160]}"
            if attempt == 0:
                await asyncio.sleep(1.5)

        self.last_error = last
        print(f"[LLM] 调用失败，本期改用规则引擎：{last}")
        return None

    async def json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        timeout: float = 90.0,
    ) -> Optional[Dict[str, Any]]:
        raw = await self.chat(
            system, user, json_mode=True,
            temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        )
        if not raw:
            return None
        return _loads_loose(raw)


def _loads_loose(raw: str) -> Optional[Dict[str, Any]]:
    """模型偶尔会把 JSON 包在 ```json 里，或者在前后加一句解释，这里尽力捞回来。"""
    text = (raw or "").strip()
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"items": obj}
    except Exception:
        pass
    # 截取最外层的一对花括号
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def clean(value: Any, limit: int = 200) -> str:
    """把模型给的字段整理成能直接念的一句话：去掉换行、引号、Markdown 和多余空白"""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[*#`>_]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("「」\"'“”‘’ ")
    if len(text) > limit:
        cut = max(text.rfind("。", 0, limit), text.rfind("，", 0, limit))
        text = text[:cut + 1] if cut > limit * 0.6 else text[:limit]
    return text.strip()


def has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fa5]", text or ""))


llm = LLMClient()
