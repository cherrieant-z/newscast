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


def _cue_hit(text: str, kw: str) -> bool:
    """关键词命中：纯字母词走词边界，避免误判"""
    if not text or not kw:
        return False
    if kw.isascii() and kw.isalpha():
        return re.search(rf'(?<![a-z]){re.escape(kw)}(?![a-z])', text) is not None
    return kw in text


# ============================================================
# 定向解读（P0-3）
# 旧做法是按板块轮播三句通用话，能套在任意一条新闻后面，等于没说。
# 新做法是按标题里真正出现的信号词给判断：匹配不上就整段不写，绝不凑字数。
# ============================================================
AI_READING_CUES = [
    (("融资", "投资", "估值", "天使轮", "a轮", "b轮", "c轮", "投了", "领投", "获投", "数千万"),
     "有钱在往这个方向押注，说明它不只是个概念了；顺着它找能落地的具体环节，比追热点实在"),
    (("发布", "推出", "上线", "开源", "开放"),
     "这是已经能直接上手的东西，花二十分钟试一遍，比看十篇评测有用"),
    (("裁员", "收缩", "下滑", "亏损", "倒闭"),
     "这条赛道在挤水分，如果你在做类似的事，先想想自己那部分会不会被替掉"),
    (("收购", "并购", "合并"),
     "格局在往头部收，小玩家的出路是做它看不上的极细分，或者早点找出口"),
    (("降价", "成本下降", "便宜", "免费", "价格战"),
     "成本在往下走，原本算不过账的小生意，可能现在就成立了"),
    (("监管", "规定", "法案", "合规", "治理", "标准"),
     "规则开始明确了，红线清楚反而是好事，可以放心投入"),
    (("芯片", "算力", "数据中心", "服务器", "显卡"),
     "底层供给在变，做上层应用的盯紧这块，它直接决定你的成本"),
    (("机器人", "具身", "机械臂"),
     "它替掉的是具体岗位，不是整个行业；看看你手上有没有这类环节"),
    (("模型", "大模型", "参数", "推理"),
     "能力又往前走了一步，把你现在做不好的那件事重新丢给它试一次"),
    (("编程", "代码", "开发"),
     "写代码的门槛又降了一档，不会写的人也能做出能跑的东西了"),
    (("智能体", "agent", "工作流", "自动化"),
     "这一层最值得先动手，它把一堆单点工具串成能自己跑完的流程"),
]

OPC_READING_CUES = [
    (("月入", "年入", "营收", "收入", "利润", "流水"),
     "它把钱的数字摆出来了，别只盯着数字，重点看客户是谁、从哪来"),
    (("变现", "付费", "订阅", "会员", "收费"),
     "收钱的闭环它跑通了，把收费方式拆出来，看能不能套到你手上的技能"),
    (("定价", "客单价", "涨价"),
     "定价是利润的命门，对照一下自己的报价，很可能定低了"),
    (("获客", "流量", "涨粉", "投放", "引流"),
     "这条最值钱，它讲清了客户从哪来，渠道是可以直接抄的"),
    (("自动化", "工作流", "工具", "效率", "sop"),
     "它省的是时间成本，把工具组合记下来，这套能复用到别的生意上"),
    (("出海", "跨境", "海外", "独立站", "亚马逊"),
     "海外的好处是同类竞争少、客单价高，难处在收款和沟通，先把这两块解决"),
    (("副业", "业余", "兼职"),
     "这条路不要求你辞职，先算算每周能投入几小时，再决定做多重"),
    (("自由职业", "接单", "外包"),
     "靠技能直接换钱，先看它的技能你能不能在一个月内练到可交付"),
    (("独立开发", "一人公司", "solo", "indie"),
     "一个人把产品做出来了，重点看它怎么找到第一批用户，那是最难的一步"),
    (("小众", "垂类", "细分"),
     "小切口的好处是大公司看不上，坏处是天花板有限，适合先跑通再扩"),
]


def targeted_reading(category: str, title: str, summary: str = "") -> str:
    """
    给一条真实新闻配针对性解读；没有可对应的信号就返回空字符串。
    只看标题：摘要里常混着正文片段，拿它匹配信号词会错配（曾出现过讲做工具却配上「收入」解读）。
    """
    text = (title or "").lower()
    cues = AI_READING_CUES if category == "AI Agent" else OPC_READING_CUES
    for kws, reading in cues:
        if any(_cue_hit(text, k) for k in kws):
            return reading
    return ""


# ============================================================
# 宏观大势解读：每个域给「这意味着什么 + 你该怎么做」
# 同样按信号词细分，避免四条听下来都像同一句模板。
# ============================================================
MACRO_READING = {
    "money": {
        "default": (
            "钱的价格在变，借钱的成本和手里现金的价值都会跟着动",
            "先算一遍自己每月的还款额，再决定是提前还债还是多留现金",
        ),
        "cues": [
            (("降准",), "银行能放出来的钱变多了，市场资金会宽松一些",
             "有房贷或经营贷的，留意重定价和置换机会；想小成本启动生意的，这时候借钱相对便宜"),
            (("降息",), "借钱的利息在往下走",
             "要贷款的话别急着签长约，先看看还有没有更低的窗口"),
            (("lpr",), "贷款利率的基准在调整",
             "浮动利率的贷款，明年月供可能跟着变，提前算一遍现金流"),
            (("净回笼", "净投放"), "央行在往市场里收钱或者放钱",
             "收钱的时候，借钱和融资都会更紧一点，有扩张计划的可以先缓一缓"),
            (("逆回购", "mlf"), "央行在调节市场上的短期资金量",
             "这种操作只影响短期的资金松紧；钱紧的时候回款会变慢，短期理财收益会略高一点"),
            (("加息",), "借钱的成本在往上走",
             "先把利率最高的那笔债还掉，扩张计划可以放慢半拍"),
            (("汇率", "人民币"), "人民币的强弱在变，直接改写进出口的价格",
             "做出口的，人民币偏弱时报价更有竞争力；做进口或买海外服务的，成本会变高"),
            (("社融",), "企业和个人借钱的意愿在变，这是经济冷热的先行指标",
             "社融回暖说明生意人敢借钱扩张了，你所在行业的订单可能跟着起来"),
            (("m2", "流动性"), "市场里的钱在变多或者变紧",
             "钱紧的时候回款会变慢，账上至少多留两个月的现金"),
            (("存款",), "存款的收益在变",
             "如果只靠存款吃利息，得接受收益率继续往下走，考虑做点分散"),
            (("国债", "债券"), "国债收益率是市场对未来的定价",
             "收益率往下走说明大家在担心增长，做生意的可以先保守一点"),
            (("银行", "信贷", "贷款"), "银行的放贷节奏和定价在调整",
             "这时候多问两家银行的报价，往往能省出真金白银"),
        ],
    },
    "market": {
        "default": (
            "资产价格在剧烈波动，这类波动会直接反映到你的账户上",
            "先看一眼自己持仓的成本线，别在情绪最激动的时候做买卖决定",
        ),
        "cues": [
            (("美股", "纳指", "道指", "标普"), "海外股市在剧烈波动，会顺着跨境基金和港股通传到你的账户",
             "持有海外基金的，先别在最恐慌的时候加仓；做外贸的，美元流动性收紧会传导到账期"),
            (("a股", "上证", "深证", "创业板", "科创板", "北交所"), "国内股市在放量波动",
             "有仓位的先看清自己的成本线和止损位；没仓位的，别在情绪最激动的时候进场"),
            (("港股", "恒指"), "港股对全球资金更敏感，涨跌往往比 A 股更剧烈",
             "如果你两边都有仓位，把港股的仓位留得比你以为的更宽一点"),
            (("黄金",), "避险资金在往黄金走",
             "黄金涨通常说明大家在担心，这时候降杠杆比追涨更划算"),
            (("原油",), "油价在动，运输和原料成本会跟着走",
             "做电商和制造的，提前锁一段运价，或者把包邮门槛往上调一档"),
            (("比特币",), "加密资产在放大市场的风险偏好",
             "它涨跌都很猛，别用生活必需的钱去碰"),
            (("美债",), "美债收益率是全球资产的定价锚",
             "它一涨，全球高估值资产都会承压，你手上的基金会跟着波动"),
            (("基金",), "基金的表现跟着市场在变",
             "先看自己买的是宽基还是行业主题，行业主题的波动要按能承受更大回撤来算"),
        ],
    },
    "demand": {
        "default": (
            "大家愿不愿意花钱在变，这直接决定你的东西好不好卖",
            "先看一眼自己最近三个月的复购率，再判断要不要扩张",
        ),
        "cues": [
            (("cpi",), "物价在变，直接关系到你的成本和客户的购买力",
             "CPI 在涨，你的进货和服务成本也会慢慢涨，定价要提前留出空间"),
            (("ppi",), "出厂价在变，上游成本已经开始往下游传导",
             "做制造或转卖的，留意上游报价，别签太长的固定价合同"),
            (("社零", "消费", "零售"), "大家愿不愿意掏钱，是你生意最直接的温度计",
             "消费在回暖就值得加大投放；在走弱就先守住老客户和复购"),
            (("楼市", "房地产", "房价", "购房"), "房地产还牵着很多家庭的资产负债表",
             "买房先看成交量和挂牌价，别只看单价；做家居建材的，需求会滞后反应"),
            (("就业", "失业率", "招聘"), "找工作的人多不多，直接决定你招人的成本和自己的议价空间",
             "招人变容易说明供给充足，可以挑更合适的人；想跳槽的，先看这个数再谈薪"),
            (("工资", "收入"), "居民的收入预期在变，这是所有消费的底座",
             "收入预期变差时，高客单生意会先受影响，低客单刚需反而更稳"),
            (("养老", "社保", "医保"), "社保和医保的规则在调整，直接关系你的长期现金流",
             "自由职业者要盯住自己的缴费方式，别断缴影响长期待遇"),
            (("生育", "人口"), "人口结构在变，很多生意的客群会跟着迁移",
             "做母婴、教育、房产的，得提前想清楚五年后的客群在哪"),
            (("旅游", "餐饮", "家政"), "线下消费的热度在变",
             "做本地生意的，跟着人流和客单价走，比看大盘更准"),
        ],
    },
    "business": {
        "default": (
            "生意的规则和环境在变，有的门在开，有的门在收",
            "对照一下自己做的事在开门的那边还是收门的那边，再决定要不要调整",
        ),
        "cues": [
            (("关税", "贸易", "经贸"), "关税和贸易规则在变，跨境生意的成本要重算",
             "做出口的，先算一遍加税后的毛利，再看要不要换市场或者换品类"),
            (("出口", "外贸", "进口"), "外部需求的冷热，直接决定很多工厂和贸易商的订单",
             "有外贸客户的盯紧账期；想接外贸单的，靠响应速度和服务取胜"),
            (("补贴", "降费"), "这是真金白银在减负",
             "符合条件就去申请，很多补贴没人领只是因为不知道"),
            (("减税", "退税", "增值税", "所得税"), "税负在调整，省下来的就是纯利润",
             "查一下自己行业今年有没有新的抵扣项，一年能省不少"),
            (("监管", "不正当竞争", "反内卷", "价格战"), "规则在收紧，靠低价硬拼的空间会被压缩",
             "先看清红线再动手，把合规成本提前算进模型里"),
            (("反垄断", "平台经济"), "平台规则在被约束，小玩家的议价空间可能变大",
             "如果你被平台抽成压得难受，留意这类政策带来的变化"),
            (("民营经济", "中小企业", "小微企业", "个体工商户"), "政策在给中小经营者松绑",
             "融资、税费、社保这三块每年都有新政策，值得花半天研究"),
            (("产业", "制造", "产能", "智能制造"), "产业在往某些方向集中，也在淘汰某些环节",
             "顺着政策倾斜的方向找位置，比逆着风硬做省力得多"),
            (("订单", "供应链"), "订单的流向就是钱在往哪走",
             "跟着订单找自己的位置，比凭空想需求靠谱"),
        ],
    },
    "tech": {
        "default": (
            "技术又往前走了一段，能做的事比上个月更多",
            "挑一件你手上最耗时的事，先试着让它替你跑一遍",
        ),
        "cues": [
            (("人工智能", "ai", "大模型"), "这是门槛最低、扩散最快的一次技术红利",
             "不用等它成熟，现在就挑一件每天重复两小时的事，试着让它接管"),
            (("芯片", "半导体", "算力"), "算力和硬件在变，做应用的你的成本结构会跟着变",
             "盯紧这块的报价，它会直接吃掉或者放大你的毛利"),
            (("机器人", "具身"), "机器人从展示走向落地，替代的是具体岗位",
             "如果你的工作里有大量重复搬运和操作，这是最该提前准备的方向"),
            (("新能源", "光伏", "储能", "电池"), "这条赛道产能和价格波动都很大",
             "想进去的话别做重资产环节，做配套服务和渠道更轻"),
            (("低空", "商业航天", "量子"), "新赛道的政策刚放开，早期机会往往在这里",
             "留意本地的试点政策，早进场的人赚的是信息差"),
            (("数据要素",), "数据正在被确权和定价",
             "手里有行业数据的，先想想它能不能变成可交易的东西"),
            (("创新药",), "医药的审批和支付方式在变",
             "这类赛道周期长、门槛高，个人更适合做周边服务而不是研发"),
            (("科技", "研发", "科技创新"), "研发投入在往某些方向集中",
             "看钱投到哪一环，那一环的用人需求和外包订单会先起来"),
        ],
    },
}


def macro_reading(domain: str, title: str) -> Tuple[str, str]:
    """返回 (这意味着什么, 你该怎么做)"""
    cfg = MACRO_READING.get(domain)
    if not cfg:
        return "", ""
    t = (title or "").lower()
    for kws, meaning, action in cfg["cues"]:
        if any(_cue_hit(t, k) for k in kws):
            return meaning, action
    return cfg["default"]


def today_action(has_ai: bool, has_opc: bool, domains: List[str] = None) -> str:
    """结尾给一个今天就能动手的具体动作，优先扣住当天出现的大势信号"""
    domains = domains or []
    if "money" in domains:
        return "花十分钟算一下你现在所有负债的实际利率，看看有没有更便宜的置换空间——这一步几乎人人可做，省下的是确定的钱。"
    if "market" in domains:
        return "打开你的基金和股票账户，算一下浮亏占你总资产多少——如果这个比例让你睡不好，说明仓位比你以为的更重，先减到能睡着的水平再说。"
    if "demand" in domains:
        return "翻一下你最近三个月的成交记录，算算老客户复购占多少——这个数字比任何宏观预测都更能告诉你下一步该扩张还是该守。"
    if "business" in domains:
        return "查一下你所在行业今年有没有能申请的补贴或税收优惠，很多钱放在那儿没人领，只是不知道。"
    if "tech" in domains:
        return "挑一件你每天重复超过一小时的事，今天就试着用工具替它跑一遍，跑通了你会回不去。"
    if has_opc:
        return "挑今天提到的一条搞钱路子，问自己一句：我能不能用更低的成本，先做个最小版本试试看？"
    if has_ai:
        return "挑今天最让你心动的一条动态，花三分钟搜一下原文，想一想它能不能用在你手头正在做的事上。"
    return "今天先记住一句金句，把它写进手机备忘录，睡前再看一眼。"


class NewsSummarizer:
    """
    负责将多源资讯合成为：
    1. 结构化 Markdown 报告（含金句 + 一人公司拆解 + AI 前沿 + 宏观大势 + 原始要闻清单留档）
    2. 「只听就够」的普通话播报底稿：所有值得知道的内容都会念出来，
       不留任何「去页面看」的尾巴；同时给出章节切分，供前端做跳转。
    """

    # 最近一次生成的章节切分：[{label, text}]，由 _build_spoken_script 写入
    last_chapters: List[Dict[str, str]] = []

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
        self.last_chapters = []
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

        # 整理来源列表（权威去重展示），并把解读带进卡片，让手机端也能直接读到
        all_sources: List[Dict[str, str]] = []
        for cat, items in collected_data.items():
            for item in items:
                note = (item.get("why_matter") or "").strip()
                if cat == "宏观大势":
                    meaning, action = macro_reading(item.get("domain", ""), item["title"])
                    label = item.get("domain_label", "")
                    note = f"{label}｜{meaning}。你该怎么做：{action}"
                elif cat in ("AI Agent", "一人公司") and not item.get("is_fallback"):
                    note = note or targeted_reading(cat, item["title"], item.get("summary", ""))
                all_sources.append({
                    "title": item["title"],
                    "category": cat,
                    "source_name": item.get("source_name", "权威来源"),
                    "url": item.get("url", "#"),
                    "why_matter": note,
                })

        category_summary: Dict[str, str] = {
            "今日金句": quote_of_the_day,
            "搞钱案例": lead_title,
            "宏观大势": f"今日识别 {len(collected_data.get('宏观大势', []))} 个跟决策有关的信号",
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
                why = it.get('why_matter', '').strip() or targeted_reading(cat, it['title'], it.get('summary', ''))
                md_lines.append(f"### 📌 【{cat}】{it['title']}")
                md_lines.append(f"- **① 一句话内容摘要**：{it.get('summary', it['title'])}")
                if why:
                    md_lines.append(f"- **② 人话解读**：{why}")
                md_lines.append("")

        # 今日宏观大势：每条给「事实 + 影响 + 行动」，取代原先的逐条念标题
        macro_items = collected_data.get("宏观大势", [])
        if macro_items:
            md_lines.extend([
                "---",
                "",
                "## 🌍 今日宏观大势（从时政 / 国际 / 财经中筛出跟你决策有关的信号）",
                ""
            ])
            for it in macro_items:
                meaning, action = macro_reading(it.get("domain", ""), it["title"])
                md_lines.extend([
                    f"### 【{it.get('domain_label', '大势')}】{it['title']}",
                    f"- **发生了什么**：{it.get('summary', it['title'])}",
                    f"- **这意味着什么**：{meaning}",
                    f"- **你该怎么做**：{action}",
                    f"- *来源：{it.get('source_name', '')}*",
                    ""
                ])

        md_lines.extend([
            "---",
            "",
            "## 📰 原始要闻清单（备查，音频里已按相关性筛过）",
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
        for idx, src in enumerate(all_sources[:60], 1):
            md_lines.append(f"{idx}. [{src['category']}] [{src['title']}]({src['url']}) - *{src['source_name']}*")

        markdown_content = "\n".join(md_lines)

        # 构建播报底稿：案例 + 前沿动态 + 宏观大势解读
        tts_script = self._build_spoken_script(
            date_str, quote_of_the_day, lead_title, 
            case_pain_point, case_model, case_tech_stack, case_revenue_and_traffic, case_beginner_guide,
            collected_data
        )

        return title, lead_title, markdown_content, tts_script, all_sources[:60], category_summary

    def _build_spoken_script(
        self, date_str: str, quote: str, lead_title: str,
        case_pain: str, case_model: str, case_stack: str, case_rev: str, case_guide: str,
        collected_data: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        构建「只听就够」的播报底稿：不留任何「去页面看」的内容，
        值得知道的全部念出来，被筛掉的明确交代一句为什么没念。
        风格：口语化开场、案例故事化、每条新闻配一句人话解读、结尾给一个可动手的小建议。
        同时把段落切分写进 self.last_chapters，前端据此做章节跳转。
        """
        # 金句末尾自带的句号先剥掉，避免与模板句号拼成「。。」双句号
        spoken_quote = safe_ai_replace(quote).strip().rstrip("。！？!?；;，,、 ")
        spoken_lead = safe_ai_replace(lead_title.replace("SOP", "标准实操流程"))

        # 案例正文做适度口语化清理，保留 Claude / Dify / n8n / Shopify 等业界通称
        clean_pain = case_pain.replace("7x24", "全天候24").replace("7*24", "全天候24")
        clean_model = case_model.replace("7x24", "全天候24").replace("7*24", "全天候24")
        clean_stack = safe_ai_replace(case_stack).replace(chr(10), " ")
        clean_rev = case_rev.replace("API", "接口调用").replace(chr(10), " ")
        clean_guide = safe_ai_replace(case_guide).replace(chr(10), " ")

        ai_items = collected_data.get("AI Agent", [])
        opc_items = collected_data.get("一人公司", [])
        macro_items = collected_data.get("宏观大势", [])

        # 每段既进播报稿，也作为前端章节（点了能跳到对应分钟）
        blocks: List[Tuple[str, str]] = []

        def add(label: str, text: str) -> None:
            if text and text.strip():
                blocks.append((label, text.strip()))

        try:
            _d = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            date_cn = f"{_d.month} 月 {_d.day} 日"
        except Exception:
            date_cn = date_str

        # 开场：一句话交代今天听什么，并明确「不用看」
        add("开场", (
            f"早上好，今天是 {date_cn}。接下来这几分钟，我把全球 AI 圈、一人公司圈，"
            "还有几个跟你钱包有关的大环境信号，全部讲给你听。"
            "你不用看任何文字，闭上眼跟着听就行。"
        ))

        add("今日金句", f"先送你今天的一句话：{spoken_quote}。这句话放在搞钱这件事上，特别应景。")

        # 1. 一人公司搞钱案例：五段各自成章，方便回头重听某一段
        add("案例·痛点", (
            f"接下来聊今天主推的一人公司案例：{spoken_lead}。我拆成五段讲。"
            f"第一段，它解决了什么让人头疼的问题？{clean_pain}"
        ))
        add("案例·收钱", f"第二段，它是怎么把这事做成生意、怎么收钱的？{clean_model}")
        add("案例·工具", f"第三段，它用了哪些工具？放心，都不贵。{clean_stack}")
        add("案例·赚钱", f"第四段，它到底赚到了多少？{clean_rev}")
        add("案例·抄作业", f"第五段，普通人怎么抄作业？{clean_guide}")

        def speak_with_reading(category: str, item: Dict[str, Any], idx: int) -> str:
            """一条新闻 = 标题 + 摘要 +（有信号才给的）定向解读"""
            t_sp = (safe_ai_replace(item['title'])
                    .replace("Personal Agent", "个人智能体")
                    .replace("Agent", "智能体").replace("OPC", "一人公司").replace("SaaS", "软件服务")
                    .replace("丨", "，").replace("｜", "，").replace("|", "，"))
            s_sp = (safe_ai_replace(item.get('summary', ''))
                    .replace("Agent", "智能体").replace("OPC", "一人公司")
                    .replace("丨", "，").replace("｜", "，")).rstrip("。；;，,、 ")
            reading = "" if item.get('is_fallback') else targeted_reading(
                category, item['title'], item.get('summary', '')
            )
            head = f"第{idx}条，{t_sp}。{s_sp}"
            head = re.sub(r'(人工智能|软件服务)\s+(?=[\u4e00-\u9fa5])', r'\1', head)
            return f"{head}。要我说，{reading}。" if reading else f"{head}。"

        # 2. 全球 AI 动态（真实抓取；解读按信号词定向生成，写不出就不写）
        if ai_items:
            if all(it.get("is_fallback") for it in ai_items):
                # 抓不到实时动态时，明确说成「判断」而不是冒充新闻，听着才不别扭
                ai_lines = ["今天 AI 圈没抓到实时动态，我不硬凑新闻，给你几条半年内都不会过时的判断。"]
            else:
                ai_lines = ["好，案例说完了，来看看过去 24 小时，AI 圈发生了什么。"]
            for i, item in enumerate(ai_items, 1):
                ai_lines.append(speak_with_reading("AI Agent", item, i))
            add("AI 动态", "\n".join(ai_lines))
        else:
            add("AI 动态", "今天 AI 圈的实时动态暂时没抓到，这段先跳过，不影响后面的内容。")

        # 3. 一人公司 / 独立开发者动态
        if opc_items:
            if all(it.get("is_fallback") for it in opc_items):
                opc_lines = ["再看一人公司这边。今天圈子里没大的新动静，我也不硬凑，给你三条值得记住的判断。"]
            else:
                opc_lines = ["再看一人公司和独立开发者那边，这里通常藏着普通人能抄的近路。"]
            for i, item in enumerate(opc_items, 1):
                opc_lines.append(speak_with_reading("一人公司", item, i))
            add("一人公司动态", "\n".join(opc_lines))

        # 4. 宏观大势：不念标题，只讲「发生了什么 / 这意味着什么 / 你该怎么做」
        macro_lines = []
        if macro_items:
            if len(macro_items) < 3:
                macro_lines.append("接下来这段聊大环境。今天真正值得说的信号不多，我不给你凑数，只讲这几条。")
            else:
                macro_lines.append(
                    "接下来这段，是今天最该留意的几个大环境信号。我不给你念标题，"
                    "只讲三件事：发生了什么，这意味着什么，以及落到你身上该怎么办。"
                )
            for i, it in enumerate(macro_items, 1):
                label = it.get("domain_label") or "大势"
                title_spoken = (safe_ai_replace(it["title"])
                                .replace("丨", "，").replace("｜", "，")
                                .rstrip("。；;，,、！？!? "))
                meaning, action = macro_reading(it.get("domain", ""), it["title"])
                macro_lines.append(
                    f"第{i}条，看{label}。{title_spoken}。这意味着，{meaning}。落到你身上，{action}。"
                )
        else:
            macro_lines.append("今天没筛出特别值得说的大环境信号，这段就跳过，不给你凑数。")

        # 明确交代「剩下的被筛掉了」，而不是让听众去别处翻文字
        backlog = (
            len(collected_data.get("学习强国", []))
            + len(collected_data.get("参考消息", []))
            + len(collected_data.get("新浪财经", []))
        )
        if backlog:
            macro_lines.append(
                f"政策和市场那几个渠道，我今天也全过了一遍，加起来 {backlog} 条。"
                "真正跟你判断有关的，上面已经讲完了；剩下的大多是看一眼就忘的消息，"
                "念了只会占你时间，我就不念了。"
            )
        add("宏观大势", "\n".join(macro_lines))

        # 5. 结尾：给一个今天就能动手的具体动作
        domains = [it.get("domain", "") for it in macro_items]
        add("今天动手的事", (
            "以上就是今天的全部内容，全在这段音频里了，没有藏在别处。"
            f"最后给你一件今天就能动手的事：{today_action(bool(ai_items), bool(opc_items), domains)}"
            "明天同一时间，不见不散。"
        ))

        self.last_chapters = [{"label": label, "text": text} for label, text in blocks]
        return "\n\n".join(text for _, text in blocks)

    async def _generate_with_llm(self, date_str: str, collected_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str, str, str, List[Dict[str, str]], Dict[str, str]]:
        # 如果配置了 LLM，使用同样的严格原则
        prompt = f"""你是一名严谨的科技商业分析师。请为 {date_str} 生成今日全球AI新闻汇总与一人公司拆解。
抓取数据：{json.dumps(collected_data, ensure_ascii=False)}

【写作规则（严格遵守）】：
1. **删除所有寒暄**：严禁出现“端上咖啡”、“我是老朋友云希”等寒暄填充词，直接陈述新闻事实。
2. **今日金句**：一句发人深省、充满行动力的一人公司搞钱金句。
3. **一人公司搞钱案例深度拆解**：讲透业务模式、痛点、全套AI工具链、变现路径、新手如何抄作业。
4. **全球AI与一人公司要闻**：每条包含①一句话内容摘要（含来源/关键事实）；②为什么值得关注。
5. **宏观大势（重点）**：从时政、国际、财经三源里挑出真正跟个人决策有关的信号，归入「钱的价格、你的钱袋子、大家敢不敢花钱、生意好不好做、技术在往哪走」五个域，每域最多一条。每条必须按「发生了什么 / 这意味着什么 / 你该怎么做」三句来写。严禁逐条念标题，严禁写能套在任何新闻后面的空话。外事会见、军事冲突、体育文娱、人事表彰一律不进播报，但仍要完整列在 markdown 清单里留档。
6. **其余要闻**：音频里只用一句话交代「还有 N 条整理在页面清单里」，不要逐条朗读。
7. **喜马拉雅新闻早餐**：若无当天内容则自动跳过。
8. **纯中文与音频要求**：全文主要采用中文，特别是语音播报稿（tts_script）必须全部使用地道中文，严禁出现任何英文长句或生硬缩写，保证语音播报纯正流利。

输出 JSON：
{{
  "title": "全球AI资讯要点、一人公司搞钱拆解与权威要闻汇总 ({date_str})",
  "lead_title": "今日搞钱案例标题",
  "markdown_content": "完整结构化 Markdown",
  "tts_script": "语音播报稿：案例五段 + AI 与一人公司逐条（每条带定向解读）+ 宏观大势四条（发生了什么/这意味着什么/你该怎么做）+ 一句可动手的事",
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
                    all_sources[:60],
                    content.get("category_summary", {})
                )
        raise RuntimeError("LLM call failed")

summarizer = NewsSummarizer()
