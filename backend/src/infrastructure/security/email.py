"""SMTP 邮件发送工具

- 使用标准库 smtplib + email.mime,同步发送,FastAPI 路由内通过 asyncio.to_thread 包裹
- SMTP_PORT=465 → SMTP_SSL;否则 STARTTLS
- 发件人 / 收件人 / 主题 / HTML 模板均可自定义

不在此处做限流 / 验证码存储;限流与存储由 EmailVerificationService 负责。
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from infrastructure.config.settings import get_settings


logger = logging.getLogger(__name__)


def _build_message(
    to_email: str, subject: str, html_body: str
) -> MIMEMultipart:
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def _smtp_send_blocking(to_email: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_USERNAME / SMTP_PASSWORD 未配置,无法发送邮件。"
            "请在 backend/.env 中配置后重启服务。"
        )

    msg = _build_message(to_email, subject, html_body)

    if settings.SMTP_PORT == 465 or settings.SMTP_USE_SSL:
        server: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            context=ssl.create_default_context(),
            timeout=30,
        )
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()

    try:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:  # noqa: BLE001
            pass


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """异步发送一封邮件。失败抛 RuntimeError(供上层捕获后回滚验证码)。"""
    try:
        await asyncio.to_thread(_smtp_send_blocking, to_email, subject, html_body)
    except Exception as e:  # noqa: BLE001
        logger.exception("邮件发送失败: to=%s subject=%s", to_email, subject)
        raise RuntimeError(f"邮件发送失败: {e}") from e


def build_verification_code_email(
    code: str,
    expire_minutes: int,
    purpose_label: str = "注册",
) -> tuple[str, str]:
    """构造验证码邮件的 (subject, html_body)。"""
    settings = get_settings()
    subject = f"{settings.SMTP_SUBJECT_PREFIX} {purpose_label}验证码"
    html_body = f"""
    <div style="font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
                max-width: 480px; margin: 32px auto; padding: 24px;
                background: #ffffff; border-radius: 12px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08); color: #1e293b;">
      <h2 style="margin: 0 0 16px; font-size: 18px;">{purpose_label}验证码</h2>
      <p style="margin: 0 0 8px; color: #64748b; font-size: 14px;">您的验证码是:</p>
      <div style="font-size: 32px; font-weight: 800; letter-spacing: 6px;
                  color: #2563eb; margin: 16px 0;">{code}</div>
      <p style="margin: 16px 0 0; color: #64748b; font-size: 13px;">
        有效期 {expire_minutes} 分钟,请勿泄露给他人。如非本人操作,请忽略本邮件。
      </p>
    </div>
    """
    return subject, html_body
