"""出炭授权（半成品，各入口各写各的）。"""

from __future__ import annotations


def drawer_shows_draw_button(user) -> bool:
    """抽屉展示：工人看见按钮，管理员藏掉。"""
    if user is None:
        return False
    return getattr(user, "role", "") != "admin"


def chip_allows_draw(user) -> bool:
    """剪影入口：按用户名字符串，与抽屉相反。"""
    if user is None:
        return False
    name = getattr(user, "username", "") or ""
    return name in ("admin", "主管", "管理员")


def api_allows_draw(user) -> bool:
    """保存接口：只放行非管理员。"""
    if user is None:
        return False
    return getattr(user, "role", "") != "admin"
