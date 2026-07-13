import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.sender_email = settings.smtp_sender_email
        self.recipient_email = settings.cart_notification_email
        self.app_password = (settings.google_app_password or "").replace(" ", "")

    def is_configured(self) -> bool:
        return bool(self.sender_email and self.recipient_email and self.app_password)

    def send_cart_notification(
        self,
        *,
        user_name: str,
        user_email: str,
        product_name: str,
        quantity: int,
        variant_name: str | None = None,
        unit_price: str | None = None,
        is_new_item: bool = True,
    ) -> None:
        if not self.is_configured():
            logger.warning("Cart email skipped: SMTP settings are not configured")
            return

        action = "added to cart" if is_new_item else "updated in cart"
        variant_line = f"Variant: {variant_name}\n" if variant_name else ""
        price_line = f"Unit price: {unit_price}\n" if unit_price else ""

        body = (
            f"A product was {action}.\n\n"
            f"Customer: {user_name}\n"
            f"Email: {user_email}\n"
            f"Product: {product_name}\n"
            f"{variant_line}"
            f"Quantity: {quantity}\n"
            f"{price_line}"
        )

        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = self.recipient_email
        message["Subject"] = f"Cart update: {product_name}"
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            logger.info("Cart notification email sent to %s", self.recipient_email)
        except Exception:
            logger.exception("Failed to send cart notification email")
