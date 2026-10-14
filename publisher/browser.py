"""Release-skill 五平台自动发文 · 有头浏览器生命周期管理

硬约束:全程有头。headless=False 在本模块内恒定,不提供任何无头开关。
"""
import time

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

try:
    from .config_loader import load_settings, SKILL_ROOT
except ImportError:  # 直接脚本运行兜底
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from config_loader import load_settings, SKILL_ROOT


class VisibleBrowser:
    """始终有头的浏览器会话。

    两种通道:
    - persistent(默认): Playwright 持久化用户目录,首次手动登录后登录态自动复用
    - cdp: 连接本机已启动 Edge/Chrome 的远程调试端口(复用日常浏览器登录态)
    """

    def __init__(self, settings=None, channel: str = None, cdp_url: str = None):
        self.settings = settings or load_settings()
        self.channel = channel or self.settings.browser_channel
        self.cdp_url = cdp_url or self.settings.cdp_url
        self.profile_dir = SKILL_ROOT / self.settings.profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._pw = None
        self._context: BrowserContext = None
        self._browser: Browser = None
        self._page: Page = None
        self._is_cdp = False

    # ---------- 生命周期 ----------
    def start(self) -> "VisibleBrowser":
        self._pw = sync_playwright().start()
        if self.cdp_url:
            print(f"[browser] 连接已启动浏览器的调试端口: {self.cdp_url}")
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
            self._is_cdp = True
            if self._browser.contexts:
                self._context = self._browser.contexts[0]
                self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            else:
                self._context = self._browser.new_context()
                self._page = self._context.new_page()
        else:
            print(f"[browser] 启动有头 {self.channel}(profile: {self.profile_dir})")
            args = []
            if self.settings.start_maximized:
                args.append("--start-maximized")
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel=self.channel,      # 系统真实 Edge/Chrome,非内置 chromium
                headless=False,            # 硬约束:可见窗口,永不为 True
                slow_mo=self.settings.slowmo_ms,
                viewport=None,             # 最大化真实窗口
                args=args,
            )
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.set_default_timeout(self.settings.default_timeout_ms)
        return self

    def stop(self):
        try:
            if self._is_cdp:
                if self._browser:
                    self._browser.close()
            elif self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()
            self._pw = None
            self._context = None
            self._page = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    # ---------- 访问 ----------
    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("浏览器尚未启动,请先 start()")
        return self._page

    @page.setter
    def page(self, value: Page):
        """切换当前活动页(平台改版后点击入口可能打开新标签页)"""
        self._page = value
        if value is not None:
            value.set_default_timeout(self.settings.default_timeout_ms)

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("浏览器尚未启动,请先 start()")
        return self._context

    def new_tab(self) -> Page:
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.settings.default_timeout_ms)
        return self._page


def visible_only_guard(headless: bool) -> bool:
    """防误用守卫:任何 headless=True 的意图都会被拒绝"""
    if headless:
        raise RuntimeError("本 skill 硬性要求有头浏览器,禁止无头模式")
    return False


if __name__ == "__main__":
    # 自检:启动一个可见窗口,验证浏览器通道可用
    with VisibleBrowser() as vb:
        vb.page.goto("about:blank")
        print("[self-check] 有头浏览器启动成功,窗口应已可见;5 秒后关闭")
        time.sleep(5)
    print("[self-check] 完成")
