# 五平台自动发文 skill · 开源项目调研报告（Markdown 版）

> 采集方式: AutoGLM Browser Agent（Edge 有头浏览器实采，未用任何搜索 API 替代）
> 采集时间: 2026-09-21 13:20–13:56 GMT+8 · 6 轮浏览器任务 · 30 个候选项目
> 逐轮 Session ID / tab_id / 起始 URL / 截图 URL 见 `browser-provenance.md`（工作台 research/ 目录）
> 可视化版本: 同目录《五平台自动发文skill-开源项目调研报告.html》

## 一、执行摘要

- 五平台在 GitHub 上均存在可借鉴项目，但**没有单一项目覆盖全部五平台**——与用户判断一致。
- 主借鉴源：kebenxiaoming/matrix（962★，Playwright 多平台）、Superheroff/douyin_uplod（569★，MIT）、donggeai/xianyu-skills（19★，技能包形态）、DaBaoAgent/xianyu-auto-publisher（Playwright 闲鱼）、zz327455573/liulutong（头条编辑器适配）、r04943083/content-pilot（MIT，中文平台工程实践）。
- **唯一缺口：58同城**。唯一"发布向"仓库 pub58 仅 8★ 且基于已弃用的 PhantomJS（无头路线）。58 链路按"通用表单自动化 + 强人工介入"落地，已如实记录。
- 借鉴均为思路/流程/选择器层面，代码自研；针对共性短板改进：全程有头、选择器集中 YAML、人工介入暂停机制。

## 二、调研过程（Browser Agent 留痕）

| 轮次 | 目标 | Session ID（前 8 位） | 时间 | 结果 |
|---|---|---|---|---|
| R1 | 抖音 | be9c0082 | 13:20–13:23 | 5 项目 |
| R2 | 快手 | 23a9511e | 13:24–13:31 | 5 项目 |
| R3 | 闲鱼 | 2cb778b9 | 13:32–13:35 | 5 项目 |
| R4 | 58同城 | 40352c28→10781536 | 13:36–13:45 | 首轮超时，重试成功 |
| R5 | 头条 | 893171ff | 13:46–13:50 | 5 项目 |
| R6 | 多平台聚合 | 8adde54e | 13:52–13:56 | 5 项目 |

环境注记：Chrome 的 AutoGLM 扩展更新后被禁用（disable_reasons=8192），探活失败后切换 Edge 通道完成全部调研。

## 三、分平台清单

### 抖音
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [Superheroff/douyin_uplod](https://github.com/Superheroff/douyin_uplod) ★主借鉴 | 569 | MIT | 上传发布全流程、话题/@人、Docker 部署 |
| [withwz/douyin_upload](https://github.com/withwz/douyin_upload) | 164 | MIT | 并发批量上传组织 |
| [Richard0403/dy-auto](https://github.com/Richard0403/dy-auto) | 130 | MIT | 发布页元素定位 |
| [spider-ios/autox-release](https://github.com/spider-ios/autox-release) | 1.1k | — | 多平台产品思路（App 端，不采用技术栈） |
| [TheSongg/apostify](https://github.com/TheSongg/apostify) | 82 | Apache-2.0 | 渠道抽象 |

### 快手
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [kebenxiaoming/matrix](https://github.com/kebenxiaoming/matrix) ★主借鉴 | 962 | 页面未确认① | Playwright 多平台适配层、登录态持久化、发布流程抽象 |
| [xixihhhh/clipforge](https://github.com/xixihhhh/clipforge) | 850 | — | 分发出口设计 |
| [cmlanche/jixieshou-autowatch-kuaishou](https://github.com/cmlanche/jixieshou-autowatch-kuaishou) | 404 | — | 不采用（刷视频 App） |
| [howhowtocook/video_auto_upload](https://github.com/howhowtocook/video_auto_upload) | 19 | — | cookie 按平台目录组织 |
| [XXXXBully/social-auto-upload-tool](https://github.com/XXXXBully/social-auto-upload-tool) | 12 | — | 前后端分离架构、平台清单 |

### 闲鱼
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [Evvvvvvwan/XianYuSmart](https://github.com/Evvvvvvwan/XianYuSmart) | 62 | — | 全流程运营版图（协议端） |
| [donggeai/xianyu-skills](https://github.com/donggeai/xianyu-skills) ★主借鉴 | 19 | — | ★技能包形态+复用已登录浏览器（与本项目同构） |
| [najiuwanan/xianyu-Plus](https://github.com/najiuwanan/xianyu-Plus) | 17 | — | 多账号管理 |
| [xiaotuzhenji/xianyu-lite-v2](https://github.com/xiaotuzhenji/xianyu-lite-v2) | 7 | — | 轻量化取舍 |
| [DaBaoAgent/xianyu-auto-publisher](https://github.com/DaBaoAgent/xianyu-auto-publisher) ★主借鉴 | 4 | 页面未确认① | ★Playwright 闲鱼网页发布实践 |

### 58同城
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [lihansunbai/Fang_Scrapy](https://github.com/lihansunbai/Fang_Scrapy) | 330 | — | 58 请求组织与反爬经验 |
| [Northxw/City58](https://github.com/Northxw/City58) | 66 | — | 详情页 URL 规律 |
| [naginoa/python-spider](https://github.com/naginoa/python-spider) | 27 | — | 参考案例 |
| [newcitysoft-org/pub58](https://github.com/newcitysoft-org/pub58) 唯一发布向 | 8 | — | 发布流程模块分解（AutoPost/BrowserCreator/ImageDownloader）；无头路线不采用 |
| [hequan2017/58job-scraper](https://github.com/hequan2017/58job-scraper) | 2 | — | 无发布价值 |

**如实记录**：58 平台无活跃高质量网页发布开源项目；本 skill 58 链路 = 通用表单自动化 + 类目配置 + 强人工介入。

### 头条
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [DNQtech/wechat_publiser](https://github.com/DNQtech/wechat_publiser) | 16 | — | 多平台任务编排 |
| [DNQtech/baowen-publisher](https://github.com/DNQtech/baowen-publisher) | 14 | — | Electron 架构、矩阵号管理 |
| [OceanBBBBbb/auto_write_toutiaohao](https://github.com/OceanBBBBbb/auto_write_toutiaohao) | 7 | — | 发布流程 Python 实践（生成部分不采用） |
| [zz327455573/liulutong](https://github.com/zz327455573/liulutong) ★主借鉴 | 3 | — | ★头条编辑器为 ProseMirror 系的适配细节 |
| [niumanju2586/toutiao-publisher](https://github.com/niumanju2586/toutiao-publisher) 形态同构 | 2 | — | ★"Skill 包+浏览器自动化"方向验证 |

### 多平台聚合（横向）
| 项目 | Star | 许可 | 借鉴点 |
|---|---|---|---|
| [wanghaisheng/easy-uploader](https://github.com/wanghaisheng/easy-uploader) | 383 | — | 上传调度队列（headless 路线不采用） |
| [ArmanShirzad/SocialMediaContentCreationAndPostingAutomationPlatform](https://github.com/ArmanShirzad/SocialMediaContentCreationAndPostingAutomationPlatform) | 48 | — | 内容管道 |
| [iamasters-academy/content-engine](https://github.com/iamasters-academy/content-engine) | 18 | — | Agentic 技能包+发布 |
| [obaskly/AutoWP](https://github.com/obaskly/AutoWP) | 10 | — | 平台适配层抽象 |
| [r04943083/content-pilot](https://github.com/r04943083/content-pilot) ★主借鉴 | 9 | MIT | ★Playwright 中文平台工程实践 |

## 四、许可与风险

- 确认宽松许可：douyin_uplod（MIT）、douyin_upload（MIT）、apostify（Apache-2.0）、content-pilot（MIT）。
- ① 标注项（matrix、xianyu-auto-publisher 等）：采集时许可证徽章未入截图可视区；按"思路级借鉴+代码自研"策略风险可控，可后续核对 LICENSE。
- 本 skill 全部代码自研，借鉴限于流程/思路/选择器组织；平台选择器自行实测校准维护。

## 五、调研 → skill 落地映射

| 调研发现 | 落地设计 | 对应文件 |
|---|---|---|
| matrix 用 Playwright 多平台发布 | Python+Playwright，channel=msedge/chrome | publisher/browser.py |
| 多数项目无头路线→风控高 | headless 恒 False（硬编码），slow_mo 慢放 | publisher/browser.py |
| xianyu-skills 复用已登录浏览器 | persistent profile + 可选 CDP 双通道 | browser.py · HANDOVER §5 |
| 选择器硬编码易失效 | 五平台选择器集中 YAML 多候选 | config/platforms.yaml |
| liulutong：头条编辑器 ProseMirror | contenteditable 多候选策略 | platforms.yaml→toutiao |
| pub58 发布流程分解 | BasePlatform 模板方法 | publisher/base.py |
| 58 无活跃项目（缺口） | 类目配置+强人工介入 | publisher/wuba.py |
| 开源项目缺执行留痕 | CSV+JSONL 台账+逐步截图+HUMAN_DONE 协议 | publisher/ledger.py · base.py |

---
*报告由 AutoClaw 生成 · 2026-09-21*
