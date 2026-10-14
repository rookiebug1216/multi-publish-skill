"""今日头条(头条号)发布器(网页端)

入口: https://mp.toutiao.com/profile_v4/graphic/publish (图文)
     https://mp.toutiao.com/profile_v4/video/publish (视频)
登录检测: 继承基类 login_check(登录墙优先)
"""
from pathlib import Path

try:
    from .base import BasePlatform
except ImportError:
    from base import BasePlatform


class Toutiao(BasePlatform):
    name = "toutiao"
    display_name = "头条"

    def open_publisher(self):
        # 登录后 sso 可能重定向到个人主页/首页:始终强制导航到目标发布页
        target = self.entry_url
        if (self.cfg.get("publish_type") or "article") == "video":
            target = ((self.cfg.get("selectors") or {}).get("video_entry_url") or
                      "https://mp.toutiao.com/profile_v4/video/publish")
        # 文章/视频入口不同,须按 publish_type 强制导航到目标页
        # (base.run 已先打开 entry_url,故不能只用 "profile_v4" 判断)
        if target.split("?")[0] not in (self.page.url or ""):
            self.page.goto(target, wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
        # 若被重定向回首页(权限/风控),暂停提示
        if "profile_v4" not in (self.page.url or ""):
            self.wait_human(f"未能进入头条发布页(当前: {self.page.url[:60]});请在浏览器中手动进入'写文章'后继续")
        # 关闭首发激励弹窗(× 按钮)与 AI 助手引导
        for sel in ("button:has-text('已知悉协议')", "[class*='modal'] [class*='close']", "text=我知道了"):
            try:
                b = self.page.locator(sel).first
                if b.count() > 0 and b.is_visible():
                    b.click(force=True)
                    self.page.wait_for_timeout(1200)
            except Exception:
                continue
        try:
            close = self.page.locator("[class*='modal'] svg, .close-btn").first
            if close.count() > 0 and close.is_visible():
                close.click(force=True)
                self.page.wait_for_timeout(800)
        except Exception:
            pass
        # 关闭 AI 创作助手侧栏(byte-drawer 遮罩会拦截后续点击)
        for _ in range(2):
            try:
                drawer = self.page.locator(".byte-drawer-wrapper, [class*='ai-assistant-drawer']")
                if drawer.count() == 0:
                    break
                closed = False
                for sel in ("[class*='ai-assistant-drawer'] [class*='close']", ".byte-drawer-wrapper [aria-label*='close' i]", "[class*='drawer'] svg[class*='close']"):
                    try:
                        b = self.page.locator(sel).first
                        if b.count() > 0 and b.is_visible():
                            b.click(force=True)
                            self.page.wait_for_timeout(1000)
                            closed = True
                            break
                    except Exception:
                        continue
                if not closed:
                    try:
                        self.page.keyboard.press("Escape")
                        self.page.wait_for_timeout(800)
                    except Exception:
                        pass
                try:
                    if self.page.locator(".byte-drawer-mask").count() == 0:
                        break
                except Exception:
                    break
            except Exception:
                break

    def fill_content(self, content: dict):
        ptype = self.cfg.get("publish_type") or "article"
        title = content.get("title") or ""
        desc = content.get("description") or ""
        body = content.get("body") or desc

        if title:
            t = self.first_locator("title_input")
            if t:
                t.click()
                # ProseMirror 系编辑器必须用 insert_text(完整 input 事件链),type() 不触发内部状态同步
                self.page.keyboard.insert_text(title)
                self.page.wait_for_timeout(800)

        if ptype == "article":
            editor = self.first_locator("article_editor")
            if editor and body:
                editor.click()
                self.page.keyboard.insert_text(body)
                self.page.wait_for_timeout(1500)
            elif not title:
                raise RuntimeError("未找到文章编辑器且标题也未填入")
        else:
            media = content.get("media_files") or []
            if media:
                channel = self._upload([str(Path(m).resolve()) for m in media])
                self.log(f"已上传 {len(media)} 个文件(通道:{channel})")
                self.page.wait_for_timeout(5000)
            if desc:
                d = self.first_locator("desc_editor")
                if d:
                    d.click()
                    self.page.keyboard.insert_text(desc)
                    self.page.wait_for_timeout(800)

    def _tap(self, sel: str, label: str, wait: int = 2500) -> bool:
        """点击第一个可见匹配元素(force,避免被浮层拦截);成功返回 True"""
        try:
            b = self.page.locator(sel).first
            if b.count() > 0 and b.is_visible():
                b.click(force=True)
                self.log(f"{label}: {sel}")
                self.page.wait_for_timeout(wait)
                return True
        except Exception:
            pass
        return False

    def submit(self, mode: str):
        if (self.cfg.get("publish_type") or "article") == "video":
            self._submit_video()
        else:
            self._submit_article()

    def _submit_video(self):
        """视频发布:点"发布" → 处理"作品同步授权"等弹窗 → 完成"""
        ok = self._tap("button:has-text('发布')", "点击'发布'", 5000)
        for _ in range(3):
            if (self._tap("button:has-text('确定')", "弹窗-确定", 4000)
                    or self._tap("button:has-text('确认发布')", "弹窗-确认发布", 4000)
                    or self._tap("button:has-text('确认')", "弹窗-确认", 4000)):
                continue
            break
        if not ok:
            self.log("未捕获到发布按钮,请以截图为准")

    def _submit_article(self):
        """头条文章发布流程(2026-09 实测,顺序不可颠倒):
        1) 点"预览并发布" → 展开发布前设置页(展示封面/添加位置/声明首发)并弹出提示
        2) 关闭提示浮层 → 封面选"无封面"(免强制上传封面)
        3) 再点"预览并发布" → 该按钮变为"确认发布"
        4) 点"确认发布" → 弹出"作品同步授权" → 点"确定" 完成发布
        """
        self._tap("button:has-text('预览并发布')", "1/4 点击'预览并发布'(展开设置)", 3500)
        self._tap("text=我知道了", "关闭提示浮层", 1200)
        self._tap("text=无封面", "2/4 封面设为'无封面'", 1800)
        self._tap("button:has-text('预览并发布')", "3/4 再次点击进入预览态", 3000)
        ok = self._tap("button:has-text('确认发布')", "4/4 点击'确认发布'", 4000)
        if not ok:
            ok = self._tap("text=确认发布", "4/4 点击'确认发布'", 4000)
        # "作品同步授权"弹窗 → 点"确定"
        self._tap("button:has-text('确定')", "同步授权弹窗-确定", 5000)
        if not ok:
            self.log("未捕获到'确认发布'按钮,请以截图为准")
        elif "发布成功" in self.page.content() or "已发布" in self.page.content():
            self.log("检测到发布成功标志")

    def save_draft(self) -> bool:
        loc = self.first_locator("draft_button")
        if loc:
            loc.click()
            self.page.wait_for_timeout(2500)
            return True
        return False
