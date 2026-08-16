"""One-click magic-link tokens for account registrations.

Uses Django's built-in `signing` module (no extra dependencies) to produce
signed, timestamped, tamper-proof tokens that can be embedded directly in
admin-notification and applicant-facing email links: admin approve/reject
decisions, and the applicant's own email-verification link.
"""

from django.core import signing

SALT = "fundcorsrd-account-approval"
MAX_AGE = 7 * 24 * 60 * 60  # 7 days, in seconds

VALID_ACTIONS = ("approve", "reject", "verify_email")


def make_approval_token(user_id, action):
    """Build a signed token encoding a (user_id, action) decision.

    `action` must be one of VALID_ACTIONS.
    """
    assert action in VALID_ACTIONS
    return signing.dumps({"user_id": user_id, "action": action}, salt=SALT)


def read_approval_token(token):
    """Decode and verify a token produced by make_approval_token.

    Returns the decoded dict on success, or None if the signature is
    invalid, the token has expired, or it is otherwise malformed.
    """
    try:
        return signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
