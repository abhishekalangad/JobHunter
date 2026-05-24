"""
SMTP Email Service - Gmail SMTP integration using yagmail
Handles email composition and sending with attachment support
"""
import os
from typing import Optional
from loguru import logger
from app.config import settings


class EmailService:
    """Gmail SMTP email service using yagmail"""

    def __init__(self):
        self._gmail_user = settings.gmail_user
        self._gmail_password = settings.gmail_app_password
        self._from_name = settings.email_from_name

    def _is_configured(self) -> bool:
        """Check if Gmail credentials are configured"""
        return bool(self._gmail_user and self._gmail_password)

    async def send_application_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        resume_path: Optional[str] = None,
        candidate_name: Optional[str] = None
    ) -> bool:
        """
        Send application email via Gmail SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body (plain text or HTML)
            resume_path: Optional path to resume file to attach
            candidate_name: Sender name
        
        Returns:
            True if sent successfully
        """
        if not self._is_configured():
            raise ValueError(
                "Gmail credentials not configured. "
                "Please set GMAIL_USER and GMAIL_APP_PASSWORD in .env file. "
                "Get App Password from: https://myaccount.google.com/apppasswords"
            )

        try:
            import yagmail
            logger.info(f"📧 Sending email to: {to_email}")

            yag = yagmail.SMTP(
                user=self._gmail_user,
                password=self._gmail_password,
                host="smtp.gmail.com",
                port=587,
                smtp_starttls=True,
                smtp_ssl=False
            )

            # Build attachments list
            attachments = []
            if resume_path and os.path.exists(resume_path):
                attachments.append(resume_path)
                logger.info(f"📎 Attaching resume: {os.path.basename(resume_path)}")

            # Send email
            yag.send(
                to=to_email,
                subject=subject,
                contents=[body],
                attachments=attachments if attachments else None
            )

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except ImportError:
            raise ImportError("yagmail not installed. Run: pip install yagmail")
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            raise

    async def test_connection(self) -> dict:
        """Test SMTP connection"""
        if not self._is_configured():
            return {
                "connected": False,
                "error": "Gmail credentials not configured",
                "setup_url": "https://myaccount.google.com/apppasswords"
            }

        try:
            import yagmail
            yag = yagmail.SMTP(
                user=self._gmail_user,
                password=self._gmail_password
            )
            yag.close()
            return {
                "connected": True,
                "email": self._gmail_user
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

    def format_html_email(self, body: str, candidate_name: str = None) -> str:
        """Convert plain text email to basic HTML format"""
        # Convert line breaks to HTML
        html_body = body.replace("\n", "<br>")

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; 
                     color: #333; line-height: 1.6; padding: 20px;">
            {html_body}
        </body>
        </html>
        """


# Singleton instance
email_service = EmailService()
