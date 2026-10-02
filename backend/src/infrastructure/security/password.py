"""密码哈希工具

基于 bcrypt(cost=12)。
- hash_password: 返回 ~60 字符 hash
- verify_password: 验证失败返回 False(不抛异常)
"""
from __future__ import annotations

import bcrypt


_BCRYPT_MAX_PASSWORD_BYTES = 72  # bcrypt 的限制


def _truncate(plain: str) -> bytes:
    """bcrypt 仅接受前 72 字节,超长密码截断以避免 ValueError。"""
    encoded = plain.encode("utf-8")
    return encoded[:_BCRYPT_MAX_PASSWORD_BYTES]


def hash_password(plain: str) -> str:
    """生成密码哈希。"""
    return bcrypt.hashpw(_truncate(plain), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码。

    失败一律返回 False,不抛出异常(以避免泄露"用户存在 vs 密码错")。
    """
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False