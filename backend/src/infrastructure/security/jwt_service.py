"""JWT 令牌签发 / 解码

使用 RS256 非对称算法,公钥可对外暴露（前端无需校验签名,故无影响）。
- access_token 有效期 15 分钟
- refresh_token 有效期 7 天

refresh_token 走"rotation"机制：每次 refresh 都撤销旧 jti 并签发新一对。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import jwt

from infrastructure.security.key_manager import get_kid, get_private_key, get_public_key


ACCESS_TOKEN_EXPIRE_SECONDS = 15 * 60           # 15 分钟
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 天

ALGORITHM = "RS256"
ISSUER = "attribution-analysis"
AUDIENCE = "attribution-analysis-api"

TokenType = Literal["access", "refresh"]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(
    *,
    user_id: int,
    email: str,
    roles: list[str],
    permissions: list[str],
    expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS,
) -> tuple[str, datetime]:
    """签发 access token。返回 (token, expires_at)。"""
    now = _now()
    expires_at = now.fromtimestamp(now.timestamp() + expires_in, tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
        "email": email,
        "roles": roles,
        "permissions": permissions,
        "type": "access",
    }
    headers = {"kid": get_kid(), "typ": "JWT", "alg": ALGORITHM}
    token = jwt.encode(payload, get_private_key(), algorithm=ALGORITHM, headers=headers)
    return token, expires_at


def create_refresh_token(
    *,
    user_id: int,
    expires_in: int = REFRESH_TOKEN_EXPIRE_SECONDS,
) -> tuple[str, str, datetime]:
    """签发 refresh token。返回 (token, jti, expires_at)。"""
    now = _now()
    expires_at = now.fromtimestamp(now.timestamp() + expires_in, tz=timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
        "type": "refresh",
    }
    headers = {"kid": get_kid(), "typ": "JWT", "alg": ALGORITHM}
    token = jwt.encode(payload, get_private_key(), algorithm=ALGORITHM, headers=headers)
    return token, jti, expires_at


def decode_token(token: str, *, expected_type: TokenType = "access") -> dict[str, Any]:
    """解码并验证 JWT,返回 claims 字典。

    抛出:
    - jwt.ExpiredSignatureError: 过期
    - jwt.InvalidTokenError: 其他无效情况（签名错误 / 类型不符 / 受众不符...）
    """
    payload = jwt.decode(
        token,
        get_public_key(),
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
        options={"require": ["exp", "iat", "sub", "jti", "type"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"token type mismatch: expected={expected_type}, got={payload.get('type')}"
        )
    return payload