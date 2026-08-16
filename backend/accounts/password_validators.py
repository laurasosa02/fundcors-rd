"""Custom password complexity validator for FUNDCORSRD.

Django ships MinimumLengthValidator (length only) but no built-in
character-class validator, so this fills the gap: at least one uppercase
letter, one lowercase letter, and one digit. Wired into
AUTH_PASSWORD_VALIDATORS (see config/settings/base.py), which means it's
enforced everywhere Django's own password_validation machinery runs -
the public registration endpoint (accounts/views.py calls
validate_password() directly) and the Django Admin's own user-creation /
change-password forms alike, with a single source of truth.
"""
import re

from django.core.exceptions import ValidationError


class ComplexityValidator:
    UPPERCASE_RE = re.compile(r"[A-Z]")
    LOWERCASE_RE = re.compile(r"[a-z]")
    DIGIT_RE = re.compile(r"[0-9]")

    def validate(self, password, user=None):
        missing = []
        if not self.UPPERCASE_RE.search(password):
            missing.append("una letra mayúscula")
        if not self.LOWERCASE_RE.search(password):
            missing.append("una letra minúscula")
        if not self.DIGIT_RE.search(password):
            missing.append("un número")

        if missing:
            raise ValidationError(
                "La contraseña debe contener al menos " + ", ".join(missing) + ".",
                code="password_no_complexity",
            )

    def get_help_text(self):
        return (
            "Tu contraseña debe contener al menos una letra mayúscula, "
            "una letra minúscula y un número."
        )
