#!/usr/bin/env python3
"""Release-skill 五平台自动发文 · 命令行入口

用法:
  python run_publish.py --platform douyin --content-file content/example_content.yaml --mode draft
  python run_publish.py --platform all --login-check          # 五平台登录态体检
  python run_publish.py --list                                # 列出支持的平台
  python run_publish.py --stats                               # 查看台账统计

模式:
  --mode draft    填好内容后存草稿(默认,最安全)
  --mode publish  填好内容并点击发布(受 settings.auto_submit_default 控制)
  --mode fill     只填内容不提交,人工在浏览器里检查后自行点击
"""
import argparse
import sys
from pathlib import Path

# Windows GBK 控制台兼容:强制 UTF-8 输出,避免 ⚠ 等字符崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_ROOT = Path(__file__).resolve().parent
PUBLISHER_DIR = SKILL_ROOT / "publisher"
sys.path.insert(0, str(SKILL_ROOT))

from publisher.config_loader import load_settings, load_platform, list_platforms  # noqa: E402
from publisher.browser import VisibleBrowser  # noqa: E402
from publisher.ledger import Ledger  # noqa: E402

PLATFORM_CLASSES = {}
for _mod, _cls in [("douyin", "Douyin"), ("kuaishou", "Kuaishou"),
                   ("xianyu", "Xianyu"), ("wuba", "Wuba"), ("toutiao", "Toutiao")]:
    try:
        _m = __import__(f"publisher.{_mod}", fromlist=[_cls])
        PLATFORM_CLASSES[_mod] = getattr(_m, _cls)
    except ImportError as e:
        print(f"[warn] 平台模块加载失败: {_mod} ({e})")


def load_content_file(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"内容文件不存在: {p}")
    import yaml
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit("内容文件格式错误:应为 YAML dict")
    return data


def build_platform(name: str, browser, settings, publish_type: str = None):
    if name not in PLATFORM_CLASSES:
        sys.exit(f"不支持的平台: {name}(支持: {', '.join(PLATFORM_CLASSES)})")
    cfg = load_platform(name)
    cls = PLATFORM_CLASSES[name]
    inst = cls(browser, settings, cfg)
    # 同步 display_name
    if cfg.get("display_name"):
        inst.display_name = cfg["display_name"]
    if cfg.get("publish_type"):
        inst.cfg.setdefault("publish_type", cfg["publish_type"])
    # 命令行 --publish-type 优先覆盖(如头条 article/video 分两次运行)
    if publish_type:
        inst.cfg["publish_type"] = publish_type
    return inst


def main():
    ap = argparse.ArgumentParser(description="五平台自动发文(有头浏览器)")
    ap.add_argument("--platform", help="平台名(douyin/kuaishou/xianyu/wuba/toutiao/all)")
    ap.add_argument("--content-file", help="内容 YAML 文件(见 content/example_content.yaml)")
    ap.add_argument("--mode", choices=["draft", "publish", "fill"], default="draft",
                    help="draft=存草稿(默认) publish=发布 fill=只填不提交")
    ap.add_argument("--publish-type", help="覆盖平台发布类型(头条: article|video; 快手: video|article)")
    ap.add_argument("--login-check", action="store_true", help="只检测登录态,不发布")
    ap.add_argument("--browser", help="覆盖浏览器通道(msedge/chrome)")
    ap.add_argument("--cdp", help="连接已启动浏览器的 CDP 地址(如 http://127.0.0.1:9222)")
    ap.add_argument("--list", action="store_true", help="列出支持的平台")
    ap.add_argument("--stats", action="store_true", help="台账统计")
    args = ap.parse_args()

    settings = load_settings()

    if args.list:
        print("支持的平台:")
        for n in list_platforms():
            print(f"  - {n}")
        return
    if args.stats:
        led = Ledger(SKILL_ROOT / settings.ledger_dir)
        import json
        print(json.dumps(led.stats(), ensure_ascii=False, indent=2))
        return
    if not args.platform:
        ap.print_help()
        return

    targets = list(PLATFORM_CLASSES.keys()) if args.platform == "all" else [args.platform]
    content = load_content_file(args.content_file) if args.content_file else None

    if args.login_check:
        # 登录态体检:逐平台开页检测(不等待人工,结果写台账)
        led = Ledger(SKILL_ROOT / settings.ledger_dir)
        results = {}
        with VisibleBrowser(settings, channel=args.browser, cdp_url=args.cdp) as vb:
            for name in targets:
                inst = build_platform(name, vb, settings)
                record = {
                    "time": "", "platform": name, "platform_display": inst.display_name,
                    "title": "(login-check)", "mode": "login_check", "status": "checking",
                    "result_url": "", "screenshot": "", "detail": "",
                }
                try:
                    inst.page.goto(inst.entry_url, wait_until="domcontentloaded")
                    inst.page.wait_for_timeout(3000)
                    ok, msg = inst.login_check()
                    results[name] = {"login": ok, "detail": msg}
                    record["status"] = "login_ok" if ok else "needs_login"
                    record["detail"] = msg
                    record["result_url"] = inst.page.url
                    record["screenshot"] = inst.screenshot("login_check")
                    print(f"[{name}] {'OK 已登录' if ok else 'X 未登录'}: {msg}")
                except Exception as e:
                    results[name] = {"login": False, "detail": str(e)}
                    record["status"] = "failed"
                    record["detail"] = str(e)
                    record["screenshot"] = inst.screenshot("login_check_error")
                    print(f"[{name}] 检测失败: {e}")
                finally:
                    try:
                        inst.page.close()
                    except Exception:
                        pass
                    led.append(record)
                if name != targets[-1]:
                    vb.new_tab()
        import json
        print("\n登录态体检结果:")
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not content:
        sys.exit("发布模式需要 --content-file 指定内容文件")

    records = []
    with VisibleBrowser(settings, channel=args.browser, cdp_url=args.cdp) as vb:
        for name in targets:
            print(f"\n===== {name} =====")
            inst = build_platform(name, vb, settings, publish_type=args.publish_type)
            try:
                rec = inst.run(content, mode=args.mode)
                records.append(rec)
            except Exception as e:
                print(f"[{name}] 执行失败: {e}")
                records.append({"platform": name, "status": "failed", "detail": str(e)})
            if name != targets[-1]:
                vb.new_tab()

    print("\n===== 执行汇总 =====")
    for r in records:
        print(f"  {r.get('platform')}: {r.get('status')} | {r.get('detail', '')[:80]}")
    print(f"台账: {SKILL_ROOT / settings.ledger_dir / 'publish_ledger.csv'}")


if __name__ == "__main__":
    main()
