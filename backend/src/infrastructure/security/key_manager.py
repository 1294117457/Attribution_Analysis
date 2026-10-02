"""JWT 密钥管理

启动时若 `backend/.keys/` 不存在或缺少 RSA 密钥对,首次调用即自动生成
(2048-bit RSA / PKCS8 PEM),私钥 `chmod 600`。

密钥存放在仓库外的运行时目录,不提交到 git（见 backend/.gitignore）。
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


# 密钥目录：backend/.keys/（在 main.py 启动时由 main.py 锁定为绝对路径）
_KEY_DIR = Path(__file__).resolve().parents[3] / ".keys"
JWT_PRIVATE_KEY_PATH = _KEY_DIR / "jwt_private.pem"
JWT_PUBLIC_KEY_PATH = _KEY_DIR / "jwt_public.pem"

_private_key: rsa.RSAPrivateKey | None = None
_public_key: rsa.RSAPublicKey | None = None
_kid: str | None = None


def _ensure_keys() -> None:
    """确保 RSA 密钥对存在;若缺失则生成。"""
    global _private_key, _public_key, _kid

    _KEY_DIR.mkdir(parents=True, exist_ok=True)

    if JWT_PRIVATE_KEY_PATH.exists() and JWT_PUBLIC_KEY_PATH.exists():
        _private_key = serialization.load_pem_private_key(
            JWT_PRIVATE_KEY_PATH.read_bytes(),
            password=None,
            backend=default_backend(),
        )
        _public_key = serialization.load_pem_public_key(
            JWT_PUBLIC_KEY_PATH.read_bytes(),
            backend=default_backend(),
        )
        _kid = str(int(JWT_PRIVATE_KEY_PATH.stat().st_mtime))
        return

    # 首次启动生成密钥
    priv = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    pub = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    JWT_PRIVATE_KEY_PATH.write_bytes(priv_pem)
    JWT_PUBLIC_KEY_PATH.write_bytes(pub_pem)

    # 仅 Linux/macOS 支持 chmod;Windows 静默忽略
    try:
        os.chmod(JWT_PRIVATE_KEY_PATH, 0o600)
    except OSError:
        pass

    _private_key = priv
    _public_key = pub
    _kid = str(int(time.time()))


def get_private_key() -> rsa.RSAPrivateKey:
    """获取 RSA 私钥（用于签发 access / refresh token）。"""
    if _private_key is None:
        _ensure_keys()
    return _private_key  # type: ignore[return-value]


def get_public_key() -> rsa.RSAPublicKey:
    """获取 RSA 公钥（用于验签）。"""
    if _public_key is None:
        _ensure_keys()
    return _public_key  # type: ignore[return-value]


def get_kid() -> str:
    """密钥 ID（kid claim 的值,用于 JWT 头）。"""
    if _kid is None:
        _ensure_keys()
    return _kid  # type: ignore[return-value]


def warmup() -> None:
    """在 lifespan 启动时调用一次,提前生成密钥,避免第一次请求时阻塞。"""
    _ensure_keys()