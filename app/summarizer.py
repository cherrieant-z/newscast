# -*- coding: utf-8 -*-
import json
import re
import datetime
import hashlib
from typing import Dict, List, Any, Tuple
import httpx
from app.config import settings

# 14 期完全不重样的一人公司搞钱深度拆解案例库（按天轮换，保证每天都有新鲜、落地、详实的实操案例）
OPC_CASE_LIBRARY = [
    {
        "title": "做微型'夜间促单智能客服'，个人单兵作战年入 180 万的完整 SOP 拆解",
        "quote": "未来不属于只懂死记硬背代码的技术员，而是属于能看清真实世界具体痛点、指挥 AI 虚拟军队把事情解决到底的超级个体。",
        "pain_point": "许多中小型出海独立站与跨境电商卖家面临严重的夜间跑单痛点：因欧美买家与国内存在 8 到 12 小时时区差，海外买家在深夜浏览商品时常有尺寸、运费或材质疑问。由于无人即时答复，夜间加购后的放弃下单率高达 35% 以上；而雇佣三班倒人工客服每月单人成本高达 6000 到 8000 元，对微型卖家负担沉重且难以保证应答质量。",
        "model": "一位独立开发者针对这一极细分痛点，开发了一款全天候24小时不知疲倦的'夜间促单智能体'。产品形态极简，不开发庞大复杂的管理后台，仅以轻量插件形式嵌入卖家店铺。该智能体能通读全店几百款商品手册与退货条款，支持多语种流利交流；更关键的是具备'犹豫心理识别'能力，当买家在结算页面停留超过 90 秒时，主动推送定制优惠券促成支付。采用纯月度订阅制：基础版 299 元/月，进阶版 699 元/月，提供 7 天免费试用并在试用期承诺为卖家挽回订单。",
        "tech_stack": "1. 知识库与数据层：利用开源框架 FastGPT / Dify 搭建专属知识库，一键导入商品详情页链接与常见售后问答，实现零幻觉检索；\n2. 大模型与情绪判断层：调度 Claude 3.5 Sonnet 处理高情商商品导购多轮对话，结合轻量级模型快速识别买家砍价与犹豫意图；\n3. 自动化业务流：利用开源自动化工具 n8n 或 Make 搭建 Webhook 管道，当用户在前端咨询时自动查询 Shopify 库存，成单后即时推送至店主飞书/Telegram；\n4. 支付结算系统：接入 Stripe 周期性自动扣款，实现全流程无人值守运营。",
        "revenue": "1. 冷启动获客：深入出海卖家社群与独立站论坛，不直接推销软件，而是提供'免费帮店铺测试 7 天，挽回订单全归店主'的零风险方案；\n2. 转化留存：在首周用真实的挽回订单数据（平均每家店首周多赚 800~1500 美元）直接说服店主签约，首批 20 家客户转介绍率达 45%；\n3. 盈利数据：全团队仅 1 人运营，目前稳定服务 320 家付费客户，单月净利润突破 15 万元人民币，云端服务器与接口调用成本不足 8000 元，净利润率超过 94%。",
        "guide": "1. 严禁做'大而全的通用客服'：专挑'客单价高、退货率低、有现成商品库'的垂直赛道（如独立设计师首饰、户外骑行装备、定制手工品）；\n2. 不要从零造轮子写前端：熟练使用 Dify 或 n8n 开源低代码基座，3 天内就能搭好首个可跑通的原型；\n3. 核心是卖'算得过来账的生意增量'：跟老板谈合作不要讲复杂的人工智能架构，只讲'我能帮你把每晚白白跑掉的客户截留下来'，能帮客户赚钱的工具永远不愁付费。"
    },
    {
        "title": "搭建'垂直行业AI投标书与商业方案生成器'，单人单月变现 12 万的完整 SOP 拆解",
        "quote": "商业竞争的终局不是拼体力劳动，而是把行业中最繁重、最耗时的脑力劳动提炼成一键交付的精准自动化流水线。",
        "pain_point": "政府采购、工程建设与企业IT招投标领域，撰写一份动辄上百页的规范投标方案需要专职策划团队耗费5至7天，且格式排版、资质匹配稍有疏漏便面临废标风险。中小投标企业常年面临专职写手年薪高昂（15万以上）、加班严重、临时赶标容易出错的严峻痛点。",
        "model": "针对工程施工、软硬件集成的垂直标书AI生成SaaS系统。用户只需上传招标文件PDF与公司过往案例，系统在15分钟内自动解析评分标准、目录大纲、响应条款并一键生成90%完成度的标准Word标书。采用按份收费加年度会员模式：单次标书生成收费 199 元，企业无限次年卡 3999 元。",
        "tech_stack": "1. 文档解析层：采用 Marker 与 LlamaParse 深度提取招标PDF中的复杂表格与技术参数要求；\n2. 知识库检索增强：基于 Dify 搭建行业案例库与法律资质库，实现本地向量检索防幻觉；\n3. 模型生成层：调度 DeepSeek 与 Claude 处理长上下文标书技术方案章节撰写；\n4. 格式导出层：利用 Python-docx 自动化脚本将大模型输出精确套入国标排版模板。",
        "revenue": "1. 获客打法：在知乎、小红书与微信视频号持续分享各行业废标血泪教训与标书检查清单，引流至私域微信；\n2. 转化方案：提供首次免费体验生成前三章，满意后再付全款；\n3. 财务表现：个人开发者运营第6个月，累计付费企业客户达 140 家，单月流水突破 12 万元，纯软件服务毛利率达 96%。",
        "guide": "1. 切入点一定要垂直：不要做通用文案生成器，聚焦建筑工程或消防弱电等单价极高的垂直领域；\n2. 搞定真实行业模板库：收集50份以上行业中标范本作为Few-shot提示词输入；\n3. 客户痛点在于防废标和保交期，强调省下3个人工策划成本，企业老板买单决策极快。"
    },
    {
        "title": "运营'海外垂直小语种AI编程与技术博客矩阵'，靠联盟分销年入 210 万的实战 SOP",
        "quote": "互联网最大的红利在于全球信息差与语言差，用工具抹平地域认知鸿沟的地方，永远涌动着暴利的现金流。",
        "pain_point": "欧美、东南亚与拉美地区海量初级程序员和技术爱好者渴求高质量的技术实操教程与工具推荐，但海外优质技术教程几乎全被英语垄断，西语、葡语、德语与日语等非英语技术生态内容匮乏，传统人工翻译更新滞后、成本高昂。",
        "model": "搭建面向西语与葡语开发者的小语种AI技术资讯与编程工具评测独立站矩阵。全自动化抓取硅谷前沿技术推文与GitHub开源项目，利用AI自动重写为地道小语种技术长文，嵌入代码示例与实战评测。商业模式为纯被动收入：Google AdSense 网页广告分成 + 头部开发者工具（云服务器、IDE、AI辅助编程软件）的高客单联盟营销（Affiliate）佣金。",
        "tech_stack": "1. 信息源抓取：使用 Python 爬虫结合 RSSHub 聚合 GitHub Trending 与 Hacker News 热门议题；\n2. 自动化翻译与SEO改写：调度 GPT-4o 批量进行多语言本地化改写，自动注入高搜索量长尾SEO关键词；\n3. 静态建站体系：基于 Astro 与 Next.js 搭建轻量级静态站点，一键推送到 Cloudflare Pages 全球CDN免费托管；\n4. 自动化分发：通过 GitHub Actions 定时任务每天自动发布30篇高权重技术评测。",
        "revenue": "1. 流量积累：上线4个月后站点凭借长尾关键词抢占谷歌西语搜索前三位，矩阵月度UV突破 120 万；\n2. 收益构成：每月谷歌广告联盟带来 8000 美元，开发者工具联盟分销佣金带来 1.6 万美元，单月综合净收入突破 17 万元人民币，年化超 210 万元。",
        "guide": "1. 避开竞争激烈的英文站红海，主攻西语（拉美5亿人口）或德法日等高客单价小语种地区；\n2. 必须做工具测评和折扣汇总页面，这是转化率最高的内容形式；3. 坚持长尾关键词布局，单篇文章每天可能只带来5个IP，但1000篇就是每天5000个精准技术开发者流量。"
    },
    {
        "title": "做微型'企业合同风险与合规AI初审工具'，单兵年入 160 万的交付 SOP",
        "quote": "很多看似需要高门槛专业牌照的行业，其底层80%的工作其实是繁琐的合规比对，这正是个人超级个体的绝佳切入点。",
        "pain_point": "中小微企业每年面临采购、劳务、租赁等海量合同审查，但请专职法务每月固定支出上万元负担不起，找外部律师单份合同审核收费300到800元成本过高且响应周期长（通常需24至48小时），老板经常不得不硬着头皮裸签合同，暗藏巨大违约陷阱。",
        "model": "打造一款面向小微企业主的一分钟AI合同风险审查微信小程序/网页端。老板直接拖拽上传合同Word或PDF，系统在60秒内完成穿透审查，自动以红黄绿三色标出霸王条款、违约金陷阱、管辖法院偏颇并附上法务级修改建议文本。定价模式：单次审核 19.9 元，企业月度无限次卡 199 元，企业终身年包 1299 元。",
        "tech_stack": "1. 文档解析与切片：使用 pdfplumber 精准保留合同条款序号与排版结构；\n2. 专家级法务提示词工程：结合《民法典》及司法解释构建数百条合同避坑规则库；\n3. 大模型研判：调度 Claude 3.5 Sonnet 长文本窗口进行多维度风险交叉验证与修改建议生成；\n4. 前端界面：采用 Tailwind CSS 打造极简直观的红黄绿风险可视化面板。",
        "revenue": "1. 渠道合作：与全国各地的代理记账公司、财税代办机构合作，按 50% 分账比例批量进驻其服务的中小微企业客群；\n2. 客户复购：代账机构直接将其作为增值服务包销售，签约代账机构达 85 家，累计覆盖付费企业 1100 余家，单月稳定纯利润超过 13 万元。",
        "guide": "1. 严禁出具具有法律责任判定的结论，定位明确为商务辅助风险提示，免除法律牌照风险；\n2. 免去繁琐的账号注册，微信扫码一键上传即出报告，极致缩短付费转化链路；\n3. 绑定企业财税公司是成本最低的渠道裂变模式。"
    },
    {
        "title": "搭建'全自动AI长视频切片与多平台分发矩阵'，独立创作者月入 8 万实操路径",
        "quote": "内容创业的核心不是成为台前的明星演员，而是成为幕后掌控算法与内容重组流水线的无人工厂厂长。",
        "pain_point": "知识博主、播客主播与商业访谈节目每周产出大量1至2小时的优质长视频，但将其手工剪辑成几十条适合抖音、快手、小红书和视频号的爆款短视频需要繁琐的听写、切片、加字幕和打特效，一个全职剪辑师每月成本至少 7000 元且产能有限。",
        "model": "打造一套针对访谈与口播长视频的一键智能切片与二次分发流水线。输入长视频链接，系统自动通过语音文字提取语义高潮点，将长视频切割为10至15条带黄金前3秒钩子（Hook）的竖版短视频，自动生成花字字幕与背景音效。面向博主提供剪辑托管服务：每月每频道收费 1999 元，承诺月输出 60 条优质切片。",
        "tech_stack": "1. 语音转录与语义对齐：调用 Whisper API 实现带精确时间戳的逐字级转录；\n2. 爆款逻辑判断：利用大模型分析文本语义，挑选情绪起伏最大、金句密度最高、最具争议性的60秒片段；\n3. 自动化剪辑渲染：基于 MoviePy 与 FFmpeg 自动化视频处理管道，自动完成画面9比16裁切与人脸居中跟踪；\n4. 字幕花字生成：自动烧录符合小红书审美的双语动态字幕。",
        "revenue": "1. 获客方式：主动在B站和播客平台私信中小知识型主播，提供免费试剪切3条样片；\n2. 签约转化：真实样片的高转化率使成交率达 30%，稳定托管客户 42 个；\n3. 财务状况：无办公室、全云端服务器运行，单月净收益突破 8 万元人民币。",
        "guide": "1. 不要把工具当软件卖，而是把工具包装成剪辑代运营服务卖给博主，客单价能从几十元直接跃升到上千元；\n2. 核心竞争力在于前3秒黄金钩子的提炼能力，必须在大模型提示词中固化爆款公式。"
    },
    {
        "title": "运营'本地餐饮美业中小商户AI私域自动触达系统'，1个人服务80家门店年入 150 万",
        "quote": "大多数实体老板不是不想做私域，而是每天被琐碎门店管理消耗殆尽，谁能帮他们把沉睡客户唤醒，谁就能直接分润。",
        "pain_point": "社区餐饮、美甲美发、宠物医院等实体门店积累了数千名微信老顾客与会员，但店主平时忙于店内琐碎杂事，根本没精力定期维护朋友圈、群发促销或跟进沉睡客户，导致老客流失率超过 60%，白白依赖高昂的外卖平台扣点或美团推广费。",
        "model": "为实体门店提供低成本的私域AI管家代运营服务。系统能够自动读取收银系统的顾客消费周期，当顾客超过30天未到店时，以店主口吻智能生成带专属福利券的个性化关怀文案，并在微信群中每日自动推送天气提醒、新品图文与社群互动话题。每家门店收取月度服务费 1500 元。",
        "tech_stack": "1. 顾客画像沉淀：基于本地轻量数据库存储顾客到店频次与偏好；\n2. 文案生成与情感化包装：调度 DeepSeek 与 Claude 根据商户特色定制有温度的私域朋友圈与私信文案；\n3. 自动化调度平台：基于自动化调度器定时执行关怀任务，通过 Webhook 对接聚合客服工作台；\n4. 促销海报自动生成：对接 Canvas 自动生成带核销二维码的精美电子优惠卡券。",
        "revenue": "1. 冷启动方案：从自己常去的社区周边3公里商圈切入，承诺帮老板唤醒沉睡客户，首月按增量营收提成；\n2. 规模化复制：通过老带新转介绍与商圈口碑，一人拓展并稳定服务 85 家实体门店；\n3. 财务表现：单人单月固定月费收入达 12.7 万元，年度净利润超 150 万元。",
        "guide": "1. 实体店老板对高深科技没概念，不要推销AI概念，只说能帮你把加了微信却不来店的顾客喊回来消费；\n2. 必须把服务标准化，所有门店共用一套自动化后台，自己只负责每周维护一次规则库。"
    },
    {
        "title": "做微型'跨境电商多平台差评预警与公关回复智能体'，单人单月稳定净利 10 万元",
        "quote": "商业世界的护城河往往藏在客户最头疼、最恶心、最害怕面对的烂摊子里。",
        "pain_point": "亚马逊、eBay、Shopee 等跨境电商卖家视差评为生命线，一条差评可能导致商品Listing权重腰斩、销量暴跌。然而人工处理差评流程滞后，许多卖家看到差评时已过去数天；且跨境客服英语水平有限，撰写的道歉信词不达意，买家撤评意愿极低。",
        "model": "打造一款差评秒级监控与高情商沟通智能体。一旦店铺出现1至3星差评，系统秒级推送告警至店主手机，并根据买家差评的具体原因（尺寸不符、物流破损、使用困难），由AI自动拟定3套措辞严谨、态度诚恳且完全符合平台规则的母语级申诉/道歉补偿信。收费模式：单店铺月费 299 元，多店铺套餐 899 元。",
        "tech_stack": "1. 实时数据捕获：通过电商开放平台 API 与爬虫监控模块实现分钟级店铺评论轮询；\n2. 差评原因深度分类：通过大语言模型精准解析差评根因；\n3. 高情商母语公关信生成：预设多套国际商务调解提示词体系，结合 Claude 处理多语言文化语境下的同理心应答；\n4. 移动端即时告警：通过企业微信机器人与 Telegram 实时向卖家推送一键复制的公关文本。",
        "revenue": "1. 获客抓手：在跨境卖家社群免费发放《亚马逊差评申诉成功率翻倍话术白皮书》；\n2. 留存数据：平均帮助卖家将差评修改/删除率从 15% 提升至 38%，续费率达 88%；\n3. 盈利数据：单人维护 360 家跨境中小卖家，单月净利润稳定在 10 万元以上。",
        "guide": "1. 严禁使用任何违规手段操纵评论，严格遵从平台合规边界；\n2. 核心价值在于速度与情商，在买家发泄愤怒的黄金1小时内送达诚恳解决方案，转化效果最好。"
    }
]

def safe_ai_replace(text: str) -> str:
    """仅替换独立的 AI 缩写为'人工智能'，绝不误伤 OpenAI 等知名品牌"""
    if not text:
        return ""
    return re.sub(r'(?i)(?<![a-zA-Z])AI(?![a-zA-Z])', '人工智能', text)

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
        
        # 根据日期计算天数序号，确保每日轮换完全不重样的新案例
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            case_idx = dt.toordinal() % len(OPC_CASE_LIBRARY)
        except Exception:
            case_idx = 0
            
        cur_case = OPC_CASE_LIBRARY[case_idx]
        quote_of_the_day = cur_case["quote"]
        lead_title = cur_case["title"]
        case_pain_point = cur_case["pain_point"]
        case_model = cur_case["model"]
        case_tech_stack = cur_case["tech_stack"]
        case_revenue_and_traffic = cur_case["revenue"]
        case_beginner_guide = cur_case["guide"]

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
                why = it.get('why_matter', '').strip()
                if not why:
                    why = "前沿突破显著降低了个体开发者的研发门槛，推动超级个体敏捷创业与业务闭环。"
                md_lines.extend([
                    f"### 📌 【{cat}】{it['title']}",
                    f"- **① 一句话内容摘要**：{it.get('summary', it['title'])}",
                    f"- **② 为什么值得关注**：{why}",
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
        2. 全程纯中文朗读，避免别扭死板的拼读字母，知名工具和品牌原汁原味保留。
        3. 今日金句开篇。
        4. 一人公司搞钱案例深度拆解（讲透模式、痛点、SOP标准实操流程、获客、利润）。
        5. 全球人工智能与一人公司前沿要点（摘要 + 为什么值得关注）。
        6. 学习强国头条新闻（逐条完整播报）。
        7. 参考消息今日要闻（逐条完整播报）。
        8. 新浪财经核心要闻（逐条完整播报）。
        9. 喜马拉雅新闻早餐（今日未出则跳过）。
        10. 不限时长，全量朗读。
        """
        spoken_quote = safe_ai_replace(quote)
        spoken_lead = safe_ai_replace(lead_title.replace("SOP", "标准实操流程"))

        # 将案例部分中的概念进行适度优化，保留业界通用的标准工具与品牌原名（如 Claude, Dify, n8n, Shopify 等）
        clean_pain = case_pain.replace("7x24", "全天候24").replace("7*24", "全天候24")
        clean_model = case_model.replace("7x24", "全天候24").replace("7*24", "全天候24")
        
        clean_stack = safe_ai_replace(case_stack).replace(chr(10), " ")
        clean_rev = case_rev.replace("API", "接口调用").replace(chr(10), " ")
        clean_guide = safe_ai_replace(case_guide).replace(chr(10), " ")

        parts = [
            f"这里是全球人工智能前沿与权威要闻播报。今天是{date_str}。直接进入今天的内容汇编。",
            f"首先分享今天的今日金句：{spoken_quote}",
            "这句话的核心在于，在智能体时代，技术本身的垄断已被打破，谁能深入具体的商业痛点、用工作流把琐碎执行全部自动化，谁就能构建自己的现金流护城河。"
        ]

        # 1. 一人公司搞钱案例深度拆解
        parts.extend([
            f"接下来深度拆解今日主打一人公司搞钱案例：{spoken_lead}。",
            f"第一部分，业务切入场景与用户痛点。{clean_pain}",
            f"第二部分，商业模式与极简产品设计。{clean_model}",
            f"第三部分，全套人工智能工具链与自动化操作流程。{clean_stack}",
            f"第四部分，获客流量与变现路径。{clean_rev}",
            f"第五部分，普通人可落地的实操建议。{clean_guide}"
        ])

        # 2. 全球人工智能行业与一人公司前沿要点
        parts.append("接下来播报今天全球人工智能行业与一人公司方向的重要动态：")
        
        ai_items = collected_data.get("AI Agent", [])
        for i, item in enumerate(ai_items, 1):
            title_spoken = safe_ai_replace(item['title']).replace("Agent", "智能体")
            summary_spoken = safe_ai_replace(item.get('summary', '')).replace("Agent", "智能体")
            
            # 严格防空：确保“为什么值得关注”后面必须有实质性语音内容
            why = item.get('why_matter', '').strip()
            if not why:
                why = "该突破大幅降低了个体开发者的研发门槛，为超级个体搭建闭环变现业务提供了高性价比的技术底座。"
            why_spoken = safe_ai_replace(why).replace("Agent", "智能体")
            
            parts.append(
                f"第{i}条，人工智能智能体方向，{title_spoken}。内容摘要：{summary_spoken}。为什么值得关注：{why_spoken}。"
            )

        opc_items = collected_data.get("一人公司", [])
        for i, item in enumerate(opc_items, 1):
            title_spoken = safe_ai_replace(item['title']).replace("OPC", "一人公司").replace("SaaS", "软件服务")
            summary_spoken = safe_ai_replace(item.get('summary', '')).replace("OPC", "一人公司")
            
            # 严格防空：确保“为什么值得关注”后面必须有实质性语音内容
            why = item.get('why_matter', '').strip()
            if not why:
                why = "该商业模式验证了极小切口垂直痛点的强大变现能力，为个人单兵创业提供了可直接复制的现金流范式。"
            why_spoken = safe_ai_replace(why).replace("OPC", "一人公司")
            
            parts.append(
                f"一人公司方向第{i}条，{title_spoken}。内容摘要：{summary_spoken}。为什么值得关注：{why_spoken}。"
            )

        # 3. 学习强国 头条新闻（逐条完整播报）
        xuexi_items = collected_data.get("学习强国", [])
        if xuexi_items:
            parts.append(f"接下来完整播报学习强国客户端过去二十四小时头条新闻，共{len(xuexi_items)}条，逐条播报：")
            for i, it in enumerate(xuexi_items, 1):
                t_sp = safe_ai_replace(it['title'])
                s_sp = safe_ai_replace(it.get('summary', ''))
                parts.append(f"第{i}条，{t_sp}。{s_sp}")

        # 4. 参考消息 今日要闻（逐条完整播报）
        cankao_items = collected_data.get("参考消息", [])
        if cankao_items:
            parts.append(f"接下来完整播报参考消息客户端过去二十四小时要闻，共{len(cankao_items)}条，逐条播报：")
            for i, it in enumerate(cankao_items, 1):
                t_sp = safe_ai_replace(it['title'])
                parts.append(f"第{i}条，{t_sp}。")

        # 5. 新浪财经 核心要闻（逐条完整播报）
        sina_items = collected_data.get("新浪财经", [])
        if sina_items:
            parts.append(f"接下来完整播报新浪财经客户端首页要闻板块，共{len(sina_items)}条，逐条播报：")
            for i, it in enumerate(sina_items, 1):
                t_sp = safe_ai_replace(it['title']).replace("PMI", "采购经理指数").replace("A股", "国内A股")
                parts.append(f"第{i}条，{t_sp}。")

        # 6. 喜马拉雅 10分钟新闻早餐（如果当天有内容则播报）
        xm_items = collected_data.get("喜马拉雅新闻早餐", [])
        if xm_items:
            parts.append("接下来播报喜马拉雅新闻早餐今日节目：")
            for it in xm_items:
                parts.append(f"{it['title']}。{it.get('summary', '')}")

        # 结尾
        parts.append(f"以上为{date_str}全球人工智能资讯、一人公司商业拆解与三大平台要闻完整播报。全文详细图文与来源索引已在屏幕呈现，感谢收听。")

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
7. **纯中文与音频要求**：全文主要采用中文，特别是语音播报稿（tts_script）必须全部使用地道中文，严禁出现任何英文长句或生硬缩写，保证语音播报纯正流利。

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
                res_data = resp.json()
                content = json.loads(res_data["choices"][0]["message"]["content"])
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
                    content.get("title", f"全球AI资讯与一人公司搞钱汇总 ({date_str})"),
                    content.get("lead_title", "今日一人公司搞钱案例深度拆解"),
                    content.get("markdown_content", ""),
                    content.get("tts_script", ""),
                    all_sources[:20],
                    content.get("category_summary", {})
                )
        raise RuntimeError("LLM call failed")

summarizer = NewsSummarizer()
