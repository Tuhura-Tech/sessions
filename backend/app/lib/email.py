"""Email service using Mailgun API with Jinja2 templating."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.lib.settings import settings

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "email_templates"


@dataclass
class EmailMessage:
    """An email message to be sent."""

    to: list[str]
    subject: str
    html: str
    text: str
    cc: list[str] | None = None
    bcc: list[str] | None = None


class EmailService:
    """Service for sending emails via Mailgun."""

    def __init__(self) -> None:
        self.api_key = settings.mailgun_api_key
        self.domain = settings.mailgun_domain
        self.api_url = settings.mailgun_api_url
        self.from_email = settings.email_from
        self.from_name = settings.email_from_name
        self.dry_run = settings.email_dry_run

        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Log configuration status on initialization
        self._log_configuration()

    def _log_configuration(self) -> None:
        """Log email configuration status for debugging."""
        if self.dry_run:
            logger.info("Email service in DRY_RUN mode - emails will be logged, not sent")
        else:
            if self.api_key and self.domain:
                logger.info(
                    f"Email service configured for Mailgun domain: {self.domain}"
                )
            else:
                logger.warning(
                    "Email service NOT properly configured for production. "
                    "Set EMAIL_DRY_RUN=true to run in dry-run mode, or configure: "
                    "MAILGUN_API_KEY, MAILGUN_DOMAIN, EMAIL_FROM"
                )

    async def render_template(self, template_name: str, **context) -> tuple[str, str]:
        """Render an email template.

        Returns (html_content, text_content) tuple.
        """
        normalized = template_name.replace(".html", "").replace(".txt", "")
        html_template = self.jinja_env.get_template(f"{normalized}.html")
        html_content = html_template.render(**context)

        text_template = self.jinja_env.get_template(f"{normalized}.txt")
        text_content = text_template.render(**context)

        return html_content, text_content

    async def send(self, message: EmailMessage | dict[str, object]) -> bool:
        """Send an email via Mailgun.

        In dry_run mode, logs the email instead of sending.
        Returns True if successful (or dry run), False otherwise.
        Always sends HTML form; text is optional fallback.
        """
        if isinstance(message, dict):
            message_dict = cast(dict[str, Any], message)
            to_value = message_dict.get("to")
            cc_value = message_dict.get("cc")
            bcc_value = message_dict.get("bcc")

            def _as_str_list(value: Any) -> list[str]:
                if isinstance(value, list):
                    return [str(item) for item in value]
                return []

            to_list = _as_str_list(to_value)
            cc_list = _as_str_list(cc_value) or None
            bcc_list = _as_str_list(bcc_value) or None

            message = EmailMessage(
                to=to_list,
                subject=str(message_dict.get("subject") or ""),
                html=str(message_dict.get("html") or ""),
                text=str(message_dict.get("text") or "")
                if message_dict.get("text")
                else "",
                cc=cc_list,
                bcc=bcc_list,
            )

        if self.dry_run:
            logger.info(
                "DRY RUN - Would send email:\n"
                "  To: %s\n"
                "  CC: %s\n"
                "  BCC: %s\n"
                "  Subject: %s\n"
                "\n\n%s",
                message.to,
                message.cc,
                message.bcc,
                message.subject,
                message.html,
            )
            return True

        if not self.api_key or not self.domain:
            logger.error("Mailgun API key or domain not configured")
            return False

        data = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": message.to,
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }

        if message.cc:
            data["cc"] = message.cc

        if message.bcc:
            data["bcc"] = message.bcc

        if settings.email_contact:
            data["h:Reply-To"] = settings.email_contact

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/{self.domain}/messages",
                    auth=("api", self.api_key),
                    data=data,
                )
                response.raise_for_status()
                logger.info(f"Email sent successfully to {message.to}")
                return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Mailgun API error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


# Singleton instance
email_service = EmailService()
