# Release-skill 交接文档

> 五平台自动发文技能（抖音/快手/闲鱼/58同城/头条）· 基于 Playwright 有头浏览器
> 本文档面向接手者，覆盖：环境安装 → 首次登录 → 日常发文 → 验证码处理 → 故障排查。

---

## 1. 环境安装

### 1.1 依赖
- Windows 10/11（本机已验证：Windows 11, Python 3.13/3.11, Edge + Chrome 已装）
- Python ≥ 3.10（含 pip）
- Microsoft Edge 或 Google Chrome（任一；默认用 Edge）

### 1.2 安装步骤
```powershell
cd <项目根目录>
pip install -r requirements.txt      # playwright + PyYAML
```

说明：`config/settings.yaml` 中 `channel: msedge` 使用系统已装的 Edge，无需再下载浏览器。若想用 Chrome，改成 `channel: chrome`。

### 1.3 安装自检
```powershell
python publisher\browser.py
```
预期：弹出**可见的** Edge 窗口（空白页），5 秒后自动关闭，控制台打印 `[self-check] 完成`。
若窗口未出现 → 见 §6 故障排查。

---

## 2. 首次登录（每平台一次）

### 2.1 为什么需要
本技能不保存任何账号密码。登录态保存在 `browser-profile/`（Playwright 持久化用户目录）中，首次手动登录一次后，后续运行自动复用。

### 2.2 操作步骤
```powershell
python run_publish.py --platform all --login-check
```
浏览器会依次打开五个平台的发文入口：

| 顺序 | 平台 | 入口 | 登录方式 |
|---|---|---|---|
| 1 | 抖音 | creator.douyin.com | 扫码（抖音 App） |
| 2 | 快手 | cp.kuaishou.com | 扫码（快手 App） |
| 3 | 闲鱼 | goofish.com | 淘宝账号扫码/密码 |
| 4 | 58同城 | bang.58.com | 手机号+验证码 |
| 5 | 头条 | mp.toutiao.com | 扫码（抖音 App）/ 手机号 |

每打开一个平台，控制台会提示「⚠ 需要人工处理」并暂停：
1. 在浏览器窗口中手动完成登录（扫码/验证码）
2. 在 PowerShell 中执行（复制即用）：
   ```powershell
   New-Item -ItemType File -Force "<项目根目录>\verification\HUMAN_DONE"
   ```
3. 脚本检测到该文件后自动继续下一个平台

### 2.3 登录验证
全部完成后，控制台输出五平台登录态 JSON 汇总（`"login": true` 即成功），截图保存在 `verification/` 目录。

### 2.4 复用与失效
- 登录态长期有效（各平台 30 天～数月不等）
- 失效表现：发布时又提示登录 → 重跑 `--login-check` 或直接在发布流程中重新扫码
- 彻底重置：删除 `browser-profile/` 文件夹后重新登录

---

## 3. 日常发文

### 3.1 准备内容文件
复制 `content/example_content.yaml` 为模板：
```yaml
title: "我的标题"
description: "视频/商品描述"
body: |
  图文正文（头条图文、快手长文用）
price: "199"                       # 仅闲鱼/58
media_files:
  - C:\Users\you\Videos\demo.mp4   # 视频/图片绝对路径
topics: ["数码", "开箱"]            # 抖音/快手话题
platform_overrides:
  xianyu:
    title: "【闲置出】九成新 XX"
    price: "99"
```

### 3.2 执行发布
```powershell
# 单平台·草稿模式（推荐日常用）
python run_publish.py --platform douyin --content-file content\my.yaml --mode draft

# 五平台齐发
python run_publish.py --platform all --content-file content\my.yaml --mode draft

# 确认草稿没问题后，正式发布
python run_publish.py --platform douyin --content-file content\my.yaml --mode publish
```

### 3.3 三种模式
| 模式 | 行为 | 适用 |
|---|---|---|
| `--mode draft` | 填好内容 → 尝试点击「存草稿」 | 日常默认，最安全 |
| `--mode publish` | 填好内容 → 控制台确认 → 点击「发布」 | 最终发布 |
| `--mode fill` | 只填内容，停在编辑器 | 人工检查后自己点 |

### 3.4 发布确认（publish 模式）
`config/settings.yaml` 中 `auto_submit_default`：
- `ask`（默认）：控制台问 `y/n` 后才点发布
- `auto`：不问直接点（谨慎）
- `never`：永远不自动点，只填内容

### 3.5 台账
每次执行自动追加记录到：
- `ledger/publish_ledger.csv` —— Excel 直接打开
- `ledger/publish_ledger.jsonl` —— 程序读取

字段：`time, platform, platform_display, title, mode, status, result_url, screenshot, detail`

状态含义：
| status | 含义 |
|---|---|
| draft_saved | 已存草稿 |
| published | 已点击发布 |
| filled_not_submitted | 已填写未提交（fill 模式或用户选 n） |
| needs_login / pending_human | 需要人工登录/处理 |
| failed | 执行失败（见 detail 与截图） |

统计：`python run_publish.py --stats`

---

## 4. 验证码与风控的人工介入

### 4.1 设计原则
本技能**不绕过任何验证码与风控**。遇到即暂停：截图（`verification/`）+ 控制台提示 + 等待 HUMAN_DONE 文件，处理完继续。

### 4.2 你会看到什么
```
============================================================
⚠ 需要人工处理[抖音]: 请登录抖音: 未找到登录态标识(可能需要扫码)
  请在浏览器窗口中完成处理后,在本目录创建文件:
  <项目根目录>\verification\HUMAN_DONE
  PowerShell: New-Item -ItemType File -Force "...\HUMAN_DONE"
  最长等待 900 秒
============================================================
```

### 4.3 处理方式
1. 切到浏览器窗口，完成扫码/滑块/短信验证
2. 执行提示中的 `New-Item` 命令
3. 脚本自动继续（超时默认 15 分钟，可在 `settings.yaml` 的 `human_wait_seconds` 调整）

### 4.4 各平台风控提示
- **抖音**：新设备/异地登录可能触发二次验证；频繁发布建议先草稿
- **快手**：扫码登录较稳；发布频率过高会限流
- **闲鱼**：淘宝风控较严，建议 CDP 模式复用日常浏览器（见 §5）
- **58同城**：发布信息需实名+手机验证；类目选择是流程一部分
- **头条**：头条号有发文频次限制（图文每日若干篇）

---

## 5. 进阶：复用日常浏览器（CDP 模式）

适用：闲鱼等对环境敏感的平台，或想直接用日常浏览器里已登录的账号。

```powershell
# 1. 完全退出 Edge，然后以调试端口启动（保留日常登录态）
msedge --remote-debugging-port=9222

# 2. 在打开的 Edge 里确认各平台已登录

# 3. 技能连接该浏览器
python run_publish.py --platform xianyu --content-file content\my.yaml --mode draft --cdp http://127.0.0.1:9222
```
或把 `cdp_url: http://127.0.0.1:9222` 写进 `config/settings.yaml` 一劳永逸。

---

## 6. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `playwright` 报未安装 | 依赖没装 | `pip install -r requirements.txt` |
| 浏览器窗口没弹出 | channel 配错/浏览器未装 | 确认 `settings.yaml` 的 channel 与实际浏览器一致 |
| `Executable doesn't exist` | 系统无 Edge/Chrome | 装 Edge，或 `python -m playwright install chromium`（仍是有头） |
| 登录后又提示未登录 | 登录态过期 | 重跑 `--login-check`；闲鱼建议 CDP 模式 |
| `未找到发布按钮` | 页面改版 | 用 F12 找新选择器 → 更新 `config/platforms.yaml` |
| 上传文件没反应 | 文件路径错/格式不支持 | 用绝对路径；确认平台支持的媒体格式 |
| 等待人工超时 | 15 分钟没处理 | 加大 `human_wait_seconds` 或重新运行 |
| 五平台连发中途失败 | 单平台异常 | 看台账 `status=failed` 的 detail；单平台重跑 |

### 6.1 页面改版后的选择器维护
1. 打开平台发文页，F12 检查元素
2. 修改 `config/platforms.yaml` 中对应平台的 selectors（支持字符串或列表=多候选）
3. 无需改任何 Python 代码

### 6.2 日志与证据
- 控制台实时输出每步操作
- `verification/` 目录：每次执行的截图（entry/editor/filled/done/error）
- `ledger/`：结构化台账

---

## 7. 安全与合规承诺

- 不采集、不存储任何账号密码或敏感凭据
- 不绕过验证码、不对抗平台风控
- 仅做内容投递，不做内容创作/伪原创/批量生成
- 使用者需遵守各平台用户协议与发布规范

---

## 8. 目录速查

```
Release-skill\
├── SKILL.md / README.md / docs\HANDOVER.md   文档三件套
├── run_publish.py                            CLI 入口
├── config\settings.yaml                      全局设置
├── config\platforms.yaml                     五平台选择器（改版改这里）
├── publisher\                                核心代码（8 个模块）
├── content\example_content.yaml              内容模板
├── ledger\                                   发文台账（CSV+JSONL）
├── verification\                             执行截图
└── browser-profile\                          登录态目录（勿删）
```
