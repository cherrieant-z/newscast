# 每日调查新闻与高保真语音播报系统 (NewsCast)

> 专为移动端打造的每日调查新闻与高保真语音播报全栈应用。  
> 每天早晨 6:00 自动抓取过去 24 小时重点资讯（AI、OPC、国际经济、YouTube、X、TikTok），深度生成“主打调查报道 + 简讯速览 + 来源链接”，并通过微软高保真神经人声 TTS 合成普通话 MP3 音频，配合移动端 PWA 离线播放器随时收听。

---

## 🌟 核心特性

1. **自动化采集与调度 (Python)**
   - **每日定时**：基于 APScheduler 与 GitHub Actions，每天清晨自动生成（提前到北京时间 05:30，6 点睁眼即可听）。
   - **六大板块全真实抓取**：
     - **每日金句**：一句发人深省的搞钱箴言。
     - **一人公司搞钱案例**：深度拆解一个可复制的赚钱路子。
     - **全球 AI 动态**：36氪 / 极客公园 / 爱范儿等中文源，真实抓取。
     - **一人公司新闻**：少数派 / 独立开发者社区，真实抓取。
     - **权威要闻**：学习强国、参考消息、新浪财经要闻，逐条播报。
     - **喜马拉雅·10分钟新闻早餐**：当天有则播，无则跳过。
   - **生动有趣·技术小白友好**：术语全部大白话化，每条新闻配一句“人话解读”，结尾送一个今天就能动手的小建议。

2. **高保真普通话语音合成 (Edge-TTS)**
   - 默认采用微软高保真新闻演播男声 `zh-CN-YunxiNeural`（云希，沉稳纪实播音风格），支持一键切换 `zh-CN-XiaoxiaoNeural`（晓晓）等。
   - 生成纯文本播报稿并自动过滤 Markdown 噪音字符，带有平滑标点停顿与自然语流。

3. **数据存储与标准 REST API**
   - 本地持久化使用轻量高效的 SQLite (通过 SQLAlchemy 异步引擎管理)。
   - 提供丰富端点：
     - `GET /api/reports/latest`：获取最新一期全量简报与音频元数据。
     - `GET /api/reports`：历史往期简报列表。
     - `POST /api/reports/trigger`：手动触发立即生成流水线（开发测试或实时抓取无需等待明早 6 点）。
     - `GET /api/status`：系统运行与调度状态。

4. **手机端 PWA 现代交互界面**
   - **响应式设计**：专为手机竖屏阅读优化，适配 iPhone/Android 底部安全区域。
   - **PWA 离线支持**：内置 `manifest.json` 与 `sw.js` Service Worker，支持“添加到主屏幕”，秒变独立原生级 App。
   - **图文卡片阅读**：横向分类胶囊标签平滑切换、主打深度卡片展开、所有简讯支持一键跳转原始出处。
   - **底部全局悬浮播放器**：
     - 实时进度拖拽与已播/总时长显示。
     - 快退 15 秒 / 快进 15 秒。
     - 0.75x、1.0x、1.25x、1.5x、2.0x 独立无损调速。
     - **Web Media Session API**：完美支持手机锁屏界面与系统通知栏后台控制（专辑封面、歌曲名、暂停/播放与跳段）。

---

## 🚀 快速启动

### 方式一：Windows 一键启动（推荐）

双击项目根目录下的 `run.bat`，或在 PowerShell 中执行：
```powershell
.\run.ps1
```
服务将在 `http://localhost:8000` 启动，浏览器打开即可使用。

### 方式二：手动命令启动

```bash
# 1. 激活虚拟环境 (已配置 uv)
.venv\Scripts\activate

# 2. 启动 FastAPI 服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式三：Docker 容器化部署

```bash
docker compose up -d --build
```

---

## 📱 移动端与局域网收听

在同一 Wi-Fi 下，用手机浏览器打开：
```text
http://<你的电脑局域网IP>:8000
```
- 点击 Safari 底部分享按钮 -> **“添加到主屏幕”** 即可全屏作为原生 App 使用。
- 支持锁屏后锁屏界面/蓝牙耳机直接播放、切歌与快进。

---

## 📻 播客订阅（一睁眼就能听）

每次生成早报后，会自动产出播客订阅地址 `podcast.xml`。把它订阅到任意播客 App，每天早晨打开 App 就有新节目，无需手动打开网页：

```text
https://cherrieant-z.github.io/newscast/podcast.xml
```

- **小宇宙 / 喜马拉雅 / Apple Podcasts / Pocket Casts**：在“添加节目 / 添加 RSS”里粘贴上面地址即可。
- 音频地址默认指向 `https://cherrieant-z.github.io/newscast/`；若使用自定义域名，请在 GitHub Actions 环境变量里设置 `PODCAST_BASE_URL`。
- 播客封面目前用的是 SVG 图标；若要在 Apple Podcasts 上架，建议替换成一张 1400×1400 的 JPG/PNG 封面。
