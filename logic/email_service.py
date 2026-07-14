"""
AcaDesk Email Service
======================
Sends HTML alert emails via SMTP with automatic retry.

Configuration (set via OS environment variables or .env file):
    SMTP_SERVER    — SMTP host (default: smtp.gmail.com)
    SMTP_PORT      — SMTP port (default: 587)
    SMTP_EMAIL     — Sender address
    SMTP_PASSWORD  — Sender app password

Behavior:
    - If SMTP_EMAIL and SMTP_PASSWORD are configured → sends REAL emails.
    - If SMTP credentials are absent → falls back to mock mode with a
      prominent WARNING log. Mock mode never marks alerts as sent.

Security:
    - SMTP password is NEVER logged.
    - Recipient addresses are logged only at DEBUG level.
"""

import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logic.logger import get_logger

_log = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # seconds between retries


class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.sender_email = os.environ.get("SMTP_EMAIL", "")
        self.sender_password = os.environ.get("SMTP_PASSWORD", "")
        self._is_configured = bool(self.sender_email and self.sender_password)

        if not self._is_configured:
            _log.warning(
                "SMTP credentials not configured (SMTP_EMAIL / SMTP_PASSWORD env vars are missing). "
                "Email alerts will be MOCKED — no real emails will be sent. "
                "Set these environment variables to enable real delivery."
            )

    def _build_message(self, to_list: list[str], subject: str, html_content: str) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AcaDesk Alerts <{self.sender_email or 'noreply@acadesk.local'}>"
        msg["To"] = ", ".join(to_list)
        msg.attach(MIMEText(html_content, "html"))
        return msg

    def _send_via_smtp(self, msg: MIMEMultipart, to_list: list[str]) -> bool:
        """Attempt SMTP delivery with retries. Returns True only on confirmed delivery."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, to_list, msg.as_string())
                _log.info(f"Email delivered successfully to {len(to_list)} recipient(s) (attempt {attempt})")
                return True
            except smtplib.SMTPAuthenticationError:
                _log.error(
                    "SMTP authentication failed. Verify SMTP_EMAIL and SMTP_PASSWORD. "
                    "For Gmail, use an App Password, not your account password."
                )
                return False  # No retry on auth failure — it won't work
            except (smtplib.SMTPException, OSError) as e:
                _log.warning(f"Email delivery attempt {attempt}/{_MAX_RETRIES} failed: {type(e).__name__}")
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)
        _log.error(f"Email delivery failed after {_MAX_RETRIES} attempts. Alert NOT marked as sent.")
        return False

    def _mock_send(self, to_list: list[str], subject: str) -> None:
        """Log the email details in mock mode. Never returns True to callers."""
        _log.warning(
            f"[MOCK EMAIL] Subject: '{subject}' | Recipients: {len(to_list)} | "
            "Configure SMTP_EMAIL and SMTP_PASSWORD to send real emails."
        )

    def send_early_warning_alert(
        self,
        to_emails,
        student_name: str,
        student_id: str,
        college_name: str,
        risk_level: str,
        dominant_factor: str,
    ) -> bool:
        """
        Send an HTML early warning alert email.
        Returns True ONLY if the email was actually delivered.
        Returns False in mock mode — callers must NOT mark alerts as sent.
        """
        # Guard: reject empty or None inputs immediately
        if not to_emails:
            _log.warning("send_early_warning_alert called with empty to_emails list")
            return False
        # Normalise recipient list
        if isinstance(to_emails, str):
            to_emails = [to_emails]
        to_list = [e.strip() for e in to_emails if e and str(e).strip()]
        if not to_list:
            _log.warning("send_early_warning_alert: no valid email addresses after filtering.")
            return False

        subject = f"URGENT: Academic Early Warning Alert for {student_name}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #E53935; text-align: center;">Academic Early Warning Alert</h2>
                    <p>Dear Student / Parent,</p>
                    <p>This is an automated notification from the <b>AcaDesk AI Monitoring System</b> at {college_name}.</p>

                    <p>The academic risk profile for <b>{student_name} ({student_id})</b> has changed to:
                    <strong style="color: #E53935;">{risk_level} Risk</strong>.</p>

                    <div style="background-color: #fce4e4; padding: 15px; border-left: 5px solid #E53935; margin: 20px 0;">
                        <p style="margin: 0;"><b>Primary Area of Concern:</b> {dominant_factor}</p>
                    </div>

                    <p>Our predictive systems indicate that without immediate intervention, there is a significant
                    risk to the student's degree progression or academic standing.</p>

                    <p><b>Required Action:</b></p>
                    <ul>
                        <li>Please contact your assigned Faculty Mentor or the Head of Department immediately.</li>
                        <li>Log into the student portal to review current attendance and academic standings.</li>
                    </ul>

                    <p>Early intervention is the key to student success. We are here to support you!</p>

                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #888; text-align: center;">
                        This is an automated message generated by the AcaDesk Intervention Engine.
                        Please do not reply directly to this email.
                    </p>
                </div>
            </body>
        </html>
        """

        msg = self._build_message(to_list, subject, html_content)

        if self._is_configured:
            return self._send_via_smtp(msg, to_list)
        else:
            self._mock_send(to_list, subject)
            return False  # Mock mode never returns True
