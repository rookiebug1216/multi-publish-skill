# Release-skill · 五平台自动发文（有头浏览器）

抖音 · 快手 · 闲鱼 · 58同城 · 头条 一键自动发文，全程可见浏览器窗口，登录一次长期复用。

## 交给 AI 助手自动安装（推荐）

本仓库是一个 **Agent Skill**。你不用手动敲命令——把下面整段话发给你的 AI 助手（Trae / Claude Code / Cursor / 任意 Agent），它就能自己完成克隆、装依赖、自检与首次登录：

```text
请帮我安装并自检 GitHub 上的「Release-skill · 五平台自动发文」技能。

仓库地址：https://github.com/rookiebug1216/multi-publish-skill

请按顺序完成：
1. 克隆上述仓库到本机并进入仓库根目录（若本地已有副本则直接用）
2. 安装依赖：pip install -r requirements.txt
3. 自检：python run_publish.py --list
   —— 应输出 douyin / kuaishou / xianyu / wuba / toutiao 五个平台
4. 首次登录：python run_publish.py --platform all --login-check
   这会依次打开五个平台的有头浏览器窗口；遇到登录/验证码请在窗口中手动扫码或输入，
   完成后创建文件 verification/HUMAN_DONE，脚本会自动继续。登录态存入 browser-profile/ 供后续复用。
5. 完成后告诉我：安装是否成功、五平台登录态结果、以及下一步常用命令。

硬性约束：本 skill 全程有头（浏览器窗口可见），不绕过任何验证码 / 风控；
登录态目录 browser-profile/ 含账号凭据，禁止提交到任何公开仓库。
```

装好后即可用自然语言驱动，例如：「用 Release-skill 把 content/example_content.yaml 以草稿模式发到抖音和头条」。

## 三步上手

```powershell
# 1. 安装依赖（首次）
cd <项目根目录>
pip install -r requirements.txt

# 2. 首次登录（每平台一次，手动扫码）
python run_publish.py --platform all --login-check

# 3. 日常发文（默认存草稿，最安全）
python run_publish.py --platform douyin --content-file content/example_content.yaml --mode draft
```

## 核心特性

- **全程有头**：浏览器窗口真实可见，可随时观察与介入；代码层面禁用无头模式
- **登录态复用**：专用浏览器配置目录 `browser-profile/`，首次手动登录后自动复用，不存任何密码
- **选择器集中**：`config/platforms.yaml` 一处维护五平台入口与选择器，页面改版无需改代码
- **人工介入点**：登录/验证码/风控自动暂停，截图留档并提示，处理完继续
- **结构化台账**：每次执行写入 `ledger/publish_ledger.csv` + `.jsonl`（时间/平台/标题/状态/链接/截图）

## 常用命令

```powershell
python run_publish.py --list                          # 列出平台
python run_publish.py --platform all --login-check    # 五平台登录态体检
python run_publish.py --platform toutiao --content-file content/my.yaml --mode publish
python run_publish.py --stats                         # 台账统计
```

## 文档

- 技能说明（AI 助手视角）: [SKILL.md](SKILL.md)
- 交接文档（安装/登录/日常/验证码/故障排查）: [docs/HANDOVER.md](docs/HANDOVER.md)

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 免责声明

> 使用本工具即表示你已阅读、理解并同意以下全部条款。

1. **仅供学习与技术研究**：本项目为浏览器自动化技术的演示与实践，不是任何平台的官方工具，也不代表任何平台立场。
2. **合法合规使用**：使用者须自行遵守目标平台（抖音、快手、闲鱼、58同城、头条等）的用户协议、社区规范及所在地区法律法规；因违规使用（如发布违法、侵权、虚假信息）产生的一切后果由使用者自行承担。
3. **不绕过风控**：本工具刻意不提供验证码识别、风控绕过、批量刷量等能力，遇登录/验证码/风控一律暂停等待人工处理。请勿将其改造成违反平台规则的工具。
4. **无担保**：平台页面随时改版，选择器可能失效。本软件按「现状」提供，不附带任何明示或默示担保；作者不对使用或无法使用本软件导致的任何直接或间接损失负责。
5. **责任限制**：在适用法律允许的最大范围内，作者及贡献者不对因本项目产生的任何索赔、损害或其他责任承担责任。
