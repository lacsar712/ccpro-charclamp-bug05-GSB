"""炭窑焖烧志业务规则。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from charclamp.domain.models import BurnShift, Clamp

MIN_PEAK_TEMP_FOR_DRAWN = 400.0


class RuleError(ValueError):
    """业务规则校验失败。"""


def latest_shift_for_clamp(clamp: Clamp) -> BurnShift | None:
    if not clamp.shifts:
        return None
    return max(clamp.shifts, key=lambda s: s.started_at)


def can_mark_clamp_drawn(clamp: Clamp) -> tuple[bool, str]:
    """
    炭窑转为「已出炭」(drawn) 的前提：
    最近一条焖烧班次的峰值温度已记录，且 >= 400℃。
    """
    latest = latest_shift_for_clamp(clamp)
    if latest is None:
        return False, "该窑尚无焖烧班次，不能标记为已出炭"
    if latest.peak_temp_c is None:
        return False, "最近班次尚未记录峰值温度，不能标记为已出炭"
    if latest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
        return (
            False,
            f"最近班次峰值温度 {latest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭",
        )
    return True, ""


def assert_can_set_clamp_status(clamp: Clamp, new_status: str) -> None:
    allowed = {Clamp.STATUS_STACKED, Clamp.STATUS_BURNING, Clamp.STATUS_DRAWN}
    if new_status not in allowed:
        raise RuleError(f"无效状态：{new_status}")
    if new_status == Clamp.STATUS_DRAWN:
        ok, msg = can_mark_clamp_drawn(clamp)
        if not ok:
            raise RuleError(msg)


async def mark_clamp_drawn(db: AsyncSession, clamp_id: int) -> Clamp:
    """把炭窑标记为「已出炭」的唯一写入口，并发安全。

    调用方必须先完成管理员授权（``draw_acl.user_can_draw``）。

    并发保证：
    - ``SELECT ... FOR UPDATE`` 锁住该窑行，同一窑的并发请求被串行化，
      因此至多一笔请求实际写入 drawn；
    - 峰值温度规则在持锁后重新读取复检，避免「先读后写」窗口；
    - 已是 drawn 时再次请求明确拒绝（不重复成功），使并发提交里至多一笔成功。
    """
    clamp = (
        await db.execute(select(Clamp).where(Clamp.id == clamp_id).with_for_update())
    ).scalar_one_or_none()
    if clamp is None:
        raise RuleError("炭窑不存在")

    if clamp.status == Clamp.STATUS_DRAWN:
        raise RuleError("该窑已出炭，无需重复标记")

    latest = (
        await db.execute(
            select(BurnShift)
            .where(BurnShift.clamp_id == clamp_id)
            .order_by(BurnShift.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        raise RuleError("该窑尚无焖烧班次，不能标记为已出炭")
    if latest.peak_temp_c is None:
        raise RuleError("最近班次尚未记录峰值温度，不能标记为已出炭")
    if latest.peak_temp_c < MIN_PEAK_TEMP_FOR_DRAWN:
        raise RuleError(
            f"最近班次峰值温度 {latest.peak_temp_c}℃ 低于 {MIN_PEAK_TEMP_FOR_DRAWN:.0f}℃，不能标记为已出炭"
        )

    clamp.status = Clamp.STATUS_DRAWN
    await db.flush()
    return clamp
