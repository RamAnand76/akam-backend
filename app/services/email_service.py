import asyncio
import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class EmailSender(Protocol):
    async def send_otp(self, to: str, code: str, ttl_minutes: int) -> None: ...


def _body(code: str, ttl_minutes: int) -> str:
    return f"Your Akam sign-in code is {code}. It expires in {ttl_minutes} minutes. If you did not request it, ignore this email."


class ConsoleSender:
    """Development only: logs the code instead of sending it."""

    async def send_otp(self, to: str, code: str, ttl_minutes: int) -> None:
        logger.info("otp_console_email", to=to, code=code)


class SmtpSender:
    async def send_otp(self, to: str, code: str, ttl_minutes: int) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.EMAIL_FROM, to, "Your Akam sign-in code"
        msg.set_content(_body(code, ttl_minutes))

        def _send() -> None:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
                s.starttls()
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)

        await asyncio.to_thread(_send)


class ResendSender:
    async def send_otp(self, to: str, code: str, ttl_minutes: int) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={"from": settings.EMAIL_FROM, "to": [to], "subject": "Your Akam sign-in code", "text": _body(code, ttl_minutes)},
            )
            r.raise_for_status()


def get_email_sender() -> EmailSender:
    return {"console": ConsoleSender, "smtp": SmtpSender, "resend": ResendSender}[settings.EMAIL_BACKEND]()
