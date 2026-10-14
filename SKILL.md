---
name: release-skill
description: 五平台自动发文技能（抖音/快手/闲鱼/58同城/头条），基于有头浏览器 Playwright 自动化，支持登录态复用、草稿/发布双模式、结构化台账。当用户要在这些平台发布视频/图文/闲置/信息时使用。
---

# Release-skill · 五平台自动发文

## 功能
用**可见浏览器窗口**（非无头）自动向五个平台投递内容：
抖音（视频/图文）、快手（视频/长文）、闲鱼（闲置商品）、58同城（本地信息）、头条（图文/视频）。

## 硬性约束
1. **全程有头**：浏览器窗口真实可见，任何环节不使用无头模式（`browser.py` 中 headless 恒为 False）
2. **不存密码**：首次登录由用户手动完成，登录态保存在 `browser-profile/` 目录，后续自动复用
3. **不绕过风控**：遇到登录/验证码/扫码时暂停（截图 + 控制台提示），等待人工处理后继续
4. **选择器集中**：所有平台入口与选择器在 `config/platforms.yaml`，页面改版只改配置

## 快速使用（AI 助手调用）

### 0. 环境准备（首次）
```powershell
cd <项目根目录>
pip install -r requirements.txt
python -m playwright install chromium   # 可选;channel=msedge/chrome 直接用系统浏览器,通常无需
```

### 1. 首次登录（每平台一次）
```powershell
python run_publish.py --platform all --login-check
```
浏览器打开各平台入口 → 检测到未登录 → 控制台提示 → **用户手动扫码/登录** → 创建 `verification/HUMAN_DONE` 文件继续 → 登录态自动存入 `browser-profile/`。

### 2. 日常发文
```powershell
# 内容文件模板: content/example_content.yaml
python run_publish.py --platform douyin --content-file content/example_content.yaml --mode draft
python run_publish.py --platform all --content-file content/my_post.yaml --mode publish
```

### 3. 台账查询
```powershell
python run_publish.py --stats
```
台账: `ledger/publish_ledger.csv`（Excel 可开）+ `publish_ledger.jsonl`（机器可读）

## 命令速查
| 命令 | 用途 |
|---|---|
| `--platform <name>` | 单平台发布（douyin/kuaishou/xianyu/wuba/toutiao） |
| `--platform all` | 顺序发布五平台 |
| `--mode draft` | 填好后存草稿（默认，最安全） |
| `--mode publish` | 填好后点击发布（受 auto_submit_default 约束） |
| `--mode fill` | 只填内容，人工点击 |
| `--login-check` | 只检测登录态 |
| `--browser msedge/chrome` | 覆盖浏览器通道 |
| `--cdp http://127.0.0.1:9222` | 连接已启动浏览器的调试端口 |

## 内容文件格式（YAML）
```yaml
title: 标题
description: 描述/简介
body: |
  图文正文（头条/快手长文）
price: ""            # 闲鱼/58
media_files:         # 视频/图片绝对路径
  - C:\path\to\video.mp4
topics: [数码, 开箱]  # 抖音/快手话题
platform_overrides:  # 按平台覆盖
  xianyu: {price: "99"}
```

## 目录结构
```
Release-skill/
├── SKILL.md                ← 本文件（技能说明）
├── README.md               ← 快速上手
├── run_publish.py          ← CLI 入口
├── requirements.txt
├── config/
│   ├── settings.yaml       ← 浏览器/交互/路径设置
│   └── platforms.yaml      ← 五平台入口+选择器（改版只需改这里）
├── publisher/
│   ├── browser.py          ← 有头浏览器生命周期（禁无头）
│   ├── base.py             ← 平台基类（登录检测/填单/人工暂停/台账）
│   ├── config_loader.py
│   ├── ledger.py           ← 结构化台账
│   └── douyin.py kuaishou.py xianyu.py wuba.py toutiao.py
├── content/example_content.yaml
├── ledger/                 ← 发文台账输出
├── verification/           ← 验证截图
├── browser-profile/        ← 登录态（首次自动创建,勿删）
└── docs/HANDOVER.md        ← 交接文档
```

## 平台说明
| 平台 | 类型 | 入口 |
|---|---|---|
| 抖音 | 视频/图文 | creator.douyin.com 创作者平台 |
| 快手 | 视频/长文 | cp.kuaishou.com |
| 闲鱼 | 闲置商品 | goofish.com（原咸鱼网页版） |
| 58同城 | 本地信息 | bang.58.com |
| 头条 | 图文/视频 | mp.toutiao.com 头条号 |

## 故障排查要点
- **登录失效**：重跑 `--login-check`，或删除 `browser-profile/` 重新登录
- **选择器失效（页面改版）**：更新 `config/platforms.yaml` 对应键
- **发布按钮找不到**：见 verification/ 截图，用浏览器 F12 查新选择器
- 详见 `docs/HANDOVER.md`

## 安全与合规
- 本技能只做「投递」，不做内容创作/伪原创/批量生成
- 遇验证码/风控一律暂停等人工，不绕过、不对抗
- 请遵守各平台用户协议与发布规范
