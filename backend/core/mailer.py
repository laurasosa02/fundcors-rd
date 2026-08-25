"""
Shared helper for every outgoing app email (registration/verification,
password reset, admin notifications). Sends each message as both plain
text and an auto-generated HTML alternative (multipart/alternative)
rather than plain-text-only, and never lets a send failure propagate as
an unhandled exception - a notification/verification email failing
should never break the request/response cycle for whatever triggered it.

The HTML alternative isn't cosmetic: a well-formed multipart message is
a real (if modest) spam-filter signal - automated plain-text-only mail
gets treated with more suspicion than the same content sent as a
properly structured HTML+text pair. It won't fix deliverability on its
own (that mostly comes down to sender/domain reputation, which no code
change controls), but it's a real improvement that doesn't depend on
any external service.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

logger = logging.getLogger(__name__)


def _text_to_html(text):
    """Minimal, dependency-free plain-text -> HTML conversion.

    Escapes the text (it may contain user-controlled values, e.g. a
    cedula or nombre) and turns blank-line-separated paragraphs into
    <p> tags, single newlines into <br>, so a multi-paragraph plain-text
    body keeps its original line breaks instead of collapsing onto one
    HTML line.
    """
    paragraphs = text.strip().split("\n\n")
    html_paragraphs = [
        "<p>" + escape(paragraph).replace("\n", "<br>") + "</p>"
        for paragraph in paragraphs
    ]
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        'color:#1a1a1a;line-height:1.6;">' + "".join(html_paragraphs) + "</div>"
    )


def send_notification_email(subject, message, recipient_list, fail_silently=True):
    """Send `message` as both plain text and an HTML alternative.

    Args:
        subject: Email subject line.
        message: Plain-text email body (also the source for the
            auto-generated HTML alternative).
        recipient_list: List of recipient email addresses.
        fail_silently: If True (default), any exception raised while
            sending is caught and logged as a warning rather than
            propagating to the caller.

    Returns:
        The number of successfully delivered messages (0 or 1) on
        success, or None if sending failed and fail_silently is True.
    """
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        email.attach_alternative(_text_to_html(message), "text/html")
        sent = email.send()
        if not sent:
            logger.warning(
                "Email send() returned 0 (subject=%r, recipient_list=%r)",
                subject,
                recipient_list,
            )
        return sent
    except Exception as exc:
        if not fail_silently:
            raise
        logger.warning(
            "Failed to send email (subject=%r, recipient_list=%r): %s",
            subject,
            recipient_list,
            exc,
        )
        return None
