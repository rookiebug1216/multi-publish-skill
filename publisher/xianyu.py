"""闲鱼(咸鱼)网页端发布器

入口: https://www.goofish.com/ → 登录后"发布闲置"
发布入口(直链): https://www.goofish.com/publish (以实际页面为准,配置可改)
登录检测: 继承基类 login_check(登录墙优先)
"""
import time
from pathlib import Path

try:
    from .base import BasePlatform
except ImportError:
    from base import BasePlatform


class Xianyu(BasePlatform):
    name = "xianyu"
    display_name = "闲鱼"

    # 自动识别出的默认分类(如"软件/程序/网站开发")在网页端不可发布,
    # 需改选网页版支持的分类。按顺序尝试,首个不再出现"网页版暂不支持"提示的即采用。
    CATEGORY_CANDIDATES = ("其他闲置", "AI编程工具/服务", "AI办公工具/服务")
    UNSUPPORTED_HINT = "网页版暂不支持"

    def open_publisher(self):
        # 若入口页不是直接编辑器,点击"发布"按钮进入
        btn = self.first_locator("publish_entry")
        if btn:
            try:
                btn.click()
                self.page.wait_for_timeout(3000)
            except Exception as e:
                self.log(f"点击发布入口失败({e}),假定已在编辑页")

    def fill_content(self, content: dict):
        title = content.get("title") or ""
        desc = content.get("description") or content.get("body") or ""
        price = content.get("price") or ""

        # 新版 goofish 表单无独立标题框:标题拼进描述首行
        if title:
            t = self.first_locator("title_input")
            if t:
                t.click()
                t.type(title, delay=60)
        if desc:
            full = (title + "\n" + desc).strip() if title else desc
            d = self.first_locator("desc_editor")
            if d:
                d.click()
                d.type(full, delay=40)
            else:
                self.log("未找到描述输入框")
        if price:
            # 闲鱼价格框无 placeholder 关键字,是 ant-input + placeholder="0.00"(第一个=价格)
            p = None
            for sel in ("input.ant-input[placeholder='0.00']", "input[placeholder='0.00']",
                        "input[placeholder*='价格']"):
                try:
                    loc = self.page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        p = loc
                        break
                except Exception:
                    continue
            if p is not None:
                p.click()
                p.type(str(price), delay=40)
                self.log(f"已填价格: {price}")
            else:
                self.log("未找到价格输入框")

        # 分类:自动识别的分类网页端可能不支持发布,需手动改选
        picked = self._select_category(content.get("category") or "")
        if picked:
            self.log(f"已确认可用分类: {picked}")
        elif self._category_unsupported():
            self.log("警告:当前分类网页版不支持,请人工在页面改选分类后继续")

        # 闲鱼 web 发闲置只接受图片(accept=image/*),视频文件会被拒("文件类型无法确定")
        media = content.get("media_files") or []
        images = [m for m in media if Path(m).suffix.lower() in
                  {".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".bmp"}]
        skipped = [m for m in media if m not in images]
        if skipped:
            self.log(f"跳过 {len(skipped)} 个非图片文件(闲鱼 web 端不支持视频): "
                     f"{', '.join(Path(s).name for s in skipped)}")
        if images:
            try:
                channel = self._upload(images)
                self.log(f"已上传 {len(images)} 张图(通道:{channel})")
                self.page.wait_for_timeout(5000)
            except Exception as e:
                self.log(f"图片上传异常({e}),改用人工介入")
                self.wait_human("请手动上传图片后继续")

    # ---------- 分类 ----------
    def _category_unsupported(self) -> bool:
        """页面上是否出现"网页版暂不支持发布此分类"提示"""
        try:
            return self.UNSUPPORTED_HINT in (self.page.inner_text("body") or "")
        except Exception:
            return False

    def _open_category_dropdown(self) -> bool:
        """点开"分类"下拉(antd Select)。

        注意:JS 的 element.click() 不会触发 antd 展开,必须用 Playwright 真实鼠标点击。
        """
        cands = (
            ".ant-form-item:has(.ant-form-item-label:has-text('分类')) .ant-select-selector",
            ".ant-form-item:has(.ant-form-item-label:has-text('分类')) .ant-select-selection-item",
            "#category .ant-select-selector",
        )
        for sel in cands:
            try:
                loc = self.page.locator(sel).first
                if loc.count() == 0 or not loc.is_visible():
                    continue
                loc.click()
                self.page.wait_for_timeout(1500)
                if self.page.locator(".ant-select-item-option").count() > 0:
                    return True
            except Exception:
                continue
        return False

    def _pick_category(self, name: str) -> bool:
        """在已展开的下拉中选中指定分类"""
        if not self._open_category_dropdown():
            self.log("未找到分类下拉")
            return False
        for sel in (f".ant-select-item-option[title='{name}']",
                    f".ant-select-item-option:has-text('{name}')"):
            try:
                loc = self.page.locator(sel).first
                if loc.count() == 0 or not loc.is_visible():
                    continue
                loc.click()
                self.page.wait_for_timeout(2000)
                return True
            except Exception:
                continue
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(500)
        return False

    def _select_category(self, preferred: str = "") -> str:
        """改选网页版可用的分类,返回最终采用值(失败返回空串)"""
        if not self._category_unsupported() and not preferred:
            self.log("分类未提示不支持,保持默认")
            return ""
        cands = [c for c in ([preferred] + list(self.CATEGORY_CANDIDATES)) if c]
        seen = []
        for name in cands:
            if name in seen:
                continue
            seen.append(name)
            if not self._pick_category(name):
                continue
            if not self._category_unsupported():
                return name
            self.log(f"分类'{name}'网页端仍不支持,尝试下一个")
        return ""

    def submit(self, mode: str):
        """点击底部"发布";精确文案避免误命中侧边栏"发闲置"等。"""
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
            self.log("已点击'发布'")
        else:
            # JS 兜底:闲鱼"发布"可能是 div/span,精确文案且可见的最内层元素
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
        self.page.wait_for_timeout(5000)
        # 二次确认弹窗(部分账号会弹"确认发布")
        for sel in ("button:has-text('确认发布')", "button:has-text('确定')"):
            try:
                b = self.page.locator(sel).first
                if b.count() > 0 and b.is_visible():
                    b.click()
                    self.log(f"二次确认: {sel}")
                    self.page.wait_for_timeout(4000)
                    break
            except Exception:
                continue
