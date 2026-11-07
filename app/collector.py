# -*- coding: utf-8 -*-
import asyncio
import datetime
import email.utils
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
    "宏观大势",
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


def _kw_hit(text: str, kw: str) -> bool:
    """关键词命中判断：纯字母词走词边界，避免 detail 被判定为命中 ai"""
    if not text or not kw:
        return False
    if kw.isascii() and kw.isalpha():
        return re.search(rf'(?<![a-z]){re.escape(kw)}(?![a-z])', text) is not None
    return kw in text


def _hits_any(text: str, keywords) -> bool:
    return any(_kw_hit(text, kw) for kw in keywords)


# ============================================================
# 相关性闸门（P0-1）：只让「真的跟 AI / 一人公司有关」的内容进来
# 起因：36氪、少数派都是全站 RSS，里面混着游戏、菜谱、设计、奶茶加盟，
#      不过闸就会把这些当新闻念给听众。
# 原则：标题或摘要命中任一关键词才放行。宁可少，不要凑。
# ============================================================
AI_GATE_KEYWORDS = [
    "人工智能", "大模型", "智能体", "生成式", "多模态", "算力", "芯片", "半导体",
    "算法", "机器学习", "深度学习", "推理", "智能驾驶", "具身", "机器人", "自动化",
    "编程助手", "代码生成", "开源模型", "训练", "微调", "推理成本",
    "ai", "gpt", "claude", "llm", "agent", "aigc", "openai", "deepseek", "qwen",
    "gemini", "copilot", "midjourney", "sora", "nvidia", "anthropic", "llama",
    "英伟达", "豆包", "通义", "文心", "kimi", "智谱", "月之暗面", "minimax",
]

OPC_GATE_KEYWORDS = [
    "独立开发", "一人公司", "超级个体", "副业", "变现", "营收", "月入", "年入",
    "赚钱", "被动收入", "付费", "定价", "客单价", "获客", "流量",
    "转化率", "复购", "留存", "毛利", "利润", "现金流", "创业", "接单",
    "自由职业", "出海", "跨境", "电商", "选品", "小众", "垂类", "效率工具",
    "工作流", "自动化", "sop", "saas", "indie", "solo", "remote", "freelance",
    "stripe", "shopify",
]

# 少数派等生活类源里跟「搞钱」无关的题材，命中即丢弃
OPC_BLOCK_KEYWORDS = [
    "菜谱", "蒸菜", "食谱", "美食", "家常", "烘焙", "探店", "好饭", "厨房",
    "游记", "出行装备", "壁纸", "表情包", "字体", "输入法", "键盘", "耳机",
    "显示器", "相机", "摄影", "影音", "观影", "书单", "日历", "桌面美化",
]


# ============================================================
# 宏观大势：不砍掉时政与国际，而是换一种用法（替代方案的核心）
#
# 现状问题：学习强国 10 条 + 参考消息 15 条逐条念标题，占 34% 篇幅、零解读，
#          其中大量是外事会见、军事冲突、体育赛事，对个人决策没有任何指向。
#
# 替代做法：
#   1) 三源（政策 / 国际 / 财经）合并，先剔除「跟个人行动无关」的类型
#   2) 留下的信号归入 4 个「大势域」，每域只取 1 条最有代表性的
#   3) 每条给出「这意味着什么 + 你该怎么做」，取代念标题
#   4) 被剔除的内容不进音频，但仍完整保留在网页清单里备查
# ============================================================
MACRO_DOMAINS = {
    "money":    "钱的价格",
    "market":   "你的钱袋子",
    "demand":   "大家敢不敢花钱",
    "business": "生意好不好做",
    "tech":     "技术在往哪走",
}
MACRO_DOMAIN_ORDER = ["money", "market", "demand", "business", "tech"]

# 关键词 -> 大势域。命中次数最多的域即为该条信号的归属。
MACRO_KEYWORDS = [
    # 域 1：钱的价格（货币、信贷、汇率、债市）
    ("降准", "money"), ("降息", "money"), ("加息", "money"), ("降lpr", "money"),
    ("lpr", "money"), ("利率", "money"), ("货币政策", "money"), ("流动性", "money"),
    ("逆回购", "money"), ("mlf", "money"), ("社融", "money"), ("m2", "money"),
    ("信贷", "money"), ("贷款", "money"), ("存款", "money"), ("汇率", "money"),
    ("人民币", "money"), ("央行", "money"), ("国债", "money"), ("债券", "money"),
    ("银行", "money"), ("货币", "money"), ("外汇", "money"),

    # 域 1.5：你的钱袋子（大盘与资产价格，直接冲击个人持仓）
    ("美股", "market"), ("纳指", "market"), ("道指", "market"), ("标普", "market"),
    ("港股", "market"), ("恒指", "market"), ("a股", "market"), ("上证", "market"),
    ("深证", "market"), ("创业板", "market"), ("科创板", "market"), ("北交所", "market"),
    ("黄金", "market"), ("原油", "market"), ("比特币", "market"), ("基金", "market"),
    ("美债", "market"), ("美元指数", "market"), ("大宗商品", "market"),

    # 域 2：大家敢不敢花钱（消费、物价、楼市、就业、收入、社保）
    ("消费", "demand"), ("社零", "demand"), ("cpi", "demand"), ("ppi", "demand"),
    ("物价", "demand"), ("通胀", "demand"), ("通缩", "demand"), ("楼市", "demand"),
    ("房地产", "demand"), ("房价", "demand"), ("房贷", "demand"), ("购房", "demand"),
    ("就业", "demand"), ("失业率", "demand"), ("招聘", "demand"), ("工资", "demand"),
    ("收入", "demand"), ("生育", "demand"), ("人口", "demand"), ("养老", "demand"),
    ("医保", "demand"), ("社保", "demand"), ("零售", "demand"), ("旅游", "demand"),
    ("餐饮", "demand"), ("家政", "demand"), ("教育", "demand"),

    # 域 3：生意好不好做（产业政策、外贸、监管、补贴）
    ("产业", "business"), ("制造", "business"), ("外贸", "business"), ("出口", "business"),
    ("进口", "business"), ("关税", "business"), ("经贸", "business"), ("贸易", "business"),
    ("民营经济", "business"), ("中小企业", "business"), ("小微企业", "business"),
    ("减税", "business"), ("退税", "business"), ("补贴", "business"), ("降费", "business"),
    ("监管", "business"), ("反垄断", "business"), ("平台经济", "business"),
    ("创业", "business"), ("个体工商户", "business"), ("营商环境", "business"),
    ("订单", "business"), ("供应链", "business"), ("产能", "business"),
    ("价格战", "business"), ("反内卷", "business"), ("不正当竞争", "business"),
    ("营商环境", "business"), ("增值税", "business"), ("所得税", "business"),

    # 域 4：技术在往哪走
    ("人工智能", "tech"), ("大模型", "tech"), ("芯片", "tech"), ("半导体", "tech"),
    ("算力", "tech"), ("新能源", "tech"), ("光伏", "tech"), ("储能", "tech"),
    ("电池", "tech"), ("机器人", "tech"), ("低空", "tech"), ("量子", "tech"),
    ("数据要素", "tech"), ("智能制造", "tech"), ("科技创新", "tech"), ("科技", "tech"),
    ("研发", "tech"), ("算法", "tech"), ("创新药", "tech"), ("商业航天", "tech"),
    ("ai", "tech"),
]

# 只要标题在讲某类资产的价格，就直接归到「你的钱袋子」。
# 「央行增持黄金」若被「央行」拽进「钱的价格」，会配上一段讲借钱成本的解读，听感完全跑偏。
MACRO_ASSET_WORDS = [
    "黄金", "金价", "原油", "油价", "比特币", "美股", "纳指", "道指", "标普",
    "a股", "上证", "深证", "创业板", "科创板", "恒指", "港股", "股价", "涨停",
    "跌停", "收盘", "收涨", "收跌", "大宗商品",
]

# 跟个人决策无关的类型：外事礼仪、人事表彰、军事冲突、国际政坛、体育文娱
# 命中即剔除（哪怕同时含经济词，因为这类标题信息量太低、无法给出行动指向）
MACRO_NEGATIVE = [
    "会见", "会谈", "致电", "贺信", "慰问", "会见外宾",
    "签署命令", "授予", "追授", "表彰", "荣誉称号", "座谈会", "集体学习",
    "听取汇报", "调研", "考察", "任免", "任命", "被查", "落马", "双开",
    "纪律审查", "开除党籍", "受贿", "受审", "判刑",
    "军事", "演习", "军演", "导弹", "战机", "航母", "空袭", "交火",
    "战火", "宣战", "冲突升级", "停火", "伤亡",
    "就职", "宣誓", "当选", "选举", "总统", "首相", "外长", "大使",
    "领事", "弹劾", "议会", "执政党",
    "奥运", "亚运", "冬奥", "世界杯", "足球", "篮球", "乒乓", "夺冠",
    "比赛", "联赛", "明星", "演员", "歌手", "婚礼", "离婚", "去世",
    "逝世", "追悼", "演唱会", "综艺", "票房",
    # 转述性、表态性国际新闻：信息很碎，给不出任何个人行动指向
    "俄媒", "美媒", "英媒", "日媒", "韩媒", "外媒", "据报道", "报道称",
    "呼吁", "警告", "谴责", "指责", "抨击", "抗议", "回应称", "声称",
    "扬言", "放话", "喊话", "爆料", "辟谣",
    # 突发社会/安全事件：属新闻，但不构成可判断的趋势信号
    "黑客", "攻击", "泄露", "诈骗", "被捕", "受审", "维权", "投诉", "事故",
]


def _macro_domain_of(title: str) -> str:
    """判断一条时政/财经标题属于哪个大势域；跟个人决策无关则返回空串"""
    t = (title or "").lower()
    if not t:
        return ""
    # 先剔除明确无关的类型
    if _hits_any(t, MACRO_NEGATIVE):
        return ""
    # 只要是讲某类资产价格的，一律归到「你的钱袋子」。
    # 否则「央行增持黄金」会被「央行」拽进「钱的价格」，配上借钱成本的解读，听感完全跑偏。
    if _hits_any(t, MACRO_ASSET_WORDS):
        return "market"
    score: Dict[str, int] = {}
    for kw, dom in MACRO_KEYWORDS:
        if _kw_hit(t, kw):
            score[dom] = score.get(dom, 0) + 1
    if not score:
        return ""
    # 命中次数最多的域胜出；打平按固定顺序（钱 -> 需求 -> 生意 -> 技术）
    return max(score.items(), key=lambda kv: (kv[1], -MACRO_DOMAIN_ORDER.index(kv[0])))[0]


def build_macro_trends(pools: Dict[str, List[Dict[str, Any]]], exclude_titles: List[str] = None) -> List[Dict[str, Any]]:
    """
    把时政 / 国际 / 财经三源合并，筛出跟个人决策有关的信号，每个大势域只取 1 条。
    取数时优先选择尚未用过的来源，避免四条全来自同一家。
    """
    exclude_titles = exclude_titles or []
    candidates: Dict[str, List[Dict[str, Any]]] = {d: [] for d in MACRO_DOMAIN_ORDER}

    for cat in ("学习强国", "新浪财经", "参考消息"):
        for it in pools.get(cat, []):
            title = it.get("title", "")
            if not title:
                continue
            if any(is_similar_title(title, ex) for ex in exclude_titles):
                continue
            dom = _macro_domain_of(title)
            if dom:
                candidates[dom].append(it)

    used_sources = set()
    trends: List[Dict[str, Any]] = []
    for dom in MACRO_DOMAIN_ORDER:
        pool = candidates[dom]
        if not pool:
            continue
        chosen = next((it for it in pool if it.get("source_name") not in used_sources), pool[0])
        used_sources.add(chosen.get("source_name"))
        trends.append({
            "title": chosen["title"],
            "category": "宏观大势",
            "domain": dom,
            "domain_label": MACRO_DOMAINS[dom],
            "summary": chosen.get("summary", chosen["title"]),
            "why_matter": "",
            "source_name": chosen.get("source_name", ""),
            "url": chosen.get("url", ""),
            "published_at": chosen.get("published_at", ""),
            "is_fallback": False,
        })
    return trends


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
    # 中文标点前后不留空格，避免「。 一笔」这种断句被读成两截
    text = re.sub(r'\s*([。！？；：，、])\s*', r'\1', text)
    return text


# 摘要里的推广 / 版权模板句：不清理会被当成正文念出来
# （上一版就曾把「查看全文，本文为会员文章，订阅后可阅读全文」原样播出去）
SUMMARY_NOISE_PATTERNS = [
    "查看全文", "本文为会员文章", "订阅后可阅读全文", "会员文章", "付费阅读",
    "阅读原文", "点击查看", "扫码", "扫描二维码", "关注公众号", "本文来自",
    "题图来自", "头图来自", "图片来源", "如有侵权", "转载请注明", "原文链接",
    "责任编辑", "本文作者", "编辑：", "作者：", "转载请", "版权归",
]

# 聚合类稿件：一天塞十几条杂讯，命中率低、噪声高，整条丢弃
AGGREGATOR_NOISE = [
    "8点1氪", "9点1氪", "10点1氪", "点1氪", "科氪", "早报", "晚报", "午报", "日报", "周报",
    "快讯汇总", "热点汇总", "热点导览", "一周要闻", "今日要闻", "新闻盘点", "盘前", "盘中",
    "收盘播报", "一文读懂", "一文看懂", "速览", "合集",
]


def _is_stale(published: str, max_days: int = 10) -> bool:
    """
    发布时间太久的条目直接丢弃。
    「过去 24 小时」的播报里如果混进几年前的旧文，听感上就是假话，比没有更糟。
    解析不出日期的（部分源不带时间）一律保留，不误伤。
    """
    raw = (published or "").strip()
    if not raw:
        return False
    dt = None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except Exception:
        dt = None
    if dt is None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                dt = datetime.datetime.strptime(raw[:19], fmt)
                break
            except Exception:
                continue
    if dt is None:
        return False
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return (datetime.datetime.utcnow() - dt).days > max_days


def _clean_summary(text: str) -> str:
    """剔除摘要里的推广 / 付费墙 / 版权模板句"""
    if not text:
        return ""
    pieces = re.split(r'(?<=[。！？!?；;])', text)
    kept = [p for p in pieces if p.strip() and not any(n in p for n in SUMMARY_NOISE_PATTERNS)]
    return "".join(kept).strip()


def _is_aggregator(title: str) -> bool:
    """判断是否为聚合类稿件（早报、快讯汇总等）"""
    return any(n in (title or "") for n in AGGREGATOR_NOISE)


def _shorten_summary(text: str, limit: int = 90) -> str:
    """
    把摘要压到一两句话。
    36氪等源的 description 其实是正文开头，不压缩就会把整篇文章念出来。
    """
    if not text:
        return ""
    text = re.sub(r'作者\s*[|｜]\s*[^\s]{1,14}\s*编辑\s*[|｜]\s*[^\s]{1,14}', '', text)
    text = re.sub(r'本文约?\s*\d+\s*字[，,]?\s*建议阅读\s*\d+\s*分钟', '', text)
    text = re.sub(r'[（(]\s*(新浪财经|36氪|极客公园|爱范儿|少数派|量子位|InfoQ[^）)]*)\s*[）)]', '', text)
    text = re.sub(r'\s+', ' ', text).strip(' ，,。')
    if len(text) <= limit:
        return text

    out = ""
    for piece in re.split(r'(?<=[。！？!?])', text):
        if len(out) + len(piece) > limit:
            break
        out += piece
    if out:
        return out.strip()

    head = text[:limit]
    cut = max(head.rfind('，'), head.rfind('；'), head.rfind(','))
    return (head[:cut] if cut > limit * 0.5 else head).rstrip('，,；; ')


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

    async def _fetch_from_sources(self, client: httpx.AsyncClient, sources: List[Dict], category: str, max_items: int = 3, gate_keywords: List[str] = None, block_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """从一组 RSS/Atom 源抓取真实新闻；带黑名单与相关性闸门，逐源降级，够数即止"""
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
                    # 聚合类稿件（早报、快讯汇总）噪声极高，整条不要
                    if _is_aggregator(title):
                        continue
                    # 旧文不要：别让「过去 24 小时」里混进几年前的帖子
                    if _is_stale(fi.get("published", "")):
                        continue
                    # 摘要先洗掉付费墙 / 推广模板句，再压到一两句
                    summary = _clean_summary(fi.get("summary", "")[:400])
                    if len(summary) < 8:
                        summary = title
                    summary = _shorten_summary(summary, 60)
                    # 题材黑名单（生活类源里的菜谱、装备、壁纸等）
                    if block_keywords and _hits_any(title.lower(), block_keywords):
                        continue
                    # 过滤纯英文长句，保证中文环境纯正
                    if is_mostly_english(title) or is_mostly_english(summary):
                        continue
                    # 相关性闸门：只看标题判断，跟本板块无关的直接丢弃，绝不凑数。
                    # 不能看摘要——36氪这类源的摘要是多条汇总，几乎什么词都有，会把闸门带偏。
                    if gate_keywords and not _hits_any(title.lower(), gate_keywords):
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

        ai_items = await self._fetch_from_sources(
            client, AI_RSS_SOURCES, "AI Agent", max_items=3, gate_keywords=AI_GATE_KEYWORDS
        )
        opc_items = await self._fetch_from_sources(
            client, OPC_RSS_SOURCES, "一人公司", max_items=3,
            gate_keywords=OPC_GATE_KEYWORDS, block_keywords=OPC_BLOCK_KEYWORDS
        )

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

        # 从时政 / 国际 / 财经三源里提炼今日宏观大势（每域一条，后接影响与行动）。
        # 注意：原始清单仍然完整保留，只是音频不再逐条念。
        results["宏观大势"] = build_macro_trends(
            results,
            exclude_titles=[it["title"] for it in (results["AI Agent"] + results["一人公司"])],
        )

        return results


collector = NewsCollector()
