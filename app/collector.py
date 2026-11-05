# -*- coding: utf-8 -*-
import asyncio
import datetime
import hashlib
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

CATEGORIES = [
    "AI Agent",
    "一人公司",
    "新浪财经",
    "参考消息",
    "学习强国",
    "喜马拉雅新闻早餐"
]

# ============================================================
# 真实中文资讯源（国内直连、无需代理、无需翻译）
# 实测可用：36氪 / 极客公园 / 爱范儿 / InfoQ / 少数派 / 构建我的被动收入 等
# 注意：36氪必须带 www；机器之心 RSS 格式损坏已剔除；量子位在部分网络走代理会失败（自动降级）
# ============================================================
AI_RSS_SOURCES = [
    {"name": "36氪",     "url": "https://www.36kr.com/feed"},
    {"name": "极客公园", "url": "https://www.geekpark.net/rss"},
    {"name": "爱范儿",   "url": "https://www.ifanr.com/feed"},
    {"name": "InfoQ中文", "url": "https://www.infoq.cn/feed"},
    {"name": "量子位",   "url": "https://www.qbitai.com/feed"},
]

# 一人公司 / 独立开发者 / 搞钱方向（中文）
OPC_RSS_SOURCES = [
    {"name": "少数派",             "url": "https://sspai.com/feed"},
    {"name": "构建我的被动收入",   "url": "https://www.bmpi.dev/index.xml"},
    {"name": "透明创业实验",       "url": "https://blog.t9t.io/atom.xml"},
    {"name": "小众软件",           "url": "https://www.appinn.com/feed/"},
]


def is_mostly_english(text: str) -> bool:
    """过滤长句全英文内容，确保主站与播报不出现未经翻译的大段英文"""
    if not text:
        return False
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
    # 如果文本较长且中文字符极其稀少（低于 5 个汉字），判定为未翻译的纯英文长句
    return len(text) > 20 and len(chinese_chars) < 5


def is_similar_title(t1: str, t2: str) -> bool:
    """去重判断：去除标点符号后比对子串重合与字符 Jaccard 相似度"""
    c1 = re.sub(r'[^\w\u4e00-\u9fa5]', '', t1)
    c2 = re.sub(r'[^\w\u4e00-\u9fa5]', '', t2)
    if not c1 or not c2:
        return False
    if c1 == c2 or c1 in c2 or c2 in c1:
        return True
    s1, s2 = set(c1), set(c2)
    jaccard = len(s1 & s2) / len(s1 | s2)
    return jaccard > 0.72


# ============================================================
# 通用 RSS / Atom 解析（用标准库，不引入额外依赖）
# ============================================================
def _local(tag: str) -> str:
    """去掉命名空间前缀，如 {http://www.w3.org/2005/Atom}title -> title"""
    return tag.split('}')[-1]


def _text_of(entry, name: str) -> str:
    for child in entry.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def _link_of(entry) -> str:
    for child in entry.iter():
        if _local(child.tag) == 'link':
            href = child.get('href', '')
            if href:
                return href.strip()
            if child.text:
                return child.text.strip()
    return ""


def _strip_html(text: str) -> str:
    """清理 HTML 标签与实体，得到纯文本摘要"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;?', ' ', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&ldquo;', '"').replace('&rdquo;', '"')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_feed_items(xml_text: str) -> List[Dict[str, str]]:
    """解析 RSS 2.0 / Atom 两种格式，返回 [{title, link, summary, published}]"""
    items = []
    if not xml_text:
        return items
    # 清理非法 XML 控制字符，避免个别源解析失败
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', xml_text)
    try:
        root = ET.fromstring(cleaned)
    except Exception:
        return items

    entries = []
    for el in root.iter():
        if _local(el.tag) in ('item', 'entry'):
            entries.append(el)

    for e in entries[:30]:
        title = _strip_html(_text_of(e, 'title'))
        if not title:
            continue
        link = _link_of(e)
        summary = _strip_html(_text_of(e, 'description') or _text_of(e, 'summary') or _text_of(e, 'content'))
        published = _text_of(e, 'pubDate') or _text_of(e, 'published') or _text_of(e, 'updated')
        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "published": published
        })
    return items


class NewsCollector:
    """
    负责采集当天重点资讯：
    1. 全球 AI 动态（机器之心 / 量子位 / 36氪 / 爱范儿等中文源，真实抓取）
    2. 一人公司 / 独立开发者搞钱（少数派 / 构建我的被动收入等，真实抓取）
    3. 新浪财经 APP：首页红框【要闻】核心专区
    4. 参考消息 APP：官方要闻 JSON 通道
    5. 学习强国：权威国内要闻（抓取失败则自动跳过，绝不播过时内容）
    6. 喜马拉雅：10分钟新闻早餐（当天有则播，无则跳过）
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }

    async def fetch_sina_finance_yaowen(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """专向抓取：新浪财经 APP 首页【要闻】红框核心专区"""
        items = []
        try:
            url = "https://finance.sina.com.cn/"
            resp = await client.get(url, timeout=8.0)
            if resp.status_code == 200:
                html = resp.content.decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")
                yw_blocks = soup.find_all(attrs={"data-sudaclick": lambda x: x and "blk_yw" in x})

                for blk in yw_blocks:
                    for a in blk.find_all("a"):
                        t = a.get_text(strip=True)
                        href = a.get("href", "")
                        # 过滤无效纯标点或通用导航词汇
                        if not t or len(t) < 6 or "新浪财经" in t or "芝麻AI" in t or "快讯汇总" in t or "早报" in t:
                            continue

                        # 检查去重
                        if not any(is_similar_title(t, existing["title"]) for existing in items):
                            items.append({
                                "title": t,
                                "category": "新浪财经",
                                "summary": t,
                                "source_name": "新浪财经·要闻",
                                "url": href if href.startswith("http") else f"https:{href}" if href.startswith("//") else "https://finance.sina.com.cn",
                                "published_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
        except Exception as e:
            print(f"[Collector] 新浪财经抓取异常: {e}")

        return items[:15]

    async def fetch_cankao_xiaoxi_yaowen(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """专向抓取：参考消息 APP【今日要闻】频道"""
        items = []
        try:
            url = "https://www.cankaoxiaoxi.com/json/channel/yaowen/list.json"
            resp = await client.get(url, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                raw_list = data.get("list", [])
                for it in raw_list:
                    d = it.get("data", {})
                    title = d.get("title", "").strip()
                    url_link = d.get("url", "https://www.cankaoxiaoxi.com")
                    pub = d.get("publishTime", "")

                    if not title or len(title) < 5:
                        continue

                    if not any(is_similar_title(title, existing["title"]) for existing in items):
                        items.append({
                            "title": title,
                            "category": "参考消息",
                            "summary": f"{title}（参考消息发布于 {pub}）" if pub else title,
                            "source_name": "参考消息·要闻",
                            "url": url_link,
                            "published_at": pub or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
        except Exception as e:
            print(f"[Collector] 参考消息抓取异常: {e}")

        return items[:15]

    async def fetch_xuexi_qiangguo_yaowen(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """
        抓取权威国内要闻（学习强国聚合源）。
        原则：抓不到就返回空列表（播报时明说“今日暂无”），绝不硬编码过时时政。
        """
        items = []
        sources = [
            ("学习强国·头条要闻", "http://www.people.com.cn/rss/politics.xml"),
        ]
        for name, url in sources:
            try:
                resp = await client.get(url, timeout=8.0)
                if resp.status_code != 200:
                    continue
                feed_items = _parse_feed_items(resp.text)
                for fi in feed_items:
                    title = fi.get("title", "").strip()
                    if not title or len(title) < 6:
                        continue
                    summary = fi.get("summary", "")[:120]
                    if not any(is_similar_title(title, e["title"]) for e in items):
                        items.append({
                            "title": title,
                            "category": "学习强国",
                            "summary": summary or title,
                            "source_name": name,
                            "url": fi.get("link", ""),
                            "published_at": (fi.get("published", "")[:19]) or datetime.datetime.now().strftime("%Y-%m-%d"),
                        })
                if items:
                    break
            except Exception as e:
                print(f"[Collector] 学习强国/权威要闻抓取异常: {e}")

        return items[:10]

    async def fetch_ximalaya_breakfast(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """抓取：喜马拉雅 10分钟新闻早餐（当天有则完整播报，无则跳过）"""
        items = []
        try:
            url = "https://mobile.ximalaya.com/mobile/v1/album/track?albumId=68589357&pageSize=5&pageId=1"
            resp = await client.get(url, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                tracks = data.get("data", {}).get("list", [])
                today_str = datetime.datetime.now().strftime("%m月%d日")
                for tr in tracks:
                    title = tr.get("title", "").strip()
                    # 严格按用户指令：只有包含“当天日期”的新闻早餐才汇报，如果当天无内容就不用报
                    if today_str in title:
                        items.append({
                            "title": title,
                            "category": "喜马拉雅新闻早餐",
                            "summary": f"喜马拉雅10分钟新闻早餐今日节目：{title}",
                            "source_name": "喜马拉雅·10分钟新闻早餐",
                            "url": f"https://www.ximalaya.com/sound/{tr.get('trackId')}",
                            "published_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
        except Exception as e:
            print(f"[Collector] 喜马拉雅抓取异常: {e}")
        return items

    async def _fetch_from_sources(self, client: httpx.AsyncClient, sources: List[Dict], category: str, max_items: int = 3) -> List[Dict[str, Any]]:
        """从一组 RSS/Atom 源抓取真实新闻，逐源降级，够数即止"""
        items = []
        for src in sources:
            try:
                resp = await client.get(src["url"], timeout=10.0)
                if resp.status_code != 200:
                    continue
                feed_items = _parse_feed_items(resp.text)
                for fi in feed_items:
                    title = fi.get("title", "").strip()
                    if not title or len(title) < 4:
                        continue
                    summary = fi.get("summary", "")[:220]
                    if len(summary) < 8:
                        summary = title
                    # 过滤纯英文长句，保证中文环境纯正
                    if is_mostly_english(title) or is_mostly_english(summary):
                        continue
                    if not any(is_similar_title(title, e["title"]) for e in items):
                        items.append({
                            "title": title,
                            "category": category,
                            "summary": summary,
                            "why_matter": "",
                            "source_name": src["name"],
                            "url": fi.get("link", ""),
                            "published_at": (fi.get("published", "")[:19]) or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "is_fallback": False,
                        })
                    if len(items) >= max_items:
                        break
            except Exception as e:
                print(f"[Collector] {src['name']} 抓取异常: {e}")
                continue
            if len(items) >= max_items:
                break
        return items[:max_items]

    def _fallback_pool(self, date_str: str, category: str) -> List[Dict[str, Any]]:
        """
        极端兜底：所有真实源都抓不到时，用精选观点库顶上。
        关键：这些明确标注为“精选观点”，绝不冒充“当天新闻”。
        """
        pools = {
            "AI Agent": [
                ("智能体正在从“会聊天”变成“会干活”", "越来越多 AI 产品开始接管真实的电脑操作、写代码、跑流程，一个人就能指挥一支虚拟团队完成过去需要多人协作的任务。"),
                ("小模型也能干大事", "开源社区把几十亿参数的模型优化得越来越能打，个人创业者不用昂贵算力也能搭起专业级业务流水线。"),
                ("多模态模型让 AI 看懂屏幕", "新一代视觉模型能像人一样看懂网页和旧软件界面，跨系统自动录入、上架、对账这类重复劳动正在被大幅压缩。"),
            ],
            "一人公司": [
                ("一个人也能跑通一门生意", "越来越多独立开发者用低代码和 AI 工作流，把获客、客服、收款串成一条自动化流水线。"),
                ("微型 SaaS 项目迎来好行情", "单人开发、AI 托管的微型软件项目越来越受买家青睐，深耕极小垂直痛点也能做出稳定现金流。"),
                ("信息差与语言差里藏着机会", "用工具抹平地域和语言鸿沟的地方，往往涌动着普通人能抓住的商业机会。"),
            ],
        }
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        return [
            {
                "title": title,
                "category": category,
                "summary": summary,
                "why_matter": "把它当成一个值得你留意的方向信号，而不是一条新鲜出炉的新闻。",
                "source_name": "精选观点库",
                "url": "",
                "published_at": now,
                "is_fallback": True,
            }
            for title, summary in pools.get(category, [])
        ]

    async def fetch_ai_agent_and_opc(self, client: httpx.AsyncClient, date_str: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """真实抓取全球 AI 与一人公司中文资讯，抓取失败才降级到精选观点库"""
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        ai_items = await self._fetch_from_sources(client, AI_RSS_SOURCES, "AI Agent", max_items=3)
        opc_items = await self._fetch_from_sources(client, OPC_RSS_SOURCES, "一人公司", max_items=3)

        if not ai_items:
            ai_items = self._fallback_pool(date_str, "AI Agent")
        if not opc_items:
            opc_items = self._fallback_pool(date_str, "一人公司")

        return {"AI Agent": ai_items, "一人公司": opc_items}

    async def collect_all(self, date_str: str = None) -> Dict[str, List[Dict[str, Any]]]:
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")

        results: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in CATEGORIES}

        async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=15.0) as client:
            tasks = [
                self.fetch_sina_finance_yaowen(client),
                self.fetch_cankao_xiaoxi_yaowen(client),
                self.fetch_xuexi_qiangguo_yaowen(client),
                self.fetch_ximalaya_breakfast(client),
                self.fetch_ai_agent_and_opc(client, date_str),
            ]
            sina_res, cankao_res, xuexi_res, xm_res, ai_res = await asyncio.gather(*tasks, return_exceptions=True)

            if isinstance(sina_res, list):
                results["新浪财经"] = sina_res
            if isinstance(cankao_res, list):
                results["参考消息"] = cankao_res
            if isinstance(xuexi_res, list):
                results["学习强国"] = xuexi_res
            if isinstance(xm_res, list):
                results["喜马拉雅新闻早餐"] = xm_res
            if isinstance(ai_res, dict):
                results["AI Agent"] = ai_res.get("AI Agent", [])
                results["一人公司"] = ai_res.get("一人公司", [])

        # 全局跨平台去重与纯英文长句过滤校验
        seen_titles = []
        for cat in CATEGORIES:
            deduped = []
            for item in results[cat]:
                title = item["title"]
                summary = item.get("summary", "")

                # 严格过滤纯英文长句，保证中文环境纯正、无未经翻译的生硬长句
                if is_mostly_english(title) or is_mostly_english(summary):
                    continue

                is_dup = False
                for existing in seen_titles:
                    if is_similar_title(title, existing):
                        is_dup = True
                        break
                if not is_dup:
                    seen_titles.append(title)
                    deduped.append(item)
            results[cat] = deduped

        return results


collector = NewsCollector()
