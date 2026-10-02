from __future__ import annotations

from litestar.connection import ASGIConnection
from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.security.session_auth import SessionAuth
from sqlalchemy import select

from charclamp.domain.models import User
from charclamp.infra.db import SessionLocal


async def retrieve_user_handler(session: dict, connection: ASGIConnection) -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()


session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    session_backend_config=ServerSideSessionConfig(
        session_id_bytes=32,
    ),
    # 注意：exclude 按前缀匹配，绝不能放 "/"，否则所有路由都被跳过鉴权。
    # 时间轴等页面的未登录跳转由各处理器自行 Redirect("/login")，
    # 未放行页面则由 SessionAuth 抛 401，经 main.py 异常处理统一跳登录。
    exclude=["/login", "/logout", "/static", "/schema", "/favicon.ico"],
)
