"""炭窑状态变更的应用服务：把授权与并发收敛到同一事务。

出炭只有这一条写路径，剪影入口与抽屉表单都走它，杜绝
「藏了按钮但接口仍放行」「两套授权结论不一致」。

并发安全：先做角色授权（操作工立即中文拒绝），再对炭窑行加
``SELECT ... FOR UPDATE`` 行锁并复核当前状态。两个管理员同时
对同一窑出炭时，后一个拿到锁后会读到前一个已提交的 drawn
状态而被拒绝，因此至多一笔成功。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from charclamp.domain.draw_acl import user_can_draw
from charclamp.domain.models import Clamp
from charclamp.domain.rules import RuleError, assert_can_set_clamp_status

DRAW_FORBIDDEN_MSG = "仅管理员可标记已出炭，当前账号无权操作"
ALREADY_DRAWN_MSG = "该窑已标记为已出炭，无需重复操作"
CLAMP_NOT_FOUND_MSG = "未找到该炭窑"


async def mark_clamp_drawn(db: AsyncSession, user, clamp_id: int) -> Clamp:
    """在调用方事务内把炭窑标记为已出炭，成功后由调用方 commit。

    任何失败都抛 RuleError（中文），且不修改状态；调用方应回滚。
    """
    # 1) 授权先行：操作工必拒，与按钮显隐无关、与并发无关。
    if not user_can_draw(user):
        raise RuleError(DRAW_FORBIDDEN_MSG)

    # 2) 锁住该窑这一行，串行化同窑的并发出炭。
    result = await db.execute(
        select(Clamp)
        .where(Clamp.id == clamp_id)
        .with_for_update()
        .options(selectinload(Clamp.shifts))
    )
    clamp = result.scalar_one_or_none()
    if clamp is None:
        raise RuleError(CLAMP_NOT_FOUND_MSG)

    # 3) 拿到锁后复核状态：别人已提交出炭则拒绝，保证至多一笔成功。
    if clamp.status == Clamp.STATUS_DRAWN:
        raise RuleError(ALREADY_DRAWN_MSG)

    # 4) 业务前提（最近班次峰值温度达标等）。
    assert_can_set_clamp_status(clamp, Clamp.STATUS_DRAWN)

    clamp.status = Clamp.STATUS_DRAWN
    return clamp
