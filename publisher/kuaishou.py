"""快手创作者平台发布器(网页端)

入口: https://cp.kuaishou.com/article/publish/video (视频)
     https://cp.kuaishou.com/article/publish/long (图文/长文)
登录检测: 继承基类 login_check(登录墙优先)
"""
from pathlib import Path

try:
    from .base import BasePlatform
except ImportError:
    from base import BasePlatform


class Kuaishou(BasePlatform):
    name = "kuaishou"
    display_name = "快手"

    def open_publisher(self):
        # 关闭快手新手引导蒙层(react-joyride):叉号/Esc/点蒙层,三连兑底
        for attempt in range(4):
            try:
                spot = self.page.locator("#react-joyride-portal").count()
            except Exception:
                spot = 0
            if spot == 0:
                break
            closed = False
            for sel in ("[class*='joyride'] [aria-label*='close' i]", "[class*='joyride'] [class*='close']", "button:has-text('知道了')", "button:has-text('跳过')", "button:has-text('下一步')", "button:has-text('下一个')"):
                try:
                    b = self.page.locator(sel).first
                    if b.count() > 0 and b.is_visible():
                        b.click(force=True)
                        self.page.wait_for_timeout(1200)
                        closed = True
                        break
                except Exception:
                    continue
            if not closed:
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                self.page.wait_for_timeout(1000)
        # entry_url 已是发布页;图文模式切换
        if (self.cfg.get("publish_type") or "").startswith("image") or self.cfg.get("publish_type") == "article":
            url = ((self.cfg.get("selectors") or {}).get("article_entry_url") or
                   "https://cp.kuaishou.com/article/publish/long")
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(3000)

    def fill_content(self, content: dict):
        media = content.get("media_files") or []
        desc = content.get("description") or content.get("title") or ""
        cover = content.get("cover_image") or ""
        if media:
            upload = self.first_locator("upload_input") or self.page.locator("input[type=file]").first
            files = [str(Path(m).resolve()) for m in media]
            upload.set_input_files(files)
            self.log(f"已选择 {len(files)} 个文件,等待上传...")
            self.page.wait_for_timeout(5000)
            if cover:
                self._set_cover(cover)

        if desc:
            editor = self.first_locator("desc_editor")
            if editor:
                editor.click()
                editor.type(desc, delay=80)
            elif not media:
                raise RuntimeError("未找到描述/正文输入框")

    def _set_cover(self, cover_path: str) -> bool:
        """设置自定义封面(封面图而非视频截帧)。

        流程:点封面预览 → 弹层切"上传封面"tab → 弹层内图片 input 填图 → 点"确认"。
        注意:封面编辑入口只在视频上传完成后才出现,故先等待该元素。
        """
        cover_path = str(Path(cover_path).resolve())
        if not Path(cover_path).exists():
            self.log(f"封面文件不存在,跳过: {cover_path}")
            return False
        try:
            entry = self.first_locator("cover_entry")
            if entry is None:
                try:
                    self.page.wait_for_selector("[class*='_default-cover']", timeout=60000)
                    entry = self.first_locator("cover_entry")
                except Exception:
                    pass
            if entry is None:
                self.log("未找到封面编辑入口(可能仍在上传),跳过自定义封面")
                return False
            entry.click()
            self.page.wait_for_timeout(3000)

            tab = self.page.locator(self.sel("cover_tab"), has_text="上传封面").first
            if tab.count() == 0:
                self.log("未找到'上传封面'tab,跳过自定义封面")
                return False
            tab.click()
            self.page.wait_for_timeout(2500)

            # 弹层内的图片 input 是页面上最后一个 file input
            inputs = self.page.locator("input[type=file]")
            n = inputs.count()
            if n == 0:
                self.log("弹层内未找到图片上传 input,跳过自定义封面")
                return False
            inputs.nth(n - 1).set_input_files([cover_path])
            self.log(f"已上传自定义封面: {Path(cover_path).name},等待载入...")
            self.page.wait_for_timeout(6000)

            cands = self.sel("cover_confirm")
            if isinstance(cands, str):
                cands = [cands]
            for sel in cands:
                b = self.page.locator(sel).first
                if b.count() > 0 and b.is_visible():
                    b.click()
                    self.page.wait_for_timeout(3000)
                    self.log("已确认自定义封面")
                    return True
            self.log("未找到'确认'按钮,封面可能未生效")
            return False
        except Exception as e:
            self.log(f"设置自定义封面失败({str(e)[:80]}),继续")
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
            return False

    def submit(self, mode: str):
        """点击底部"发布"按钮。

        注意:侧边栏有"发布作品"(含"发布"子串),用 button:has-text('发布') 会误命中,
        故必须用精确文案 :text-is('发布')。
        """
        btn = None
        for sel in ("button:text-is('发布')", "[role=button]:text-is('发布')"):
            try:
                loc = self.page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    btn = loc
                    break
            except Exception:
                continue
        if btn is not None:
            btn.click()
            self.log("已点击底部'发布'按钮")
            self.page.wait_for_timeout(4000)
        else:
            # JS 兜底:精确文案"发布"且可见的最内层元素
            hit = self.page.evaluate(
                """() => {
                const all = [...document.querySelectorAll('button,[role=button],a,div,span')]
                  .filter(e => (e.textContent||'').trim() === '发布' && e.offsetParent !== null);
                const inner = all.filter(e => !all.some(o => o !== e && e.contains(o)));
                if (inner.length) { inner[0].click(); return true; }
                return false; }"""
            )
            if not hit:
                raise RuntimeError("未找到发布按钮")
            self.log("JS 兜底点击'发布'")
            self.page.wait_for_timeout(4000)
        # 可能的二次确认弹窗
        for sel in ("button:has-text('确认发布')", "button:has-text('确定')", "button:has-text('继续发布')"):
            try:
                b = self.page.locator(sel).first
                if b.count() > 0 and b.is_visible():
                    b.click()
                    self.log(f"二次确认: {sel}")
                    self.page.wait_for_timeout(4000)
                    break
            except Exception:
                continue

    def save_draft(self) -> bool:
        loc = self.first_locator("draft_button")
        if loc:
            loc.click()
            self.page.wait_for_timeout(2500)
            return True
        return False
