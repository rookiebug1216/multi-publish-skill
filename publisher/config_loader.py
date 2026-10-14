"""Release-skill 五平台自动发文 · 配置加载"""
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # 兜底:提示安装
    yaml = None

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_ROOT / "config"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    if yaml is None:
        raise RuntimeError("缺少 PyYAML,请先: pip install pyyaml (或 pip install -r requirements.txt)")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


class Settings:
    """全局设置(config/settings.yaml)"""

    def __init__(self, data: dict):
        self.raw = data or {}
        browser = self.raw.get("browser") or {}
        self.browser_channel = browser.get("channel") or "msedge"   # msedge / chrome
        self.headless = False                    # 硬约束:恒为有头,无配置项可改
        self.profile_dir = browser.get("profile_dir") or "browser-profile"
        self.cdp_url = browser.get("cdp_url") or ""
        self.default_timeout_ms = int(browser.get("default_timeout_ms") or 30000)
        self.slowmo_ms = int(browser.get("slowmo_ms") or 300)
        self.start_maximized = bool(browser.get("start_maximized", True))

        inter = self.raw.get("interaction") or {}
        self.human_wait_seconds = int(inter.get("human_wait_seconds") or 900)
        self.auto_submit_default = str(inter.get("auto_submit_default") or "ask").lower()

        paths = self.raw.get("paths") or {}
        self.ledger_dir = paths.get("ledger_dir") or "ledger"
        self.verification_dir = paths.get("verification_dir") or "verification"


def load_settings() -> Settings:
    return Settings(_load_yaml(CONFIG_DIR / "settings.yaml"))


def _platforms_root(all_platforms: dict) -> dict:
    """兼容两种结构: platforms: 下嵌套,或顶层直接平铺平台名"""
    if not all_platforms:
        return {}
    if isinstance(all_platforms.get("platforms"), dict):
        return all_platforms["platforms"]
    return {k: v for k, v in all_platforms.items()
            if isinstance(v, dict) and not k.startswith("_")}


def load_platform(name: str) -> dict:
    """读取平台配置:优先 config/platforms/<name>.yaml,回退 platforms.yaml"""
    single = CONFIG_DIR / "platforms" / f"{name}.yaml"
    if single.exists():
        data = _load_yaml(single)
        if data:
            data.setdefault("name", name)
            return data
    node = _platforms_root(_load_yaml(CONFIG_DIR / "platforms.yaml")).get(name)
    if node:
        node.setdefault("name", name)
        return node
    raise FileNotFoundError(f"平台配置缺失: {single} 或 platforms.yaml 中无 {name}")


def list_platforms() -> list:
    sub = CONFIG_DIR / "platforms"
    names = sorted(p.stem for p in sub.glob("*.yaml")) if sub.exists() else []
    if not names:
        names = sorted(_platforms_root(_load_yaml(CONFIG_DIR / "platforms.yaml")).keys())
    return names
