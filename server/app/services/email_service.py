import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._worker_task: asyncio.Task | None = None
        self._is_running = False

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.SMTP_HOST and self.settings.SMTP_USER and self.settings.SMTP_PASSWORD)

    def start_worker(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Email worker started")

    async def stop_worker(self) -> None:
        self._is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        remaining = self._queue.qsize()
        if remaining > 0:
            logger.warning(f"Email worker stopped with {remaining} emails in queue")

    async def _worker_loop(self) -> None:
        while self._is_running:
            try:
                email_data = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await self._send_email_sync(
                    to_email=email_data["to"],
                    subject=email_data["subject"],
                    plain_content=email_data["plain"],
                    html_content=email_data.get("html"),
                )
            except Exception as e:
                logger.error(f"Email worker send error: {e}")
            finally:
                self._queue.task_done()

    async def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        plain_content: str,
        html_content: str | None = None,
    ) -> bool:
        if not self.is_configured:
            logger.warning("SMTP not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.settings.SMTP_FROM
            msg["To"] = to_email
            msg["Subject"] = f"[XHS365] {subject}"

            msg.attach(MIMEText(plain_content, "plain", "utf-8"))

            if html_content:
                msg.attach(MIMEText(html_content, "html", "utf-8"))
            else:
                html = self._build_html(subject, plain_content)
                msg.attach(MIMEText(html, "html", "utf-8"))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._smtp_send, msg, to_email)

            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _smtp_send(self, msg: MIMEMultipart, to_email: str) -> None:
        with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
            if self.settings.SMTP_USE_TLS:
                server.starttls()
            server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
            server.sendmail(self.settings.SMTP_FROM, [to_email], msg.as_string())

    async def enqueue(
        self,
        to_email: str,
        subject: str,
        plain_content: str,
        html_content: str | None = None,
    ) -> bool:
        if not self.is_configured:
            return False
        try:
            self._queue.put_nowait({
                "to": to_email,
                "subject": subject,
                "plain": plain_content,
                "html": html_content,
            })
            return True
        except asyncio.QueueFull:
            logger.error("Email queue full, dropping email")
            return False

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: str | None = None,
    ) -> bool:
        return await self._send_email_sync(to_email, subject, content, html_content)

    async def send_monitor_triggered_email(
        self,
        to_email: str,
        rule_name: str,
        product_name: str,
        trigger_detail: str,
    ) -> bool:
        subject = f"监控提醒：{product_name}"
        content = (
            f"您设置的商品监控规则已触发：\n\n"
            f"规则名称：{rule_name}\n"
            f"商品名称：{product_name}\n"
            f"触发详情：{trigger_detail}\n\n"
            f"请登录 XHS365 查看详情。"
        )
        return await self.enqueue(to_email, subject, content)

    async def send_welcome_email(self, to_email: str, nickname: str) -> bool:
        subject = "欢迎加入 XHS365"
        content = (
            f"亲爱的 {nickname}：\n\n"
            f"欢迎加入 XHS365！您现在可以开始使用商品监控、AI分析等核心功能。\n\n"
            f"快速开始：\n"
            f"1. 添加您想监控的商品\n"
            f"2. 设置监控规则和告警条件\n"
            f"3. 使用AI分析获取市场洞察\n\n"
            f"如有任何问题，请随时联系我们的客服团队。"
        )
        html = self._build_template_email(
            title="欢迎加入 XHS365",
            greeting=f"亲爱的 {nickname}：",
            body="""
            <p>欢迎加入 XHS365！您现在可以开始使用商品监控、AI分析等核心功能。</p>
            <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 15px 0;">
                <h3 style="margin: 0 0 10px 0; color: #333;">快速开始</h3>
                <ol style="margin: 0; padding-left: 20px; line-height: 2;">
                    <li>添加您想监控的商品</li>
                    <li>设置监控规则和告警条件</li>
                    <li>使用AI分析获取市场洞察</li>
                </ol>
            </div>
            """,
        )
        return await self.enqueue(to_email, subject, content, html)

    async def send_password_change_email(self, to_email: str) -> bool:
        subject = "密码修改通知"
        content = (
            "您的账户密码已成功修改。\n\n"
            "如果这不是您本人的操作，请立即联系客服并修改密码。"
        )
        html = self._build_template_email(
            title="密码修改通知",
            greeting="您好：",
            body="""
            <p>您的账户密码已成功修改。</p>
            <p style="color: #e6a23c; font-weight: bold;">⚠️ 如果这不是您本人的操作，请立即联系客服并修改密码。</p>
            """,
        )
        return await self.enqueue(to_email, subject, content, html)

    async def send_plan_upgrade_email(self, to_email: str, plan_name: str, expires_at: str | None = None) -> bool:
        subject = f"套餐升级通知 - {plan_name}"
        expire_info = f"，有效期至 {expires_at}" if expires_at else ""
        content = (
            f"恭喜！您的套餐已升级为 {plan_name}{expire_info}。\n\n"
            f"您现在可以使用更多高级功能，包括更多AI分析次数、更快的采集速度等。"
        )
        html = self._build_template_email(
            title="套餐升级通知",
            greeting="恭喜！",
            body=f"""
            <p>您的套餐已升级为 <strong style="color: #ff2442;">{plan_name}</strong>{expire_info}。</p>
            <p>您现在可以使用更多高级功能，包括更多AI分析次数、更快的采集速度等。</p>
            """,
        )
        return await self.enqueue(to_email, subject, content, html)

    def _build_html(self, subject: str, content: str) -> str:
        lines = content.split("\n")
        body_html = ""
        for line in lines:
            if line.strip():
                body_html += f"<p>{line}</p>"
            else:
                body_html += "<br>"

        return self._build_template_email(subject, "您好：", body_html)

    def _build_template_email(self, title: str, greeting: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <div style="border-bottom: 3px solid #ff2442; padding-bottom: 15px; margin-bottom: 20px;">
      <h1 style="color: #ff2442; font-size: 20px; margin: 0;">{title}</h1>
    </div>
    <div style="color: #333; font-size: 14px; line-height: 1.8;">
      <p>{greeting}</p>
      {body}
    </div>
    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee;
                color: #999; font-size: 12px; text-align: center;">
      此邮件由 XHS365 系统自动发送，请勿回复。
    </div>
  </div>
</body>
</html>"""


email_service = EmailService()
