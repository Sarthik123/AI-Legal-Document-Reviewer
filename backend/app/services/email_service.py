import os
import json
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from email.policy import SMTP

from dotenv import load_dotenv


load_dotenv()


class EmailDeliveryError(RuntimeError):
    pass


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")


def send_email(recipient: str, subject: str, body: str) -> None:
    if os.getenv("EMAIL_PROVIDER", "smtp").strip().lower() == "brevo_api":
        api_key = os.getenv("BREVO_API_KEY", "").strip()
        sender = os.getenv("BREVO_FROM_EMAIL", "").strip()
        sender_name = os.getenv("BREVO_FROM_NAME", "AI Legal Reviewer").strip()
        if not api_key or not sender:
            raise EmailDeliveryError("Brevo API email delivery is not configured.")
        request = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps({
                "sender": {"email": sender, "name": sender_name},
                "to": [{"email": recipient}],
                "subject": subject,
                "textContent": body,
            }).encode("utf-8"),
            headers={"accept": "application/json", "api-key": api_key, "content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20):
                return
        except OSError as error:
            raise EmailDeliveryError("Brevo API could not send the message.") from error

    host = os.getenv("SMTP_HOST", "smtp-relay.brevo.com").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip()
    security = os.getenv("SMTP_SECURITY", "starttls").strip().lower()

    if (
        not host
        or not sender
        or bool(username) != bool(password)
    ):
        raise EmailDeliveryError(
            "Email delivery is not configured. Set SMTP_FROM and, when "
            "required by the provider, both SMTP_USERNAME and SMTP_PASSWORD."
        )

    if security not in {"starttls", "ssl", "none"}:
        raise EmailDeliveryError(
            "SMTP_SECURITY must be starttls, ssl, or none."
        )

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as error:
        raise EmailDeliveryError("SMTP_PORT must be a valid port number.") from error

    message = EmailMessage(policy=SMTP.clone(max_line_length=998))
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(
                host,
                port,
                timeout=20,
                context=ssl.create_default_context(),
            ) as client:
                if username:
                    client.login(username, password)
                client.send_message(message)
            return

        with smtplib.SMTP(host, port, timeout=20) as client:
            client.ehlo()

            if security == "starttls":
                client.starttls(context=ssl.create_default_context())
                client.ehlo()

            if username:
                client.login(username, password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("The email provider could not send the message.") from error
