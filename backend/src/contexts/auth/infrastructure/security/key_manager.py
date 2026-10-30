"""JWT 密钥管理

密钥来源优先级（★ 敏感信息一律来自环境变量 / `.env`，禁止入库）：

1. **环境变量 / `.env`**：`JWT_PRIVATE_KEY_PEM`（可选 `JWT_PUBLIC_KEY_PEM`）
   —— 生产环境推荐：容器多副本共享同一份密钥，避免自动生成的密钥彼此不匹配。
2. **运行时文件**：`backend/.keys/jwt_private.pem`（不存在则自动生成 2048-bit RSA / PKCS8 PEM，私钥 chmod 600）。
3. **自动生成**：首次调用 `_ensure_keys()` 时生成并落盘到 `.keys/`。

⚠️ `.keys/` 目录与 `*.pem` 均已在 `.gitignore` 中，禁止提交到 git。
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


def _pem_from_settings() -> tuple[str | None, str | None]:
    """从配置（`.env` / 环境变量）读取 PEM 密钥（支持字面量 `\\n` 换行）。

    ★ `.env` 是单行文本格式，多行 PEM 需写成 ``JWT_PRIVATE_KEY_PEM=-----BEGIN...\\n...``。
      同时兼容真实换行。
    ★ 走 `get_settings()` 而非 `os.environ` —— pydantic-settings 只把 `.env`
      读进 Settings 对象，**不会**写回 `os.environ`。
    """
    try:
        from shared.infrastructure.config.settings import get_settings

        settings = get_settings()
        priv = (settings.JWT_PRIVATE_KEY_PEM or "").strip()
        pub = (settings.JWT_PUBLIC_KEY_PEM or "").strip()
    except Exception:  # noqa: BLE001 — 配置不可用时退回 os.environ
        priv = (os.environ.get("JWT_PRIVATE_KEY_PEM") or "").strip()
        pub = (os.environ.get("JWT_PUBLIC_KEY_PEM") or "").strip()
    if not priv:
        return None, None
    # 字面量 "\n" → 真实换行
    priv = priv.replace("\\n", "\n")
    pub = pub.replace("\\n", "\n")
    return priv, pub or None


def _load_from_env() -> bool:
    """尝试从环境变量 / `.env` 加载密钥；成功返回 True。"""
    global _private_key, _public_key, _kid

    priv_pem, pub_pem = _pem_from_settings()
    if not priv_pem:
        return False
    try:
        _private_key = serialization.load_pem_private_key(
            priv_pem.encode("utf-8"), password=None, backend=default_backend())
        if pub_pem:
            _public_key = serialization.load_pem_public_key(
                pub_pem.encode("utf-8"), backend=default_backend())
        else:
            _public_key = _private_key.public_key()
        _kid = "env"
        return True
    except Exception as e:  # noqa: BLE001 — 配置错误不应让服务起不来，但要明确报错
        raise RuntimeError(
            "JWT_PRIVATE_KEY_PEM / JWT_PUBLIC_KEY_PEM 解析失败，请检查 .env 中的 PEM 格式"
        ) from e


def _ensure_keys() -> None:
    """确保 RSA 密钥对存在;若缺失则生成。"""
    global _private_key, _public_key, _kid

    # ① 优先用环境变量 / .env（生产推荐）
    if _load_from_env():
        return

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