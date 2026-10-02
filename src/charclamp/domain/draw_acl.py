"""出炭授权：全应用唯一事实来源。

抽屉是否显示按钮、剪影入口是否放行、保存接口是否接受，三者必须
共用同一个判定，禁止再各写一套（曾经出现过「工人看见按钮、管理员
被挡、接口只认非管理员」的矛盾）。

规则：仅管理员（role == "admin"）可将炭窑标记为「已出炭」。
"""

from __future__ import annotations

ADMIN_ROLE = "admin"


def user_can_draw(user) -> bool:
    """当前账号是否可以出炭：仅管理员。

    抽屉按钮显隐、剪影入口、保存接口都必须调用本函数，
    不允许任何入口再单独按用户名/角色另写判定。
    """
    if user is None:
        return False
    return getattr(user, "role", None) == ADMIN_ROLE
