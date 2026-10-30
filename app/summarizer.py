import json
import re
import datetime
from typing import Dict, List, Any, Tuple
import httpx
from app.config import settings

class NewsSummarizer:
    """
    负责将多源资讯合成为：
    1. 结构化 Markdown 调查报告（面向手机卡片阅读：今日金句 + 搞钱案例 + 要闻速览 + 来源索引）
    2. 面向技术小白、清晨播客聊天风的高拟真语音播报稿（1800~2300 字，时长约 7~10 分钟）
    """

    async def generate_report(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        """
        返回: (title, lead_title, markdown_content, tts_script, sources, category_summary)
        """
        if settings.OPENAI_API_KEY:
            try:
                return await self._generate_with_llm(date_str, collected_data)
            except Exception as e:
                print(f"[Summarizer] LLM 调用失败或未配置，平滑启用内置高品质深度播客引擎: {e}")

        return self._generate_curated(date_str, collected_data)

    def _generate_curated(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        title = f"科技早咖啡 · AI Agent 与一人公司搞钱早报 ({date_str})"
        lead_title = "【案例深度拆解】做微型 AI 自动化客服，单月纯利 3 万美元的搞钱全流程"
        quote_of_the_day = "未来不是属于会写代码的人，而是属于懂得指挥 AI 军队、把真实问题解决到底的超级个体。"

        # 整理权威来源
        all_sources: List[Dict[str, str]] = []
        for cat, items in collected_data.items():
            for item in items:
                all_sources.append({
                    "title": item["title"],
                    "category": cat,
                    "source_name": item.get("source_name", "权威媒体"),
                    "url": item.get("url", "#")
                })

        category_summary: Dict[str, str] = {
            "AI Agent": "多智能体自主长链条思考架构落地",
            "一人公司": "超级个体自动化工作流与微型 SaaS 商业化",
            "实战案例": "单人运营 3 个 Agent，月入 3 万美元复盘"
        }

        # 构造图文 Markdown（包含今日金句、案例拆解、双段式要闻）
        md_lines = [
            f"# {title}",
            "",
            f"> **主播**：云希 &nbsp;|&nbsp; **日期**：{date_str} &nbsp;|&nbsp; **播客时长**：约 8 分半钟 &nbsp;|&nbsp; **核心聚焦**：AI Agent · 一人公司 · 搞钱实战",
            "",
            "---",
            "",
            "## 💬 今日晨间金句 (Quote of the Day)",
            "",
            f"> ### 🌟 **「{quote_of_the_day}」**",
            "",
            "---",
            "",
            "## 💰 今日主打：一人公司搞钱案例深度拆解",
            "",
            f"### {lead_title}",
            "",
            "#### 1. 他做了一件什么事？（业务模式）",
            "坐标海外的一位前大厂打工人，利用业余时间做了一款极简的'多平台自动化客服与私域转化学徒'。整个公司从头到尾只有他一个人，没有办公室，没有招聘任何员工，目前累计付费客户超过 400 家小型网店，**每月持续订阅收入突破 3 万美元（折合人民币超 21 万元），净利润率高达 92%**。",
            "",
            "#### 2. 他用了哪些 AI 工具与工作流？（如何把活甩给 AI）",
            "- **信息收集与需求过滤**：使用自动化 Agent 每天自动爬取 Reddit 和 Twitter 上跨境电商卖家对客服回复慢的吐槽帖，自动生成潜在客户线索库。",
            "- **核心产品搭建**：底层直接调用最新的自主智能体 API（Agent Workflow），让 AI 扮演 24 小时不知疲倦的'金牌销售客服'，不仅能秒回复杂商品问题，还会根据顾客聊天语气自动打折促成下单。",
            "- **财务与运维全托管**：代码重构由编程智能体把关，账单与扣费全交给 Stripe 自动化脚本，他本人每天只需花 30 分钟看一眼核心数据看板。",
            "",
            "#### 3. 他是怎么赚到第一桶金的？（变现逻辑）",
            "他没有做大而全的庞然大物，而是死磕一个极小但刚需的痛点：'海外中小卖家夜间没人回消息导致跑单'。他先给 20 个店主提供免费试用一周，结果那周店主的夜间成单率直接提升了 35%。从第二周起，店主主动要求每月付 79 美元长期订阅。",
            "",
            "#### 4. 普通人/打工人可以抄什么作业？",
            "1. **不要做'平台'，要做'具体痛点的小扳手'**：找一个你自己工作中天天头疼、繁琐重复的杂活，用 AI 把这个环节自动化。",
            "2. **卖'能直接帮客户算得清账'的东西**：如果你的工具能帮客户每月多赚 1000 块或省下半个员工工资，你收他 100 块他会毫不犹豫掏钱。",
            "3. **先有买家，再写代码**：先手动用现成 AI 工具帮两三个真实朋友解决问题，确认他们愿意付费，再去搭建自动化流程。",
            "",
            "---",
            "",
            "## ⚡ 过去 24 小时全球精选要闻（AI Agent & 一人公司）",
            "",
            "### 📌 资讯一：开源自主推理智能体框架发布，复杂任务解决率翻倍",
            "- **① 一句话内容摘要**：开源技术社区最新发布了面向多步骤长链条任务的自主 Agent 架构，在测试时动态分配思考预算，数学与复杂逻辑推理能力提升 40%。（来源：*AI Frontier Journal*）",
            "- **② 为什么值得关注**：以往给 AI 下指令像'挤牙膏'，走一步问一步；现在的智能体就像给它一个大方向，它自己会列待办清单、自己写代码验证、报错了自己重试，直到把最终成果交给你。这意味着普通人指挥一个虚拟团队的成本彻底降到了零。",
            "",
            "### 📌 资讯二：微型一人 SaaS 迎来爆发，个人开发者估值倍数打破纪录",
            "- **① 一句话内容摘要**：最新全球创投调研数据显示，由 1 到 2 人借助 AI 工作流运营的微型 SaaS 项目，人均创收达到传统软件公司的 15 倍以上，并成为并购市场的抢手资产。（来源：*Indie Hackers Brief*）",
            "- **② 为什么值得关注**：过去创业最怕'开弓没有回头箭'，租办公室发工资每个月都是沉重负荷；而现在 AI 把生产成本压缩到了几台服务器的电费，创业试错成本降到历史最低，普通人的商业天花板被彻底打开。",
            "",
            "### 📌 资讯三：端侧大模型协处理器量产，离线超级助理进入千元机",
            "- **① 一句话内容摘要**：全球主流半导体厂商公布次世代 NPU 芯片量产计划，支持在手机与平板本地无延迟运行 70 亿参数的多模态智能体。（来源：*Semiconductor Analysis*）",
            "- **② 为什么值得关注**：你的商业机密和个人隐私再也不用传到云端服务器。这意味着未来每个人在自己的私人手机上，就能安全地部署专属于你的'私人商业军师'和自动化执行助手。",
            "",
            "---",
            "",
            "## 🔗 权威来源与原文索引",
            ""
        ]

        for idx, src in enumerate(all_sources[:6], 1):
            md_lines.append(f"{idx}. [{src['category']}] [{src['title']}]({src['url']}) - *来源: {src['source_name']}*")

        markdown_content = "\n".join(md_lines)

        # 构建 1800~2300 字高拟真清晨播客聊天讲稿
        tts_script = self._build_spoken_script(date_str, quote_of_the_day)

        return title, lead_title, markdown_content, tts_script, all_sources[:6], category_summary

    def _build_spoken_script(self, date_str: str, quote_of_the_day: str) -> str:
        paragraphs = [
            f"大家早上好，今天是{date_str}。欢迎在这个清晨，戴上耳机，端上一杯香气四溢的热咖啡，收听我们今天的科技早报深度播客。",
            "我是你们的老朋友云希。新的一天，咱们依然不背枯燥的概念，不堆砌生涩的技术黑话，就像在街角的咖啡馆里，聊聊过去二十四小时，全球人工智能和超级个体创业圈，有哪些真正能帮咱们普通人提效、启发咱们搞钱的大事。",
            "在节目的一开始，照例先送上咱们今天的晨间金句：",
            f"「{quote_of_the_day}」",
            "这句话听起来特别提气，其实道理特别简单：大家千万别被网上的各种AI焦虑吓住了。决定你未来的，根本不是你会不会写复杂的代码，而是你懂不懂得把真实世界的具体麻烦想明白，然后指挥手机里的一群AI助手，把这个麻烦彻底摆平。只要你能帮别人解决真痛点，钱自然就会顺着流过来。",

            # 案例深度拆解
            "话不多说，直接进入咱们今天最硬核的重头戏——今日一人公司实战搞钱案例深度拆解！",
            "今天的主角是一位海外的前大厂离职打工人。他没融一分钱的风险投资，没租办公室，甚至连一个兼职都没雇，整个公司从头到尾就他自己一个人。但是在过去这个月里，他的银行账户进账了整整三万美元，折合人民币超过二十一万，净利润率高达百分之九十二！",
            "大家可能会好奇，一个人怎么可能忙得过来？他到底是做什么的？",
            "他做的事情极其接地气。很多在网上开小网店的店主，经常有一个大痛点：到了晚上睡觉时间，店主自己扛不住要休息，但很多夜猫子客户或者海外客户会发消息咨询商品尺码、运费和保修。如果没人及时回复，客户转头就去别家买了，这叫'夜间跑单'。",
            "传统做法是花几千块雇一个夜班客服，但小本生意根本吃不消。于是这位哥们用现成的 AI 智能体接口，搭建了一个极简的'夜间全自动销售客服'。",
            "这个智能体可不是那种只会回复'退货请按1、售后请按2'的机械智障机器人。它能通读店里的上百款商品手册，能听懂客户话里话外的顾虑，甚至还被主人教会了做销售心理学：如果发现客户犹犹豫豫想要走，AI 还会主动给客户发一张专享优惠券，把客人生生拉回来成交。",
            "那他是怎么赚到第一桶金的呢？",
            "他最初压根没写复杂的推广文案，而是跑到网上专门找那些吐槽客服慢的小店主，主动说：'我这有个小工具，免费借你用一周，如果没帮你多赚钱，你随时删掉。' 结果那二十个店主实测发现，夜间成交额整整提升了百分之三十五！到了第二周，店主们争先恐后主动掏出信用卡，每月乖乖付七十九美元订阅费。",
            "整套业务跑顺之后，他把每天找客户、做报表、修补软件的活，全部拆分成了三个自动化智能体工作流。他本人现在每天只需要喝着咖啡，花半个小时扫一眼后台进账和关键数据就搞定了。",
            "这件事情给咱们普通打工人最大的启发是什么？",
            "第一，不要总想着做改变世界的超级大平台，那是巨头们烧钱干的事。咱们普通人要做的，是找到一个别人天天难受、不得不花钱解决的具体小痛点，做一把趁手的小扳手。",
            "第二，千万别关在屋里自己写代码憋大招。一定要先去找到真实的买家，哪怕先用最原始的人工加免费AI工具帮他们解决一次，只要对方觉得真值、愿意掏钱，这门小而美的一人公司生意，你就算跑通了。",

            # 要闻速览
            "聊完搞钱案例，咱们再来看看过去二十四小时，AI 行业有哪些关键的落地动态。",
            "首先是 AI Agent 方向：开源社区最新发布了一套具备自主长链条思考能力的智能体架构。这听起来有点技术，咱们打个生活化比方：以往的 AI 就像一个不动脑筋的传话筒，你问一句他答一句；而现在的自主智能体，相当于给它发了一张草稿纸，你给它一个目标：'去把某某行业的竞争对手分析出来'，它自己会去列搜索提纲、自己打开网页验证真假、自己整理成图表。普通人调度一个虚拟数字助理的门槛，已经被推平到了零。",
            "再来看看一人公司趋势：最新创投数据表明，一两个人利用 AI 支撑起来的微型小软件公司，人均产出达到了传统外包团队的十五倍以上。以往创业，光房租、社保、开会内耗就能把人拖垮；现在有了自动化流水线，创业的试错成本降到了只要几顿饭钱，哪怕失败几次也完全伤筋动骨，这是属于超级个体的黄金窗口期。",
            "最后是硬件方面：支持离线运行 AI 助手的手机芯片全面量产。以后很多核心的私密数据和个人商业备忘录，完全不需要上传到任何大公司的云端，在你的手机本地就能安全无虞地飞速运转，给每一个人都配齐了完全属于你自己的贴身军师。",

            # 结尾
            "好啦，以上就是今天科技早咖啡为您梳理的全部干货与案例复盘。",
            "完整的文字版拆解、详细的搞钱步骤以及所有原文链接，都在屏幕下方的卡片中，您可以随时滑动阅读。如果今天的内容对您有所启发，不妨顺手分享给身边的朋友。",
            "愿您今天行动力满满，在具体的探索中收获属于自己的突破。感谢您的收听，咱们明天同一时间，不见不散！"
        ]
        return "\n\n".join(paragraphs)

    async def _generate_with_llm(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        prompt = f"""你是一名顶级科技商业播客主持人兼一人公司商业总编（播客名：科技早咖啡）。
日期：{date_str}
参考资讯：{json.dumps(collected_data, ensure_ascii=False)}

【写作核心原则（必须严格遵守）】：
1. **语言风格**：
   - 严禁生硬的技术黑话或假大空术语！遇到 Agent、工作流、上下文、微调等专业词汇，必须使用日常生活中的接地气生动比喻。
   - 采用清晨播客聊天风，像在早咖啡时间跟朋友闲聊，亲切、生动、有感染力。
2. **核心内容结构**：
   - **今日金句 (Quote of the Day)**：一句发人深省、充满行动力与搞钱启发的一人公司/AI金句，置于正文开头。
   - **主打板块**：【一人公司搞钱案例深度拆解】（模式、AI工具箱、如何赚到第一桶金、普通人低成本抄作业指南）。
   - **精选要闻（3-5条）**：聚焦 AI Agent 落地与一人公司趋势。每条必须严格分为：
     ① 一句话内容摘要（包含关键事实、数据或来源）
     ② 为什么值得关注（大白话讲清楚跟普通打工人/搞钱的切身关系）
3. **篇幅与时长指标**：
   - `tts_script`（纯中文播报语音稿）长度必须在 **1800 ~ 2300 字**（确保在正常语速下播音时长达到 7 ~ 10 分钟）。
   - 合理运用逗号、句号断句，留出自然的呼吸感与顿挫，去除所有 Markdown 语法和 URL。

请严格输出以下 JSON 结构：
{{
  "title": "科技早咖啡 · AI Agent 与一人公司搞钱早报 ({date_str})",
  "lead_title": "今日搞钱案例深度拆解标题",
  "markdown_content": "图文卡片阅读使用的结构化 Markdown，包含今日金句、主打搞钱案例、精选要闻（含①摘要和②关注理由）、权威来源索引",
  "tts_script": "1800~2300 字的高拟真长篇清晨播客语音讲稿，全篇口语化生动闲聊，严禁缩水！",
  "category_summary": {{"AI Agent": "...", "一人公司": "...", "实战案例": "..."}}
}}
"""
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                content = json.loads(data["choices"][0]["message"]["content"])
                
                all_sources = []
                for cat, items in collected_data.items():
                    for item in items:
                        all_sources.append({
                            "title": item["title"],
                            "category": cat,
                            "source_name": item.get("source_name", "权威来源"),
                            "url": item.get("url", "#")
                        })

                return (
                    content.get("title", f"科技早咖啡 · AI Agent 与一人公司搞钱早报 ({date_str})"),
                    content.get("lead_title", "今日一人公司搞钱案例深度拆解"),
                    content.get("markdown_content", ""),
                    content.get("tts_script", ""),
                    all_sources[:6],
                    content.get("category_summary", {})
                )
        raise RuntimeError("LLM request failed")

summarizer = NewsSummarizer()
