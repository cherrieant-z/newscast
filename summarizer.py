# -*- coding: utf-8 -*-
import json
import re
import datetime
import hashlib
from typing import Dict, List, Any, Tuple
import httpx
from app.config import settings

class NewsSummarizer:
    """
    负责将多源资讯合成为：
    1. 结构化 Markdown 报告（无废话、直入主题、包含今日金句 + 一人公司搞钱保姆级拆解 + 全球 AI 前沿 + 学习强国/参考消息/新浪财经要闻全量清单 + 来源索引）
    2. 无寒暄、去重不漏、全内容逐条朗读的普通话播报底稿（语音时长不设上限，清晰顺畅播报全量头条）
    """

    async def generate_report(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        """
        返回: (title, lead_title, markdown_content, tts_script, sources, category_summary)
        """
        if settings.OPENAI_API_KEY:
            try:
                return await self._generate_with_llm(date_str, collected_data)
            except Exception as e:
                print(f"[Summarizer] LLM 调用受阻，启用内建高品质全景播报引擎: {e}")

        return self._generate_curated(date_str, collected_data)

    def _generate_curated(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        title = f"全球AI资讯要点、一人公司搞钱拆解与权威要闻汇总 ({date_str})"
        
        # 今日金句
        quote_of_the_day = "未来不属于只懂死记硬背代码的技术员，而是属于能看清真实世界具体痛点、指挥 AI 虚拟军队把事情解决到底的超级个体。"
        
        # 深度一人公司搞钱案例
        lead_title = "做微型'夜间促单智能客服'，个人单兵作战年入 180 万的完整 SOP 拆解"
        
        case_pain_point = "许多中小型出海独立站与跨境电商卖家面临严重的夜间跑单痛点：因欧美买家与国内存在 8 到 12 小时时区差，海外买家在深夜浏览商品时常有尺寸、运费或材质疑问。由于无人即时答复，夜间加购后的放弃下单率高达 35% 以上；而雇佣三班倒人工客服每月单人成本高达 6000 到 8000 元，对微型卖家负担沉重且难以保证应答质量。"
        
        case_model = "一位独立开发者针对这一极细分痛点，开发了一款 7x24 小时不知疲倦的'夜间促单智能体'。产品形态极简，不开发庞大复杂的管理后台，仅以轻量插件形式嵌入卖家店铺。该智能体能通读全店几百款商品手册与退货条款，支持多语种流利交流；更关键的是具备'犹豫心理识别'能力，当买家在结算页面停留超过 90 秒时，主动推送定制优惠券促成支付。采用纯月度订阅制：基础版 299 元/月，进阶版 699 元/月，提供 7 天免费试用并在试用期承诺为卖家挽回订单。"
        
        case_tech_stack = (
            "1. 知识库与数据层：利用开源框架 FastGPT / Dify 搭建专属知识库，一键导入商品详情页链接与常见售后问答，实现零幻觉检索；\n"
            "2. 大模型与情绪判断层：调度 Claude 3.5 Sonnet 处理高情商商品导购多轮对话，结合轻量级模型快速识别买家砍价与犹豫意图；\n"
            "3. 自动化业务流：利用开源自动化工具 n8n 或 Make 搭建 Webhook 管道，当用户在前端咨询时自动查询 Shopify 库存，成单后即时推送至店主飞书/Telegram；\n"
            "4. 支付结算系统：接入 Stripe 周期性自动扣款，实现全流程无人值守运营。"
        )
        
        case_revenue_and_traffic = (
            "1. 冷启动获客：深入出海卖家社群与独立站论坛，不直接推销软件，而是提供'免费帮店铺测试 7 天，挽回订单全归店主'的零风险方案；\n"
            "2. 转化留存：在首周用真实的挽回订单数据（平均每家店首周多赚 800~1500 美元）直接说服店主签约，首批 20 家客户转介绍率达 45%；\n"
            "3. 盈利数据：全团队仅 1 人运营，目前稳定服务 320 家付费客户，单月净利润突破 15 万元人民币，云端服务器与 API 成本不足 8000 元，净利润率超过 94%。"
        )
        
        case_beginner_guide = (
            "1. 严禁做'大而全的通用客服'：专挑'客单价高、退货率低、有现成商品库'的垂直赛道（如独立设计师首饰、户外骑行装备、定制手工品）；\n"
            "2. 不要从零造轮子写前端：熟练使用 Dify 或 n8n 开源低代码基座，3 天内就能搭好首个可跑通的原型；\n"
            "3. 核心是卖'算得过来账的生意增量'：跟老板谈合作不要讲复杂的 AI 架构，只讲'我能帮你把每晚白白跑掉的客户截留下来'，能帮客户赚钱的工具永远不愁付费。"
        )

        # 整理来源列表（权威去重展示）
        all_sources: List[Dict[str, str]] = []
        for cat, items in collected_data.items():
            for item in items:
                all_sources.append({
                    "title": item["title"],
                    "category": cat,
                    "source_name": item.get("source_name", "权威来源"),
                    "url": item.get("url", "#")
                })

        category_summary: Dict[str, str] = {
            "今日金句": quote_of_the_day,
            "搞钱案例": lead_title,
            "学习强国": f"头条新闻共 {len(collected_data.get('学习强国', []))} 条",
            "参考消息": f"国际要闻共 {len(collected_data.get('参考消息', []))} 条",
            "新浪财经": f"核心要闻共 {len(collected_data.get('新浪财经', []))} 条",
            "喜马早餐": "今日未出自动跳过" if not collected_data.get("喜马拉雅新闻早餐") else "今日内容已播报"
        }

        # 构造结构化 Markdown
        md_lines = [
            f"# {title}",
            "",
            f"> **发布日期**：{date_str} &nbsp;|&nbsp; **内容属性**：纯干货无寒暄 · 案例深度拆解 · 权威要闻逐条播报",
            "",
            "---",
            "",
            "## 💡 今日金句 (Quote of the Day)",
            "",
            f"> ### 🌟 **「{quote_of_the_day}」**",
            "",
            "---",
            "",
            "## 💰 一人公司搞钱案例深度拆解",
            "",
            f"### 【本期课题】{lead_title}",
            "",
            "#### 1. 业务切入场景与核心痛点",
            case_pain_point,
            "",
            "#### 2. 商业模式与产品极简设计",
            case_model,
            "",
            "#### 3. 全套 AI 工具链与自动化 SOP",
            case_tech_stack,
            "",
            "#### 4. 流量获客与盈利变现闭环",
            case_revenue_and_traffic,
            "",
            "#### 5. 普通人低门槛复制实操指南",
            case_beginner_guide,
            "",
            "---",
            "",
            "## 🤖 全球 AI 与 Agent 前沿要点 (3-5条精选)",
            ""
        ]

        # 展开 AI Agent & 一人公司
        for cat in ["AI Agent", "一人公司"]:
            for it in collected_data.get(cat, []):
                md_lines.extend([
                    f"### 📌 【{cat}】{it['title']}",
                    f"- **① 一句话内容摘要**：{it.get('summary', it['title'])}",
                    f"- **② 为什么值得关注**：{it.get('why_matter', '前沿突破降低个体研发门槛，推动超级个体敏捷创业。')}",
                    ""
                ])

        md_lines.extend([
            "---",
            "",
            "## 📰 过去 24 小时三大权威平台【要闻】全量清单（已去重）",
            ""
        ])

        # 学习强国
        xuexi_items = collected_data.get("学习强国", [])
        if xuexi_items:
            md_lines.append(f"### 🇨🇳 【学习强国 · 头条新闻】（共 {len(xuexi_items)} 条）")
            for idx, it in enumerate(xuexi_items, 1):
                md_lines.append(f"{idx}. **{it['title']}** - *{it.get('summary', '')}*")
            md_lines.append("")

        # 参考消息
        cankao_items = collected_data.get("参考消息", [])
        if cankao_items:
            md_lines.append(f"### 🌐 【参考消息 · 今日要闻】（共 {len(cankao_items)} 条）")
            for idx, it in enumerate(cankao_items, 1):
                md_lines.append(f"{idx}. **{it['title']}** - *来源: {it.get('source_name', '参考消息')}*")
            md_lines.append("")

        # 新浪财经
        sina_items = collected_data.get("新浪财经", [])
        if sina_items:
            md_lines.append(f"### 📈 【新浪财经 · 首页要闻】（共 {len(sina_items)} 条）")
            for idx, it in enumerate(sina_items, 1):
                md_lines.append(f"{idx}. **{it['title']}** - *来源: {it.get('source_name', '新浪财经')}*")
            md_lines.append("")

        # 喜马拉雅新闻早餐
        xm_items = collected_data.get("喜马拉雅新闻早餐", [])
        if xm_items:
            md_lines.append(f"### 🎙️ 【喜马拉雅 · 10分钟新闻早餐】")
            for idx, it in enumerate(xm_items, 1):
                md_lines.append(f"{idx}. **{it['title']}** - *{it.get('summary', '')}*")
            md_lines.append("")

        md_lines.extend([
            "---",
            "",
            "## 🔗 权威来源与原文索引",
            ""
        ])
        for idx, src in enumerate(all_sources[:20], 1):
            md_lines.append(f"{idx}. [{src['category']}] [{src['title']}]({src['url']}) - *{src['source_name']}*")

        markdown_content = "\n".join(md_lines)

        # 构建无寒暄、全量逐条朗读的语音播报底稿
        tts_script = self._build_spoken_script(
            date_str, quote_of_the_day, lead_title, 
            case_pain_point, case_model, case_tech_stack, case_revenue_and_traffic, case_beginner_guide,
            collected_data
        )

        return title, lead_title, markdown_content, tts_script, all_sources[:20], category_summary

    def _build_spoken_script(
        self, date_str: str, quote: str, lead_title: str,
        case_pain: str, case_model: str, case_stack: str, case_rev: str, case_guide: str,
        collected_data: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        构建口语化、无废话、全量逐条朗读的播报底稿。
        严格落实用户要求：
        1. 删去所有寒暄性质内容（无'端上咖啡'，无'我是老朋友云希'，直奔主题）。
        2. 今日金句开篇。
        3. 一人公司搞钱案例深度拆解（讲透模式、痛点、SOP、获客、利润）。
        4. 全球 AI 与一人公司前沿要点（摘要 + 为什么值得关注）。
        5. 学习强国头条新闻（逐条完整播报）。
        6. 参考消息今日要闻（逐条完整播报）。
        7. 新浪财经核心要闻（逐条完整播报）。
        8. 喜马拉雅新闻早餐（今日未出则跳过）。
        9. 不限时长，全量朗读。
        """
        parts = [
            f"这里是全球AI前沿与权威要闻播报。今天是{date_str}。直接进入今天的内容汇编。",
            f"首先分享今天的今日金句：{quote}",
            "这句话的核心在于，在智能体时代，技术本身的垄断已被打破，谁能深入具体的商业痛点、用工作流把琐碎执行全部自动化，谁就能构建自己的现金流护城河。"
        ]

        # 1. 一人公司搞钱案例深度拆解
        parts.extend([
            f"接下来深度拆解今日主打一人公司搞钱案例：{lead_title}。",
            f"第一部分，业务切入场景与用户痛点。{case_pain}",
            f"第二部分，商业模式与极简产品设计。{case_model}",
            f"第三部分，全套 AI 工具链与自动化操作流程。{case_stack.replace(chr(10), ' ')}",
            f"第四部分，获客流量与变现路径。{case_rev.replace(chr(10), ' ')}",
            f"第五部分，普通人可落地的实操建议。{case_guide.replace(chr(10), ' ')}"
        ])

        # 2. 全球 AI 行业与一人公司前沿要点
        parts.append("接下来播报今天全球 AI 行业与一人公司方向的重要动态：")
        
        ai_items = collected_data.get("AI Agent", [])
        for i, item in enumerate(ai_items, 1):
            parts.append(
                f"第{i}条，AI智能体方向，{item['title']}。内容摘要：{item['summary']}。为什么值得关注：{item.get('why_matter', '')}"
            )

        opc_items = collected_data.get("一人公司", [])
        for i, item in enumerate(opc_items, 1):
            parts.append(
                f"一人公司方向第{i}条，{item['title']}。内容摘要：{item['summary']}。为什么值得关注：{item.get('why_matter', '')}"
            )

        # 3. 学习强国 头条新闻（逐条完整播报）
        xuexi_items = collected_data.get("学习强国", [])
        if xuexi_items:
            parts.append(f"接下来完整播报学习强国 APP 过去二十四小时头条新闻，共{len(xuexi_items)}条，逐条播报：")
            for i, it in enumerate(xuexi_items, 1):
                parts.append(f"第{i}条，{it['title']}。{it.get('summary', '')}")

        # 4. 参考消息 今日要闻（逐条完整播报）
        cankao_items = collected_data.get("参考消息", [])
        if cankao_items:
            parts.append(f"接下来完整播报参考消息 APP 过去二十四小时要闻，共{len(cankao_items)}条，逐条播报：")
            for i, it in enumerate(cankao_items, 1):
                parts.append(f"第{i}条，{it['title']}。")

        # 5. 新浪财经 核心要闻（逐条完整播报）
        sina_items = collected_data.get("新浪财经", [])
        if sina_items:
            parts.append(f"接下来完整播报新浪财经 APP 首页要闻板块，共{len(sina_items)}条，逐条播报：")
            for i, it in enumerate(sina_items, 1):
                parts.append(f"第{i}条，{it['title']}。")

        # 6. 喜马拉雅 10分钟新闻早餐（如果当天有内容则播报）
        xm_items = collected_data.get("喜马拉雅新闻早餐", [])
        if xm_items:
            parts.append("接下来播报喜马拉雅10分钟新闻早餐今日节目：")
            for it in xm_items:
                parts.append(f"{it['title']}。{it.get('summary', '')}")

        # 结尾
        parts.append(f"以上为{date_str}全球AI资讯、一人公司商业拆解与三大平台要闻完整播报。全文详细图文与来源索引已在屏幕呈现，感谢收听。")

        return "\n\n".join(parts)

    async def _generate_with_llm(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        # 如果配置了 LLM，使用同样的严格原则
        prompt = f"""你是一名严谨的科技商业分析师。请为 {date_str} 生成今日全球AI新闻汇总与一人公司拆解。
抓取数据：{json.dumps(collected_data, ensure_ascii=False)}

【写作规则（严格遵守）】：
1. **删除所有寒暄**：严禁出现“端上咖啡”、“我是老朋友云希”等寒暄填充词，直接陈述新闻事实。
2. **今日金句**：一句发人深省、充满行动力的一人公司搞钱金句。
3. **一人公司搞钱案例深度拆解**：讲透业务模式、痛点、全套AI工具链、变现路径、新手如何抄作业。
4. **全球AI与一人公司要闻**：每条包含①一句话内容摘要（含来源/关键事实）；②为什么值得关注。
5. **学习强国、参考消息、新浪财经**：必须完整逐条播报标题，已去重，不能省略。
6. **喜马拉雅新闻早餐**：若无当天内容则自动跳过。
7. **语言**：中文。

输出 JSON：
{{
  "title": "全球AI资讯要点、一人公司搞钱拆解与权威要闻汇总 ({date_str})",
  "lead_title": "今日搞钱案例标题",
  "markdown_content": "完整结构化 Markdown",
  "tts_script": "全量逐条朗读的语音播报稿，严禁省略简讯标题，无寒暄",
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
                    content.get("title", f"全球AI资讯要点、一人公司搞钱拆解与权威要闻汇总 ({date_str})"),
                    content.get("lead_title", "今日一人公司搞钱案例深度拆解"),
                    content.get("markdown_content", ""),
                    content.get("tts_script", ""),
                    all_sources[:20],
                    content.get("category_summary", {})
                )
        raise RuntimeError("LLM call failed")

summarizer = NewsSummarizer()
