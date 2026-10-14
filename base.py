"""平台基类转发层（兼容旧导入路径）。

真实实现位于 publisher/base.py。本文件仅做 re-export,不再维护重复代码。
历史副本与正式实现曾发生漂移:旧副本缺 login_check 通用实现、缺 Windows GBK
控制台 UTF-8 兜底、confirm_publish 缺异常保护,子类继承它会直接 NotImplementedError。

统一导入方式:
    from publisher.base import BasePlatform
"""
from publisher.base import (  # noqa: F401
    BasePlatform,
    HumanIntervention,
    now_str,
)

__all__ = ["BasePlatform", "HumanIntervention", "now_str"]
