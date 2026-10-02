"""出炭授权：唯一事实来源。

所有入口（抽屉按钮、剪影按钮、保存接口）必须共用 ``user_can_draw``，
禁止再按用户名/界面位置各写一套判断。
仅管理员（``role == "admin"``）可把炭窑标记为「已出炭」。
"""

from __future__ import annotations

ADMIN_ROLE = "admin"


def user_can_draw(user) -> bool:
    """当前账号是否有权限标记已出炭：仅管理员。"""
    if user is None:
        return False
    return getattr(user, "role", "") == ADMIN_ROLE


# 兼容旧名称：三个入口现在指向同一判断，杜绝结论不一致。
drawer_shows_draw_button = user_can_draw
chip_allows_draw = user_can_draw
api_allows_draw = user_can_draw
