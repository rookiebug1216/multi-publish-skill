"""multi-publish-skill 五平台自动发文 · 平台基类

职责:登录检测、导航到发文入口、填写内容、人工介入暂停、截图、台账写入。
所有平台实现类继承本类。
"""
import datetime as _dt
import sys
from pathlib import Path

# Windows GBK 控制台兼容:强制 UTF-8 输出
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from .ledger import Ledger
    from .config_loader import Settings, SKILL_ROOT
except ImportError:  # 直接脚本运行兜底
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ledger import Ledger
    from config_loader import Settings, SKILL_ROOT


def now_str() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class HumanIntervention(Exception):
    """需要人工介入(登录/验证码/风控)。抛出前应已截图并提示用户。"""


class BasePlatform:
    """平台发布器基类。

    子类需实现:
      - login_check() -> (bool, str)   登录态检测,返回(是否已登录, 说明)
      - open_publisher()               导航到发文入口
      - fill_content(content)          填写标题/正文/上传文件
      - submit(mode)                   按 mode 提交(draft/publish/ask)
    """

    # 子类覆盖
    name = "base"
    display_name = "基础平台"

    def __init__(self, browser, settings: Settings, platform_cfg: dict):
        self.browser = browser
        self.page = browser.page
        self.settings = settings
        self.cfg = platform_cfg or {}
        self.ledger = Ledger(SKILL_ROOT / (settings.ledger_dir or "ledger"))
        self.shot_dir = SKILL_ROOT / (settings.verification_dir or "verification")
        self.shot_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 工具 ----------
    @property
    def entry_url(self) -> str:
        return self.cfg.get("entry_url") or self.cfg.get("url") or ""

    def log(self, msg: str):
        print(f"[{self.name}] {now_str()} {msg}", flush=True)

    def login_check(self):
        """通用登录态检测(墙优先):先查登录墙,再查登录态标识,最后查 URL 特征。

        平台配置 selectors.login_wall: 登录页/登录弹窗特征(存在=未登录)
        平台配置 selectors.login_indicator: 已登录特征(存在=已登录)
        """
        wall = self.first_locator("login_wall")
        if wall:
            return False, "出现登录墙/登录弹窗(未登录)"
        ok = self.first_locator("login_indicator")
        if ok:
            return True, "检测到登录态标识"
        url = self.page.url
        if any(k in url for k in ("login", "passport", "sso")):
            return False, f"跳转到登录页: {url}"
        return False, "未检测到登录态标识"

    def screenshot(self, tag: str) -> str:
        """截图到 verification/ 目录,返回绝对路径"""
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.shot_dir / f"{self.name}_{tag}_{ts}.png"
        try:
            self.page.screenshot(path=str(path), full_page=False)
            self.log(f"截图: {path.name}")
            return str(path)
        except Exception as e:  # 截图失败不阻塞主流程
            self.log(f"截图失败({e}),继续")
            return ""

    def sel(self, key: str, default: str = "") -> str:
        """读取平台配置中的选择器。支持多候选(列表),返回原值;由 _first_existing 处理"""
        sels = (self.cfg.get("selectors") or {}).get(key, default)
        return sels

    def first_locator(self, key: str, default: str = ""):
        """按候选选择器顺序找第一个可见元素,返回 locator(找不到返回 None)"""
        cands = self.sel(key, default)
        if isinstance(cands, str):
            cands = [cands]
        for sel in cands:
            if not sel:
                continue
            loc = self.page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible():
                    return loc
            except Exception:
                continue
        return None

    def wait_human(self, reason: str, timeout: int = None):
        """暂停等待人工处理(登录/验证码/风控)。

        - 控制台明确提示原因与剩余时间
        - 每 5 秒轮询检测 done 文件: verification/HUMAN_DONE
        - 超时抛 HumanIntervention
        """
        timeout = timeout or self.settings.human_wait_seconds
        done_flag = self.shot_dir / "HUMAN_DONE"
        self.screenshot("wait_human")
        print("\n" + "=" * 60, flush=True)
        print(f"⚠ 需要人工处理[{self.display_name}]: {reason}", flush=True)
        print(f"  请在浏览器窗口中完成处理后,在本目录创建文件: {done_flag}", flush=True)
        print(f"  PowerShell: New-Item -ItemType File -Force \"{done_flag}\"", flush=True)
        print(f"  最长等待 {timeout} 秒", flush=True)
        print("=" * 60, flush=True)
        deadline = _dt.datetime.now() + _dt.timedelta(seconds=timeout)
        while _dt.datetime.now() < deadline:
            if done_flag.exists():
                done_flag.unlink(missing_ok=True)
                self.log("检测到 HUMAN_DONE,继续执行")
                return
            self.page.wait_for_timeout(5000)
        raise HumanIntervention(f"{self.display_name} 等待人工处理超时({timeout}s): {reason}")

    def confirm_publish(self) -> bool:
        """发布前确认。settings.auto_submit_default:
        - ask: 控制台询问 y/n
        - auto: 直接通过(已在文档提示风险)
        - never: 返回 False,由人工在浏览器里自己点
        """
        mode = self.settings.auto_submit_default
        if mode == "auto":
            return True
        if mode == "never":
            self.log("auto_submit=never:内容已填写,请人工在浏览器中点击发布")
            return False
        try:
            ans = input(f"[{self.name}] 内容已填写,是否点击发布? (y=发布 / n=不发布): ").strip().lower()
        except (EOFError, OSError):
            self.log("无交互终端,按不发布处理(内容已保留在页面)")
            return False
        return ans in ("y", "yes", "")

    def _upload(self, files: list) -> str:
        """上传文件:优先 input[type=file] 直填;否则监听 file chooser 点触发区。返回通道名"""
        files = [str(Path(f).resolve()) for f in files]
        upload = self.first_locator("upload_input")
        if upload is not None:
            upload.set_input_files(files)
            return "input"
        trigger = self.first_locator("upload_trigger")
        if trigger is None:
            raise RuntimeError("未找到上传入口:无 input[type=file] 且未配置/未找到 upload_trigger")
        with self.page.expect_file_chooser(timeout=15000) as fc:
            trigger.click()
        fc.value.set_files(files)
        return "filechooser"

    # ---------- 主流程 ----------
    def run(self, content: dict, mode: str = "draft", login_only: bool = False) -> dict:
        """端到端执行:入口 → 登录检测 → 填内容 → 提交 → 台账。

        返回台账记录 dict。任何失败也写台账(status=failed/pending_human)。
        """
        record = {
            "time": now_str(),
            "platform": self.name,
            "platform_display": self.display_name,
            "title": (content or {}).get("title", "")[:80],
            "mode": mode,
            "status": "started",
            "result_url": "",
            "screenshot": "",
            "detail": "",
        }
        try:
            self.log(f"打开发文入口: {self.entry_url}")
            self.page.goto(self.entry_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)
            self.screenshot("entry")

            ok, msg = self.login_check()
            if not ok:
                record["status"] = "needs_login"
                record["detail"] = f"未登录或登录态失效: {msg}"
                self.ledger.append(record)
                self.wait_human(f"请登录{self.display_name}: {msg}")
                ok, msg = self.login_check()
                if not ok:
                    raise HumanIntervention(f"登录后检测仍未通过: {msg}")
                record["status"] = "logged_in"

            if login_only:
                record["status"] = "login_ok"
                record["detail"] = "登录态有效(仅检测模式)"
                self.screenshot("login_ok")
                self.ledger.append(record)
                return record

            self.open_publisher()
            self.screenshot("editor")

            self.fill_content(content)
            self.screenshot("filled")

            if mode == "draft":
                done = self.save_draft()
                record["status"] = "draft_saved" if done else "draft_manual"
            elif mode == "fill":
                self.wait_human("内容已填写完成。请在浏览器中人工检查并自行决定发布/放弃;完成后继续")
                record["status"] = "filled_not_submitted"
                record["detail"] = "fill 模式:已填写,是否发布由人工在浏览器决定"
            else:
                if self.confirm_publish():
                    self.submit(mode)
                    record["status"] = "published"
                    self.page.wait_for_timeout(4000)
                    record["result_url"] = self.extract_result_url()
                else:
                    record["status"] = "filled_not_submitted"
            record["screenshot"] = self.screenshot("done")
            record["detail"] = record["detail"] or f"mode={mode} 完成"
            self.ledger.append(record)
            return record

        except HumanIntervention as e:
            record["status"] = "pending_human"
            record["detail"] = str(e)
            record["screenshot"] = self.screenshot("human")
            self.ledger.append(record)
            raise
        except Exception as e:
            record["status"] = "failed"
            record["detail"] = f"{type(e).__name__}: {e}"
            record["screenshot"] = self.screenshot("error")
            self.ledger.append(record)
            raise

    # ---------- 子类接口 ----------
    # login_check() 使用基类通用实现(登录墙优先);平台如有特殊逻辑可覆盖

    def open_publisher(self):
        """默认入口即编辑器;需额外点击的平台覆盖此方法"""
        pass

    def fill_content(self, content: dict):
        raise NotImplementedError

    def submit(self, mode: str):
        raise NotImplementedError

    def save_draft(self) -> bool:
        """存草稿:键盘 End 滚底 → 候选选择器强点击 → JS 文案兵底。
        抖音新版编辑器滚动在内层容器,locator 滚动不生效,用键盘与 JS 双通道。"""
        try:
            self.page.keyboard.press("End")
            self.page.wait_for_timeout(1500)
            self.page.keyboard.press("End")
            self.page.wait_for_timeout(1500)
        except Exception:
            pass
        cands = self.sel("draft_button")
        if isinstance(cands, str):
            cands = [cands]
        for sel in cands or []:
            try:
                loc = self.page.locator(sel).first
                if loc.count() == 0:
                    continue
                try:
                    loc.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                self.page.wait_for_timeout(500)
                if loc.is_visible():
                    loc.click(force=True)
                    self.page.wait_for_timeout(3000)
                    return True
            except Exception:
                continue
        # JS 兑底:找文案含"草稿"的按钮直接点击(在新层容器内也能触发)
        try:
            clicked = self.page.evaluate(
                """() => { const els=[...document.querySelectorAll('button, [role=button], a, span, div')];
                const b=els.find(e=>{const t=(e.textContent||'').trim(); return t && t.length<=8 && t.includes('草稿') && e.offsetParent!==null});
                if(b){b.click(); return (b.textContent||'').trim();} return null; }"""
            )
            if clicked:
                self.log(f"JS 兑底点击: {clicked}")
                self.page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
        self.log("未找到草稿按钮,内容已留在编辑器,请人工保存")
        return False

    def extract_result_url(self) -> str:
        try:
            return self.page.url
        except Exception:
            return ""
