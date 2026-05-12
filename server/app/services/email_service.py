import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.SMTP_HOST and self.settings.SMTP_USER and self.settings.SMTP_PASSWORD)

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
    ) -> bool:
        if not self.is_configured:
            logger.warning("SMTP not configured, skipping email notification")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.settings.SMTP_FROM
            msg["To"] = to_email
            msg["Subject"] = f"[XHS365] {subject}"

            msg.attach(MIMEText(content, "plain", "utf-8"))

            if html_content:
                msg.attach(MIMEText(html_content, "html", "utf-8"))
            else:
                html = self._build_html(subject, content)
                msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
                server.sendmail(self.settings.SMTP_FROM, [to_email], msg.as_string())

            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

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
        return await self.send_notification_email(to_email, subject, content)

    def _build_html(self, subject: str, content: str) -> str:
        lines = content.split("\n")
        body_html = ""
        for line in lines:
            if line.strip():
                if line.startswith("规则名称") or line.startswith("商品名称") or line.startswith("触发详情"):
                    key, value = line.split("：", 1)
                    body_html += f'<p><strong>{key}：</strong>{value}</p>'
                else:
                    body_html += f'<p>{line}</p>'
            else:
                body_html += "<br>"

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
  <div style="background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <div style="border-bottom: 3px solid #ff2442; padding-bottom: 15px; margin-bottom: 20px;">
      <h1 style="color: #ff2442; font-size: 20px; margin: 0;">XHS365 监控提醒</h1>
    </div>
    <div style="color: #333; font-size: 14px; line-height: 1.8;">
      {body_html}
    </div>
    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee;
                color: #999; font-size: 12px; text-align: center;">
      此邮件由 XHS365 系统自动发送，请勿回复。
    </div>
  </div>
</body>
</html>"""


email_service = EmailService()
