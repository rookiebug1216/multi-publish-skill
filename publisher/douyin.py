"""抖音创作者平台发布器(网页端)

2025-09 实测改版适配:
- 旧直链 /creator-micro/content/upload 登录后可能跳回创作者中心首页
- 首页含"作品发布"卡片区:发布高清视频/发布图文/发布全景视频/发布文章
- 适配策略:先试旧直链 input[type=file];无则点击"发布高清视频"卡片;上传用 file chooser 兜底

借鉴: Superheroff/douyin_uplod(MIT, Playwright 流程) — 上传输入框、话题输入、定时发布等交互思路
登录检测: 继承基类 login_check(登录墙优先),选择器见 config/platforms.yaml
"""
import time
from pathlib import Path

try:
    from .base import BasePlatform
except ImportError:
    from base import BasePlatform


class Douyin(BasePlatform):
    name = "douyin"
    display_name = "抖音"

    def open_publisher(self):
        # 旧直链可能跳回首页;首页需点击"发布高清视频"卡片进入上传页
        self.page.wait_for_timeout(2500)
        try:
            if self.page.locator("input[type=file]").count() > 0:
                return  # 已在含上传控件的页面
        except Exception:
            pass
        before = len(self.browser.context.pages)
        card = self.first_locator("video_entry_card")
        if card is None:
            self.wait_human("未找到'发布高清视频'入口,请人工点击进入视频上传页后继续")
            return
        card.click()
        self.page.wait_for_timeout(5000)
        pages = self.browser.context.pages
        if len(pages) > before:  # 新标签页打开则切换活动页
            self.browser.page = pages[-1]
        self.page.wait_for_timeout(2000)

    def fill_content(self, content: dict):
        media = content.get("media_files") or []
        if not media:
            raise ValueError("抖音发布需要 media_files(视频或图片路径列表)")
        channel = self._upload(media)
        self.log(f"已选择 {len(media)} 个文件(通道:{channel}),等待上传处理...")
        self.page.wait_for_timeout(10000)

        cover = content.get("cover_image") or ""
        if cover:
            self._set_cover(cover)

        title = content.get("title") or ""
        desc = content.get("description") or content.get("body") or ""
        t = self.first_locator("title_input")
        if t and title:
            t.click()
            t.type(title, delay=60)
        editor = self.first_locator("desc_editor")
        if editor and desc:
            editor.click()
            editor.type(desc, delay=60)
        if not editor and not t:
            self.log("未找到标题/描述输入框,保留已上传文件,后续人工补写")

    def _ensure_cover_dialog_closed(self):
        """确保封面弹层已关闭(否则会遮挡后续标题/描述输入)"""
        for _ in range(3):
            try:
                wrap = self.page.locator("[class*='dy-creator-content-modal-wrap']")
                if wrap.count() == 0 or not wrap.first.is_visible():
                    return
            except Exception:
                return
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
            self.page.wait_for_timeout(1500)

    def _click_text_js(self, text: str) -> bool:
        """按精确文案点击最内层可见元素(用于弹层内'完成'等非 button 元素)"""
        try:
            return bool(self.page.evaluate(
                """(t) => {
                const els = [...document.querySelectorAll('button,div,span,a')].filter(e =>
                  e.offsetParent !== null && (e.textContent||'').trim() === t);
                const inner = els.filter(e => !els.some(o => o !== e && e.contains(o)));
                if (inner.length) { inner[0].click(); return true; }
                return false; }""",
                text,
            ))
        except Exception:
            return False

    def _find_pending_cover_slot(self):
        """返回仍显示'选择封面'的槽位按钮(已设置过的槽位不再匹配)"""
        slots = self.page.locator(self.sel("cover_slot"))
        btn_sel = self.sel("cover_slot_button")
        try:
            n = slots.count()
        except Exception:
            return None
        for i in range(n):
            try:
                c = slots.nth(i).locator(btn_sel).first
                if c.count() > 0 and c.is_visible() and "选择封面" in (c.inner_text() or ""):
                    return c
            except Exception:
                continue
        return None

    def _set_cover(self, cover_path: str) -> bool:
        """设置自定义封面(而非视频截帧)。

        抖音有"竖封面3:4""横封面4:3"两个槽位,逐个设置同一张封面图。
        流程:点槽位"选择封面" → 弹层点"上传封面"(需 force 点击,否则被浮层遮挡)
        → 捕获 file chooser 填图 → 点"完成" → 确保弹层关闭。
        封面槽位只在视频上传完成后才出现,故先等待。
        """
        cover_path = str(Path(cover_path).resolve())
        if not Path(cover_path).exists():
            self.log(f"封面文件不存在,跳过: {cover_path}")
            return False

        upload_text = self.sel("cover_upload_text", "上传封面")
        done_text = self.sel("cover_done_text", "完成")
        try:
            self.page.wait_for_selector(self.sel("cover_slot"), timeout=60000)
        except Exception:
            self.log("未找到封面槽位(可能仍在上传),跳过自定义封面")
            return False

        done = 0
        for _ in range(3):  # 最多 3 轮,防止误判导致死循环
            btn = self._find_pending_cover_slot()
            if btn is None:
                break
            try:
                btn.click()
                self.page.wait_for_timeout(3500)

                up = self.page.get_by_text(upload_text, exact=True).first
                if up.count() == 0:
                    self.log(f"未找到'{upload_text}'入口,跳过该槽位")
                    self._ensure_cover_dialog_closed()
                    continue
                # 需 force:按钮被"设置两张封面..."提示浮层遮挡
                with self.page.expect_file_chooser(timeout=20000) as fc:
                    up.click(force=True)
                fc.value.set_files([cover_path])
                self.log(f"已上传封面图(第{done + 1}张): {Path(cover_path).name}")
                self.page.wait_for_timeout(6000)

                if not self._click_text_js(done_text):
                    self.log(f"未找到'{done_text}'按钮,封面可能未生效")
                self.page.wait_for_timeout(3500)
                self._ensure_cover_dialog_closed()
                done += 1
            except Exception as e:
                self.log(f"设置封面失败({str(e)[:70]}),继续")
                self._ensure_cover_dialog_closed()

        if done:
            self.log(f"已确认自定义封面(共 {done} 个槽位)")
        else:
            self.log("自定义封面未生效,请人工在页面设置")
        return done > 0

    def submit(self, mode: str):
        btn = self.first_locator("publish_button")
        if not btn:
            raise RuntimeError("未找到发布按钮,请检查页面是否改版")
        btn.click()
        self.page.wait_for_timeout(3000)

    def save_draft(self) -> bool:
        loc = self.first_locator("draft_button")
        if loc:
            loc.click()
            self.page.wait_for_timeout(3000)
            return True
        return False

    def extract_result_url(self) -> str:
        try:
            return self.page.url
        except Exception:
            return ""
