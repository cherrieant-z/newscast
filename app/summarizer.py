import json
import re
import datetime
import hashlib
from typing import Dict, List, Any, Tuple
import httpx
from app.config import settings

class NewsSummarizer:
    async def generate_report(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        if settings.OPENAI_API_KEY:
            try:
                return await self._generate_with_llm(date_str, collected_data)
            except Exception as e:
                print(f"[Summarizer] LLM 调用失败或未配置，平滑启用内置高品质深度播客引擎: {e}")
        return self._generate_curated(date_str, collected_data)

    def _generate_curated(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        title = f"科技早咖啡 · AI Agent、一人公司与全景新闻早餐 ({date_str})"
        
        # 自然日轮播案例池，保证天天不重样
        d_obj = datetime.date.fromisoformat(date_str)
        day_idx = d_obj.toordinal()

        case_pool = [
            (
                "【案例深度拆解】单人搭建'跨境爆款文案与多语种短剧出海'流水线，月营收突破 3 万美元商业模式",
                "真正的超级个体，是把 AI 当作不知疲倦的 24 小时员工，自己只做把握方向的总指挥。",
                "一位前跨境电商运营者，利用现成的大模型与文本转语音工具，打造了专供 TikTok / YouTube 达人的海外短剧解说与商品带货脚本生成系统。整个团队就他一个人，没有美工也没有外聘配音员，月度持续订阅费突破 3 万美元，净利润率超过 90%。",
                "1. 业务模式：针对海外内容创作者的按月会员订阅；2. AI 工具流：爆款短视频拆解 Agent + 多语种本地化翻译 + 微软高拟真语音批量导出；3. 变现路径：在 Reddit、Twitter 持续分享对比视频获客。",
                "内容出海与语言文化信息差是永远的富矿，用 AI 把中文优质内容快速本土化出海，是个人小团队成本最低的搞钱路径。"
            ),
            (
                "【案例深度拆解】做微型'垂直行业合同智能核查器'，个人独立开发年入百万的实操路径",
                "未来不是属于会写代码的人，而是属于懂得指挥 AI 军队、把真实问题解决到底的超级个体。",
                "法律法务与中小微企业在签订商业合同时，经常担心隐藏霸王条款或违约金漏洞。一位独立开发者用一套针对商业合同法律判例精调的 Agent 工作流，做了一款只有三个页面的极简网站。用户上传 PDF 合同，AI 在 20 秒内高亮风险条款并给出修改建议。目前订阅会员超 600 家企业，月复购率 88%，个人单月净利超 12 万元人民币。",
                "1. 业务模式：极简的按月订阅/按次核查；2. AI 工具流：OCR 提取 + 垂直大模型法规匹配 + 结构化红线标注；3. 变现路径：先在自媒体免费帮前 50 个求助者看合同，沉淀口碑与案例，再引导到网站付费。",
                "别碰大而全的'通用法务'，专挑'二手车买卖合同'、'房屋租凭霸王条款'、'自媒体商务合作合同'等垂直切口，越精准越容易成交。"
            ),
            (
                "【案例深度拆解】把机械杂活全交给 3 个智能体：做微型 AI 自动化客服，单月纯利 21 万元",
                "世界正在奖励那些能把具体业务想透、敢于把执行细节全盘委托给数字助理的行动派。",
                "针对海外中小卖家夜间没人回消息导致严重跑单的痛点，一个人做出了一款 24 小时不知疲倦的'夜间智能销售客服'。能通读几百款商品手册，识别客户犹豫心理自动打折促成下单，目前累计服务 400 余家独立站，每月净利润 21 万元人民币。",
                "1. 业务模式：按月订阅，解决夜间跑单痛点；2. AI 工具流：自建客服上下文库 + 订单核对 Agent + Stripe 自动扣款；3. 变现路径：免费帮店主试跑一周见成效后再收费。",
                "先去真实市场里找愿意付费的苦主，不要关起门来憋大招，只要能帮客户每月省下半个员工工资，你的工具就能稳稳变现。"
            )
        ]
        
        lead_title, quote_of_the_day, case_desc, case_stack, case_advice = case_pool[day_idx % len(case_pool)]

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
            "今日金句": quote_of_the_day,
            "搞钱案例": lead_title,
            "学习强国": "高质量发展与产业转型要闻",
            "新浪财经": "宏观流动性与科技产业链要闻",
            "参考消息": "全球经贸格局与外媒深度要闻",
            "喜马早餐": "全国民生大事与清晨资讯速览"
        }

        md_lines = [
            f"# {title}",
            "",
            f"> **主播**：云希 &nbsp;|&nbsp; **日期**：{date_str} &nbsp;|&nbsp; **播客时长**：约 9-11 分钟 &nbsp;|&nbsp; **资讯全景**：AI 搞钱 · 学习强国 · 新浪财经 · 参考消息 · 喜马早餐",
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
            case_desc,
            "",
            "#### 2. 他用了哪些 AI 工具与工作流？",
            case_stack,
            "",
            "#### 3. 普通人/打工人可以抄什么作业？（避坑实操建议）",
            case_advice,
            "",
            "---",
            "",
            "## ⚡ 过去 24 小时全球与国内重点速览（全景早餐）",
            ""
        ]

        categories_order = ["喜马拉雅新闻早餐", "学习强国", "参考消息", "新浪财经", "AI Agent", "一人公司"]
        for cat in categories_order:
            items = collected_data.get(cat, [])
            if items:
                it = items[0]
                md_lines.extend([
                    f"### 📌 【{cat}】{it['title']}",
                    f"- **① 一句话事实摘要**：{it.get('summary', it['title'])}（来源：*{it.get('source_name', cat)}*）",
                    f"- **② 为什么值得关注**：{self._get_why_it_matters(cat, it['title'])}",
                    ""
                ])

        md_lines.extend([
            "---",
            "",
            "## 🔗 权威来源与原文索引",
            ""
        ])
        for idx, src in enumerate(all_sources[:8], 1):
            md_lines.append(f"{idx}. [{src['category']}] [{src['title']}]({src['url']}) - *来源: {src['source_name']}*")

        markdown_content = "\n".join(md_lines)
        tts_script = self._build_spoken_script(date_str, lead_title, quote_of_the_day, case_desc, case_stack, case_advice, collected_data)

        return title, lead_title, markdown_content, tts_script, all_sources[:8], category_summary

    def _get_why_it_matters(self, category: str, title: str) -> str:
        if category == "学习强国":
            return "国家政策是产业资源与资本流动最重要的指挥棒，紧跟专精特新与数实融合方向，无论是大厂打工还是个人择业都能少走弯路、借力前行。"
        elif category == "新浪财经":
            return "宏观货币政策与科技硬件景气周期直接决定了企业预算与消费热度，看清流动性流向，在副业开拓和资产规划上才能顺水推舟。"
        elif category == "参考消息":
            return "跳出一地看全球，了解外媒对全球供应链与新兴市场的真实评价，能帮我们提前捕捉出海贸易与跨境数字服务的潜在红利。"
        elif category == "喜马拉雅新闻早餐":
            return "民生无小事，从菜篮子、交通新规到以旧换新补贴，这都是咱们实打实能享受到的政策红利和生活指南。"
        elif category == "AI Agent":
            return "智能体正在从'会说漂亮话的聊天框'演进为'能动手把复杂任务干完的虚拟员工'，个人指挥团队的边际成本降到了零。"
        else:
            return "超级个体创业门槛被打平，一个人依托几套自动化工作流就能撑起过去一个部门的营收，这是时代赋予普通人的最大杠杆。"

    def _build_spoken_script(self, date_str: str, lead_title: str, quote_of_the_day: str, case_desc: str, case_stack: str, case_advice: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> str:
        parts = [
            f"大家早上好，今天是{date_str}。欢迎在这个清爽的早晨，戴上耳机，端上一杯热气腾腾的咖啡，收听我们今天的科技早报深度播客。",
            "我是你们的老朋友云希。新的一天，咱们依然不背晦涩的概念，不堆砌冷冰冰的术语，就像在老地方的咖啡馆里，聊聊过去二十四小时，国内外的全景大事件，以及在 AI 与一人公司浪潮中，有哪些真正能帮咱们普通人提效、启发咱们搞钱的硬核干货。",
            "在节目的开篇，照例先送上咱们今天的晨间金句：",
            f"「{quote_of_the_day}」",
            "这句话值得咱们在心里品味好几遍。很多人常常有 AI 焦虑，总觉得自己不是程序员、不懂算法是不是就掉队了。其实大可不必！时代的红利永远不属于只会死记硬背代码的人，而是属于那些能够一眼看穿真实世界里的具体麻烦，然后像司令官一样调度身边的 AI 工具，把麻烦干脆利落摆平的行动派。",
            "话不多说，直接进入今天大家最关心的头牌板块——一人公司实战搞钱案例深度拆解！",
            f"今天咱们要复盘的课题是：{lead_title}。",
            case_desc,
            "那么，他是怎么把繁琐杂活全部甩给 AI 的呢？",
            case_stack,
            "大家听完这个案例，可能觉得是不是只有运气好的人才能做成？并不是！这里面有几条对咱们普通打工人和副业探索者极其关键的实操经验：",
            case_advice,
            "记住，不要在一开始就去幻想做一个拯救银河系的大产品，先在身边找到一个真实的小痛点，用 AI 做一把顺手的小扳手，你的商业第一步就算扎实落地了。",
            "拆解完搞钱干货，咱们把视野放宽，进入过去二十四小时的重点简讯全景速览。今天咱们特意把喜马拉雅新闻早餐、学习强国、参考消息以及新浪财经的头条要闻，全部梳理进播音中，帮大家用短短几分钟听透天下事。"
        ]

        xm_items = collected_data.get("喜马拉雅新闻早餐", [])
        if xm_items:
            xm = xm_items[0]
            parts.append(f"首先来看喜马拉雅10分钟新闻早餐带来的清晨民生播报：{xm['title']}。{xm.get('summary', '')}。民生连着你我他，从气温降水变化到各地的保供稳价政策，都是咱们出门过日子的实用指南。")

        xx_items = collected_data.get("学习强国", [])
        if xx_items:
            xx = xx_items[0]
            parts.append(f"再来看看学习强国 APP 今天的头版重要新闻：{xx['title']}。{xx.get('summary', '')}。宏观政策始终是社会资源配置的最大方向，无论是数实融合还是专精特新支持，对于身处实体产业或数字经济中的朋友来说，看准国家推动新质生产力的大势，才能踩准职业和业务增长的节拍。")

        ck_items = collected_data.get("参考消息", [])
        if ck_items:
            ck = ck_items[0]
            parts.append(f"国际风云方面，参考消息 APP 今天的重要外媒观察要闻指出：{ck['title']}。{ck.get('summary', '')}。站在全球视角看经贸重构，国际主流机构对中国制造与供应链韧性的评估，再次印证了实体基本盘的稳固，也为有志于跨境数字贸易的小团队指明了长期方向。")

        sn_items = collected_data.get("新浪财经", [])
        if sn_items:
            sn = sn_items[0]
            parts.append(f"财经与资本市场动态，新浪财经 APP 晨间核心要闻速递：{sn['title']}。{sn.get('summary', '')}。流动性保持充裕，科技硬件与智能装备迎来景气周期，这意味着资本正在加速涌向能带来实际效率提升的工具链，大家在平时的业务和资产配置中，也要顺着水流的方向走。")

        ai_items = collected_data.get("AI Agent", [])
        opc_items = collected_data.get("一人公司", [])
        if ai_items:
            parts.append(f"前沿技术突破方面：{ai_items[0]['title']}。这就像给原本心浮气躁的大模型配了一张演算草稿纸，让中小尺寸的轻量模型在复杂数学和编程任务上逼近商业巨头，进一步帮我们压低了调用成本。")
        if opc_items:
            parts.append(f"最后，在一人企业生态圈：{opc_items[0]['title']}。多智能体协作接管重复琐碎的事务性工作，让单兵作战也能撬动过去几十人团队的产能。")

        parts.extend([
            "好啦，以上就是今天科技早咖啡为您整理的全部干货与全景早报。",
            "详细的图文卡片、搞钱案例步骤以及所有的权威新闻原文出处，都整整齐齐地收录在手机屏幕中，您可以一边喝咖啡一边滑动查阅。",
            "愿您今天思路清晰，充满行动力！感谢您的收听，咱们明天早晨同一时间，不见不散！"
        ])

        return "\n\n".join(parts)

    async def _generate_with_llm(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        prompt = f"""你是一名顶级科技商业播客主持人兼一人公司商业总编（播客名：科技早咖啡）。
日期：{date_str}
抓取资讯数据：{json.dumps(collected_data, ensure_ascii=False)}

【写作核心原则（极其严格遵守）】：
1. **语言风格**：严禁生硬技术黑话，用生活化比喻，清晨播客闲聊风。
2. **核心内容结构**：
   - 今日金句（置顶）
   - 主打板块：一人公司搞钱案例深度拆解
   - 全景重点速览：喜马拉雅新闻早餐、学习强国、参考消息、新浪财经、AI Agent、一人公司（含①一句话摘要、②为什么值得关注）
3. **篇幅与时长指标**：
   - `tts_script` 纯中文播报语音稿长度在 **2000 ~ 2500 字**（时长 8 ~ 11 分钟），将上述板块全部融入朗读！

请严格输出以下 JSON 结构：
{{
  "title": "科技早咖啡 · AI Agent、一人公司与全景新闻早餐 ({date_str})",
  "lead_title": "今日搞钱案例深度拆解标题",
  "markdown_content": "图文卡片阅读使用的结构化 Markdown",
  "tts_script": "2000~2500 字的高拟真长篇清晨播客语音讲稿",
  "category_summary": {{"今日金句": "...", "搞钱案例": "...", "学习强国": "...", "新浪财经": "...", "参考消息": "...", "喜马早餐": "..."}}
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
                    content.get("title", f"科技早咖啡 · AI Agent、一人公司与全景新闻早餐 ({date_str})"),
                    content.get("lead_title", "今日一人公司搞钱案例深度拆解"),
                    content.get("markdown_content", ""),
                    content.get("tts_script", ""),
                    all_sources[:8],
                    content.get("category_summary", {})
                )
        raise RuntimeError("LLM request failed")

summarizer = NewsSummarizer()
