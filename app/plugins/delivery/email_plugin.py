"""
app/plugins/delivery/email_plugin.py

Email delivery plugin - sends alert notifications via Gmail SMTP.
Used the same SMTP credentials already configured in docker-compose on Node 4

Required env vars:
    SMTP_HOST - e.g. smtp.gmail.com
    SMTP_PORT - e.g. 587
    SMTP_USER - e.g. MarketPulse.Alerts.Grafana@gmail.com
    SMTP_PASSWPRD - Gmail app password
    SMTP_FROM - display sender address (usually same as SMTP_USER)
"""

from __future__ import annotations

import smtplib
import ssl
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.plugins.delivery.base import AlertDeliveryPlugin, AlertPayload, DeliveryResult


class EmailDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "email"
    feature_flag = "delivery.email"

    async def deliver(self, alert: AlertPayload, recipient: str) -> DeliveryResult:
        try:
            msg = self._build_message(alert, recipient)
            self._send(msg, recipient)
            return DeliveryResult(
                success=True,
                channel=self.channel_name,
                delivered_at=datetime.now(UTC),
            )
        except Exception as exc:  # noqa: BLE001
            return DeliveryResult(
                success=False,
                channel=self.channel_name,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        """Verify SMTP credentials are accepted without sending anything."""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            return True
        except Exception:  # noqa: BLE001
            return False

    # helpers
    def _build_message(self, alert: AlertPayload, recipient: str) -> MIMEMultipart:
        severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴"}.get(alert.severity, "📢")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{severity_emoji} [MarketPulse] {alert.title}"
        msg["From"] = settings.SMTP_FROM
        msg["To"] = recipient

        plain = (
            f"{alert.body}\n\n"
            f"Symbol:       {alert.symbol or 'N/A'}\n"
            f"Severity:     {alert.severity.upper()}\n"
            f"Triggered At: {alert.triggered_at.isoformat()}\n"
        )
        msg.attach(MIMEText(plain, "plain"))
        return msg

    def _send(self, msg: MIMEMultipart, recipient: str) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, recipient, msg.as_string())
