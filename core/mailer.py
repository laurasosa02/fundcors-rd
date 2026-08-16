"""
Tiny wrapper around Django's send_mail that never lets an email failure
propagate as an unhandled exception. If sending fails for any reason
(bad SMTP credentials, network hiccup, etc.), the error is logged as a
warning instead of raising, so a notification email failing does not
break the request/response cycle for whatever triggered it.

Not wired into any app's views yet -- available for future use so
callers don't each reinvent this same try/except.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_notification_email(subject, message, recipient_list, fail_silently=True):
    """Send an email from DEFAULT_FROM_EMAIL, logging (not raising) on failure.

    Args:
        subject: Email subject line.
        message: Plain-text email body.
        recipient_list: List of recipient email addresses.
        fail_silently: If True (default), any exception raised while
            sending is caught and logged as a warning rather than
            propagating to the caller.

    Returns:
        The return value of django.core.mail.send_mail on success, or
        None if sending failed and fail_silently is True.
    """
    try:
        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
        )
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
