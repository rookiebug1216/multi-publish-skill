"""58同城发布器(网页端)

支持两条线(由 config/platforms.yaml 的 wuba.line 决定):

1) line=rent(租房线,2025-09 实测)
   cd.58.com/chuzu/ → 免费发布 → zfang.58.com/post/pc/zhengzu?cityId=102
   → 身份弹窗(个人房东) → 表单(#xiaoqu/#shi/#ting/#wei/#mianJi/#jiaGe/...) → 发布

2) line=used_car(二手车线,2026-09 实测;唯一同时支持 图片 + 视频 的线)
   post.58.com/che/102/29/s5 → "普通发布" → 弹窗"普通发布"
   → post.58.com/102/29/s5?kuaipai=true
   → 第1步:城市/联系电话/发布者身份(.squareRadio[name=isBiz][data-value=0]=个人)
      → "开始发布" → 短信验证码(#yzm)
   → 第2步:车辆图片(#imgUpload input[type=file]) + 车辆视频(#upload_zcsp input[type=file])
      + 车况描述(#cheStateIntro) + 结构化车况字段(品牌/车系/上牌时间/里程/价格…)

登录检测: 继承基类 login_check(登录墙优先)
"""
from pathlib import Path

try:
    from .base import BasePlatform
except ImportError:
    from base import BasePlatform


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".m4v", ".mov", ".avi", ".mkv", ".flv", ".wmv"}


class Wuba(BasePlatform):
    name = "wuba"
    display_name = "58同城"

    # ---------- 通用小工具 ----------
    def _click_exact_text(self, text: str, which: str = "first", timeout: int = 8000) -> bool:
        """按精确文案点击元素(避免 text= 子串误命中,如"个人"命中"个人中心")"""
        try:
            loc = self.page.get_by_text(text, exact=True)
            n = loc.count()
            if n == 0:
                return False
            target = loc.first if which == "first" else loc.last
            target.click(timeout=timeout)
            return True
        except Exception as e:
            self.log(f"点击'{text}'({which})失败: {str(e)[:80]}")
            return False

    def _kill_overlays(self):
        """清理 58 推广浮层("推荐前往58微信小程序"等):关闭钮被 img 覆盖,用 JS 直接移除 DOM"""
        for _ in range(3):
            try:
                removed = self.page.evaluate(
                    """() => { let n = 0;
                    const kill = (sel) => document.querySelectorAll(sel).forEach(e => { e.remove(); n++; });
                    kill('.close-wrap-content');
                    kill('[class*="close-wrap"]');
                    const dlg = [...document.querySelectorAll('div,img')].filter(e => {
                        const r = e.getBoundingClientRect();
                        return r.width > 500 && r.height > 250 && (e.textContent || '').includes('58微信小程序');
                    });
                    dlg.forEach(e => {
                        const box = e.closest('[class*="wrap"],[class*="dialog"],[class*="popup"],[class*="mask"]') || e;
                        box.remove(); n++;
                    });
                    return n; }"""
                )
                self.log(f"JS 移除浮层节点: {removed}")
                self.page.wait_for_timeout(600)
                if self.page.locator(".close-wrap-content").count() == 0:
                    break
            except Exception as e:
                self.log(f"浮层清理异常({str(e)[:60]})")
                break

    # ---------- 入口 ----------
    @property
    def line(self) -> str:
        return (self.cfg.get("line") or "rent").strip()

    def open_publisher(self):
        if self.line == "used_car":
            self._open_used_car()
        else:
            self._open_rent()

    def _login_wall_guard(self, back_url: str):
        wall = self.first_locator("login_wall")
        if wall is not None and "passport" in (self.page.url or ""):
            self.log("未登录,跳转登录页...")
            try:
                self.page.goto("https://passport.58.com/login", wait_until="domcontentloaded")
                self.page.wait_for_timeout(4000)
            except Exception:
                pass
            self.wait_human("请在浏览器中完成 58 登录(扫码或短信);成功后继续")
            self.page.goto(back_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)

    # ---------- 租房线 ----------
    def _open_rent(self):
        url = self.entry_url or "https://zfang.58.com/post/pc/zhengzu?cityId=102"
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(5000)
        self._login_wall_guard(url)
        try:
            role = self.page.locator("text=个人房东").first
            if role.count() > 0 and role.is_visible():
                role.click(timeout=5000)
                self.page.wait_for_timeout(800)
                self.page.locator("text=下一步").first.click(timeout=6000)
                self.page.wait_for_timeout(7000)
                self.log("身份已选:个人房东,进入表单")
        except Exception as e:
            self.log(f"身份弹窗未出现或已选过({str(e)[:60]}),继续")

    # ---------- 二手车线 ----------
    def _open_used_car(self):
        url = (self.cfg.get("used_car_entry_url")
               or "https://post.58.com/che/102/29/s5")
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(6000)
        self._login_wall_guard(url)
        # "普通发布"(首屏第1个)→ 弹窗"真的不考虑高价卖车吗?"里的"普通发布"(最后一个)
        if self._click_exact_text("普通发布", "first"):
            self.page.wait_for_timeout(3500)
            self._click_exact_text("普通发布", "last")
            self.page.wait_for_timeout(7000)
        if "post.58.com" not in (self.page.url or ""):
            self.wait_human(f"未能进入 58 二手车发布表单(当前: {self.page.url[:60]});请人工进入后继续")
        self.log(f"已进入二手车发布表单: {self.page.url[:70]}")

    # ---------- 填内容 ----------
    def fill_content(self, content: dict):
        if self.line == "used_car":
            self._fill_used_car(content)
        else:
            self._fill_rent(content)

    # ---- 租房线填表(原实现) ----
    def _fill_rent(self, content: dict):
        """content 约定(platform_overrides.wuba):
          xiaoqu/layout("3/1/1")/area/floor_now/floor_total/price/body/nick_name/phone
        """
        self._kill_overlays()
        w = (content.get("platform_overrides") or {}).get("wuba") or {}
        xiaoqu = w.get("xiaoqu") or ""
        layout = w.get("layout") or ""
        area = str(w.get("area") or "")
        floor_now = str(w.get("floor_now") or "")
        floor_total = str(w.get("floor_total") or "")
        price = str(content.get("price") or w.get("price") or "")
        body = content.get("body") or content.get("description") or ""

        def _fill(selector_id, value, via_keyboard=True):
            if not value:
                return False
            loc = self.page.locator(f"#{selector_id}")
            if loc.count() == 0:
                return False
            try:
                loc.click()
                loc.fill("")
                if via_keyboard:
                    self.page.keyboard.insert_text(str(value))
                else:
                    loc.fill(str(value))
                self.page.wait_for_timeout(400)
                return True
            except Exception as e:
                self.log(f"填充 #{selector_id} 失败: {str(e)[:60]}")
                return False

        filled = []
        if xiaoqu:
            x = self.page.locator("#xiaoqu")
            if x.count() > 0:
                x.click()
                x.fill("")
                self.page.keyboard.insert_text(xiaoqu)
                self.page.wait_for_timeout(2000)
                try:
                    sug = self.page.locator("[class*='sug'] li, [class*='autocomplete'] li, [id*='sug'] li").first
                    if sug.count() > 0 and sug.is_visible():
                        sug.click()
                        self.page.wait_for_timeout(800)
                        filled.append("xiaoqu(联想)")
                    else:
                        filled.append("xiaoqu(无联想,保留输入)")
                except Exception:
                    filled.append("xiaoqu(输入)")
        if "/" in layout:
            shi, ting, wei = (layout.split("/") + ["", ""])[:3]
            if _fill("shi", shi, via_keyboard=False):
                filled.append("shi")
            if _fill("ting", ting, via_keyboard=False):
                filled.append("ting")
            if _fill("wei", wei, via_keyboard=False):
                filled.append("wei")
        if _fill("mianJi", area):
            filled.append("mianJi")
        if _fill("suoZaiLouCeng", floor_now, via_keyboard=False):
            filled.append("suoZaiLouCeng")
        if _fill("zongLouCeng", floor_total, via_keyboard=False):
            filled.append("zongLouCeng")
        if _fill("jiaGe", price):
            filled.append("jiaGe")
        if body:
            d = self.page.locator("#fangyuanxiangqing")
            if d.count() > 0:
                d.click()
                self.page.keyboard.insert_text(f"{content.get('title','')}。\n{body}")
                self.page.wait_for_timeout(500)
                filled.append("fangyuanxiangqing")
        if _fill("nickName", w.get("nick_name") or "", via_keyboard=False):
            filled.append("nickName")
        if _fill("phone", w.get("phone") or "", via_keyboard=False):
            filled.append("phone")
        self.log(f"已填充字段: {', '.join(filled) if filled else '无(内容文件未提供 wuba 专属字段)'}")

        media = content.get("media_files") or []
        if media:
            try:
                channel = self._upload([str(Path(m).resolve()) for m in media])
                self.log(f"已上传 {len(media)} 个文件(通道:{channel})")
                self.page.wait_for_timeout(5000)
            except Exception as e:
                self.log(f"图片上传异常({e}),跳过(可在浏览器手动补)")

        if not filled and not media:
            self.wait_human("58 租房表单未能自动填充(字段可能改版),请人工填写后继续")

    # ---- 二手车线填表 ----
    def _fill_used_car(self, content: dict):
        """第1步(城市/电话/身份/短信) → 第2步(图片+视频+车况描述)。

        短信验证码必须人工:content.platform_overrides.wuba.sms_code 可预填;
        未提供则 wait_human 等人工输码并进入第2步。
        """
        self._kill_overlays()
        w = (content.get("platform_overrides") or {}).get("wuba") or {}

        # --- 第1步:发布者身份 = 个人 ---
        try:
            radio = self.page.locator('.squareRadio_wrap[name="isBiz"] .squareRadio[data-value="0"]')
            if radio.count() > 0:
                radio.first.click(timeout=5000)
                self.page.wait_for_timeout(800)
                self.log("已选择发布者身份:个人")
        except Exception as e:
            self.log(f"选择身份失败({str(e)[:60]}),尝试继续")

        # 联系电话(已登录通常自动带出)
        phone = str(w.get("phone") or "")
        if phone:
            try:
                p = self.page.locator("#Phone")
                if p.count() > 0:
                    p.click()
                    p.fill("")
                    p.fill(phone)
                    self.page.wait_for_timeout(400)
                    self.log(f"已填联系电话: {phone}")
            except Exception as e:
                self.log(f"填联系电话失败({str(e)[:60]})")

        # --- 点击"开始发布" → 触发短信验证码 ---
        if self._click_exact_text("开始发布", "first"):
            self.page.wait_for_timeout(4000)
            self.log("已点击'开始发布'")

        sms_code = str(w.get("sms_code") or "")
        yzm = self.page.locator("#yzm")
        yzm_visible = yzm.count() > 0 and yzm.first.is_visible()
        if yzm_visible:
            if sms_code:
                try:
                    yzm.first.click()
                    yzm.first.fill(sms_code)
                    self.page.wait_for_timeout(600)
                    self.log("已填入短信验证码(来自内容文件)")
                    self._click_exact_text("开始发布", "first")
                    self.page.wait_for_timeout(6000)
                except Exception as e:
                    self.log(f"填验证码失败({str(e)[:60]}),转人工")
                    self.wait_human("58 短信验证码需人工:请输入验证码并点击'开始发布'进入'填写信息'页;完成后继续")
            else:
                self.wait_human(
                    "58 二手车发布需要短信验证码:请在浏览器中获取并输入验证码、点击'开始发布',"
                    "进入'填写信息'页后继续"
                )
        # 等待进入第2步(车辆图片/车况描述出现)
        try:
            self.page.wait_for_selector("#cheStateIntro", state="visible", timeout=20000)
            self.log("已进入第2步:填写信息")
        except Exception:
            self.log("未检测到第2步表单(可能仍在验证码页),继续尝试填充")

        # --- 第2步:图片 + 视频 + 车况描述 ---
        media = [str(Path(m).resolve()) for m in (content.get("media_files") or [])]
        images = [m for m in media if Path(m).suffix.lower() in IMAGE_EXT]
        videos = [m for m in media if Path(m).suffix.lower() in VIDEO_EXT]

        if images:
            try:
                up = self.page.locator("#imgUpload input[type=file]").first
                up.set_input_files(images)
                self.log(f"已上传车辆图片 {len(images)} 张")
                self.page.wait_for_timeout(8000)
            except Exception as e:
                self.log(f"车辆图片上传异常({str(e)[:80]}),请人工补传")
        if videos:
            try:
                up = self.page.locator("#upload_zcsp input[type=file], .localVideoUpLoad input[type=file]").first
                up.set_input_files(videos)
                self.log(f"已上传车辆视频 {len(videos)} 个")
                self.page.wait_for_timeout(10000)
            except Exception as e:
                self.log(f"车辆视频上传异常({str(e)[:80]}),请人工补传")

        body = content.get("body") or content.get("description") or ""
        if body:
            try:
                d = self.page.locator("#cheStateIntro")
                if d.count() > 0:
                    d.first.click()
                    self.page.keyboard.insert_text(body[:300])
                    self.page.wait_for_timeout(600)
                    self.log("已填车况描述")
            except Exception as e:
                self.log(f"填车况描述失败({str(e)[:60]})")

        # 结构化车况字段(品牌/车系/上牌时间/里程/价格区间…)无法完全自动化 → 人工补齐
        self.wait_human(
            "58 二手车表单已完成:图片/视频/车况描述。请在浏览器中补齐必填车况字段"
            "(品牌、车系、车型、上牌时间、排放标准、行驶里程、出售价格等),确认无误后继续"
        )

    # ---------- 提交 ----------
    def submit(self, mode: str):
        btn = self.first_locator("publish_button")
        if not btn:
            raise RuntimeError("未找到发布按钮")
        btn.click()
        self.page.wait_for_timeout(3000)
