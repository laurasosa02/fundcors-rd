import json
import logging
import secrets
import ssl
import string
import urllib.parse
import urllib.request

import certifi
from django_ratelimit.decorators import ratelimit

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import User
from .tokens import make_approval_token, read_approval_token

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

# Built once and reused for every siteverify call. Uses certifi's CA
# bundle explicitly rather than relying on the interpreter's own default
# (some Python installs, e.g. python.org's macOS builds, don't ship a
# working system CA bundle out of the box, which would otherwise make
# every registration fail with an SSL certificate verification error).
_RECAPTCHA_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

logger = logging.getLogger(__name__)

REGISTRATION_REQUIRED_FIELDS = [
    "nombre",
    "cedula",
    "telefono",
    "email",
    "password",
    "password_confirm",
]


def _parse_json_body(request):
    """Parse the request body as JSON.

    Returns (data, error_response). On success error_response is None and
    data is the decoded JSON. On failure data is None and error_response
    is a ready-to-return 400 JsonResponse.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"message": "JSON inválido"}, status=400)
    if not isinstance(data, dict):
        data = {}
    return data, None


def _validate_registration(data):
    """Validate the register_view payload, collecting every problem found.

    Returns a dict shaped like {field: [message, ...]}, empty if valid.
    """
    errors = {}

    def add_error(field, message):
        errors.setdefault(field, []).append(message)

    for field in REGISTRATION_REQUIRED_FIELDS:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            add_error(field, "Este campo es obligatorio.")

    email = data.get("email")
    if isinstance(email, str) and email.strip() and "@" not in email:
        add_error("email", "El correo electrónico no es válido.")

    password = data.get("password")
    if isinstance(password, str) and password:
        # Delegates to whatever's configured in AUTH_PASSWORD_VALIDATORS
        # (see config/settings/base.py): minimum length, complexity
        # (upper/lower/digit), common-password and all-numeric checks -
        # one source of truth shared with the Django Admin's own
        # password forms, instead of duplicating the rules here.
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            for message in exc.messages:
                add_error("password", message)

    password_confirm = data.get("password_confirm")
    if password != password_confirm:
        add_error("password_confirm", "Las contraseñas no coinciden.")

    # Only bother checking uniqueness once the email has passed the basic
    # shape checks above.
    if "email" not in errors and isinstance(email, str) and email.strip():
        if User.objects.filter(email=email.strip()).exists():
            add_error("email", "Ya existe una cuenta con este correo electrónico.")

    return errors


def _verify_recaptcha(token, remote_ip):
    """Verifies a reCAPTCHA v2 response token against Google's siteverify
    endpoint, so automated registration submissions can't reach the
    database at all (as opposed to only being flagged after the fact).

    Fails closed: any missing secret key, missing/empty token, network
    error, or a "success": false response from Google is treated as a
    failed verification.
    """
    secret = settings.RECAPTCHA_SECRET_KEY
    if not secret:
        logger.warning(
            "RECAPTCHA_SECRET_KEY is not configured - rejecting registration "
            "until it is set."
        )
        return False
    if not token or not isinstance(token, str):
        return False

    try:
        payload = urllib.parse.urlencode(
            {"secret": secret, "response": token, "remoteip": remote_ip or ""}
        ).encode()
        request_obj = urllib.request.Request(RECAPTCHA_VERIFY_URL, data=payload, method="POST")
        with urllib.request.urlopen(
            request_obj, timeout=8, context=_RECAPTCHA_SSL_CONTEXT
        ) as response:
            result = json.loads(response.read().decode())
        return bool(result.get("success"))
    except Exception as exc:  # noqa: BLE001 - any failure here must fail closed
        logger.warning("reCAPTCHA verification request failed: %s", exc)
        return False


def _send_admin_registration_email(user):
    """Informational only - registration no longer waits on any admin
    decision, the account activates automatically once the applicant
    verifies their email (see verify_email_view). This is just an FYI so
    the foundation's staff knows a new agrimensor signed up; there is
    nothing for them to click or approve here. An admin who does need to
    deactivate a problematic account can still do so from
    /django-admin/ (the "Rechazar usuarios seleccionados" action).
    """
    message = (
        "Nuevo registro en el portal de FUNDCORSRD (se activa "
        "automáticamente al verificar el correo, sin necesitar "
        "aprobación).\n\n"
        f"Nombre: {user.get_full_name() or user.username}\n"
        f"Cédula: {user.cedula}\n"
        f"Teléfono: {user.telefono}\n"
        f"Correo: {user.email}\n"
    )

    # Registration must succeed even if email delivery fails, so this is
    # fail_silently. If it does fail, log it rather than swallowing it
    # without a trace.
    sent = send_mail(
        subject="Nuevo registro - FUNDCORSRD",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_NOTIFY_EMAIL],
        fail_silently=True,
    )
    if not sent:
        logger.warning(
            "Failed to send admin registration-notification email for user id=%s email=%s",
            user.id,
            user.email,
        )


def _send_verification_email(request, user):
    """Sent immediately on registration. Confirms the applicant actually
    controls the email address they registered with - clicking the link
    is what activates the account (see verify_email_view), there is no
    separate admin-approval step.
    """
    token = make_approval_token(user.id, "verify_email")
    verify_url = request.build_absolute_uri(f"/auth/verify-email/?token={token}")

    sent = send_mail(
        subject="Verifica tu correo electrónico - FUNDCORSRD",
        message=(
            f"Hola {user.get_full_name() or user.username},\n\n"
            "Gracias por registrarte en el portal de FUNDCORSRD. Antes de "
            "poder iniciar sesión necesitamos confirmar que esta dirección "
            "de correo es tuya.\n\n"
            f"Verificar mi correo: {verify_url}\n\n"
            "Si no solicitaste este registro, puedes ignorar este mensaje.\n\n"
            "FUNDCORSRD"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    if not sent:
        logger.warning(
            "Failed to send verification email for user id=%s email=%s",
            user.id,
            user.email,
        )


def _generate_temp_password(length=12):
    """Cryptographically secure random password (uses `secrets`, never the
    non-cryptographic `random` module) guaranteed to contain at least one
    uppercase letter, one lowercase letter, and one digit, so it also
    satisfies this project's own AUTH_PASSWORD_VALIDATORS complexity rule.
    """
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    pool = string.ascii_uppercase + string.ascii_lowercase + string.digits
    remaining = [secrets.choice(pool) for _ in range(length - len(required))]

    password_chars = required + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _send_temp_password_email(user, new_password):
    sent = send_mail(
        subject="Tu nueva contraseña temporal - FUNDCORSRD",
        message=(
            f"Hola {user.get_full_name() or user.username},\n\n"
            "Solicitaste recuperar el acceso a tu cuenta en el portal de "
            "FUNDCORSRD. Esta es tu nueva contraseña temporal:\n\n"
            f"    {new_password}\n\n"
            "Inicia sesión con ella y, por tu seguridad, cámbiala por una "
            "de tu preferencia lo antes posible.\n\n"
            "Si no solicitaste este cambio, contacta a FUNDCORSRD de "
            "inmediato.\n\n"
            "FUNDCORSRD"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    if not sent:
        logger.warning(
            "Failed to send temporary-password email for user id=%s email=%s",
            user.id,
            user.email,
        )


@require_GET
def csrf_view(request):
    token = get_token(request)
    return JsonResponse({"csrfToken": token})


@require_POST
def register_view(request):
    data, error_response = _parse_json_body(request)
    if error_response is not None:
        return error_response

    errors = _validate_registration(data)

    # Checked regardless of the other field errors above, so a bot (or a
    # human who forgot the checkbox) sees the captcha problem in the same
    # response rather than needing a second round-trip to discover it.
    if not _verify_recaptcha(data.get("recaptcha_token"), request.META.get("REMOTE_ADDR")):
        errors.setdefault("recaptcha_token", []).append(
            "Verificación de seguridad fallida. Intenta de nuevo."
        )

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    nombre = data["nombre"].strip()
    cedula = data["cedula"].strip()
    telefono = data["telefono"].strip()
    email = data["email"].strip()
    password = data["password"]

    name_parts = nombre.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            cedula=cedula,
            telefono=telefono,
            status=User.Status.PENDING,
        )
    except IntegrityError:
        return JsonResponse(
            {
                "errors": {
                    "email": ["Ya existe una cuenta con este correo electrónico."]
                }
            },
            status=400,
        )

    _send_admin_registration_email(user)
    _send_verification_email(request, user)

    return JsonResponse(
        {"message": "Solicitud de registro recibida"}, status=201
    )


@require_POST
def login_view(request):
    data, error_response = _parse_json_body(request)
    if error_response is not None:
        return error_response

    email = data.get("email", "")
    password = data.get("password", "")

    user = authenticate(request, username=email, password=password)

    if user is None:
        return JsonResponse({"message": "Credenciales inválidas"}, status=401)

    if user.email_verified_at is None:
        return JsonResponse(
            {
                "message": (
                    "Debes verificar tu correo electrónico antes de iniciar "
                    "sesión. Revisa tu bandeja de entrada."
                ),
                "status": "unverified",
            },
            status=403,
        )

    if user.status == User.Status.PENDING:
        # Defensive fallback, not expected in the normal flow: status
        # auto-transitions to APPROVED the moment email_verified_at is
        # set (see verify_email_view), so by the time email_verified_at
        # is not None above, status should already be APPROVED or
        # REJECTED - this only fires if an admin manually reset a
        # verified user's status back to pending from /django-admin/.
        return JsonResponse(
            {
                "message": "Tu cuenta no está activa. Contacta a FUNDCORSRD para más información.",
                "status": "pending",
            },
            status=403,
        )

    if user.status == User.Status.REJECTED:
        return JsonResponse(
            {
                "message": (
                    "Tu solicitud de registro fue rechazada. Contacta a "
                    "FUNDCORSRD para más información."
                ),
                "status": "rejected",
            },
            status=403,
        )

    login(request, user)
    return JsonResponse(
        {"status": "approved", "nombre": user.get_full_name() or user.username}
    )


_FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "Si el correo está registrado, te enviamos una contraseña temporal. "
    "Revisa tu bandeja de entrada."
)


@require_POST
@ratelimit(key="ip", rate="5/h", method="POST", block=False)
def forgot_password_view(request):
    """Generates and emails a brand-new random password for the account
    matching the submitted email, replacing the old one - see the
    project notes for why this mails a fresh password rather than a
    reset link: simpler to build, and the client's explicit choice.

    Always returns the same generic message whether or not the email
    is actually registered - a different response per case would let
    an attacker enumerate real accounts one guess at a time.
    """
    if getattr(request, "limited", False):
        return JsonResponse(
            {"message": "Demasiados intentos. Intenta más tarde."}, status=429
        )

    data, error_response = _parse_json_body(request)
    if error_response is not None:
        return error_response

    email = data.get("email")
    if not isinstance(email, str) or not email.strip():
        return JsonResponse(
            {"errors": {"email": ["Este campo es obligatorio."]}}, status=400
        )

    user = User.objects.filter(email=email.strip()).first()
    if user is not None:
        new_password = _generate_temp_password()
        user.set_password(new_password)
        user.save(update_fields=["password"])
        _send_temp_password_email(user, new_password)

    return JsonResponse({"message": _FORGOT_PASSWORD_GENERIC_MESSAGE})


@require_POST
def change_password_view(request):
    """Lets a logged-in user set their own password - the natural
    follow-up to forgot_password_view, which can only ever hand out a
    random temporary one. Requires the current password (so a session
    left open on a shared/unlocked device can't be used to permanently
    lock the real owner out) and re-runs the same complexity rules as
    registration via validate_password.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Debes iniciar sesión."}, status=401)

    data, error_response = _parse_json_body(request)
    if error_response is not None:
        return error_response

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    new_password_confirm = data.get("new_password_confirm", "")

    errors = {}

    if not request.user.check_password(current_password):
        errors.setdefault("current_password", []).append(
            "La contraseña actual no es correcta."
        )

    if isinstance(new_password, str) and new_password:
        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            for message in exc.messages:
                errors.setdefault("new_password", []).append(message)
    else:
        errors.setdefault("new_password", []).append("Este campo es obligatorio.")

    if new_password != new_password_confirm:
        errors.setdefault("new_password_confirm", []).append(
            "Las contraseñas no coinciden."
        )

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    # Without this, changing the password invalidates the session auth
    # hash Django stamped into the current session, silently logging the
    # user out on their very next request even though the change itself
    # succeeded - this keeps the current session valid while still
    # invalidating any *other* session logged in as this user, which is
    # the correct/expected behavior for a password change.
    update_session_auth_hash(request, request.user)

    return JsonResponse({"message": "Contraseña actualizada correctamente."})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"message": "Sesión cerrada"})


@require_GET
def me_view(request):
    if request.user.is_authenticated:
        return JsonResponse(
            {
                "authenticated": True,
                "status": request.user.status,
                "nombre": request.user.get_full_name() or request.user.username,
            }
        )
    return JsonResponse({"authenticated": False, "status": None, "nombre": None})


def _invalid_link_response():
    return HttpResponse(
        "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
        "<body><p>Enlace inválido o expirado</p></body></html>",
        status=400,
        content_type="text/html; charset=utf-8",
    )


def _user_not_found_response():
    return HttpResponse(
        "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
        "<body><p>Usuario no encontrado</p></body></html>",
        status=404,
        content_type="text/html; charset=utf-8",
    )


def _confirm_form_response(request, token, question_html):
    """Renders a GET-safe confirmation page with a POST form.

    Used by one-click email links that mutate state (currently just
    email verification): the actual mutation never happens on a bare
    GET - mail clients, antivirus link-scanners, and chat/webmail
    link-unfurlers routinely prefetch every URL found in an email body,
    which would otherwise silently trigger the mutation before a human
    ever looks at it. Callers are responsible for HTML-escaping any
    user-controlled values in question_html.
    """
    csrf_token = get_token(request)
    return HttpResponse(
        "<!doctype html><html><head><meta charset=\"utf-8\"></head><body>"
        f"<p>{question_html}</p>"
        f'<form method="post">'
        f'<input type="hidden" name="csrfmiddlewaretoken" value="{escape(csrf_token)}">'
        f'<input type="hidden" name="token" value="{escape(token)}">'
        f'<button type="submit">Confirmar</button>'
        f"</form>"
        "</body></html>",
        content_type="text/html; charset=utf-8",
    )


@require_http_methods(["GET", "POST"])
def verify_email_view(request):
    """Clicking this link is the ONLY thing that activates an account -
    there is no separate admin-approval step. The POST branch marks the
    email verified and, in the same action, approves the account
    (unless it was already explicitly rejected by an admin - a stale
    verification link must never resurrect a banned account).
    """
    token = request.GET.get("token", "") if request.method == "GET" else request.POST.get("token", "")
    payload = read_approval_token(token)
    if payload is None or payload.get("action") != "verify_email":
        return _invalid_link_response()

    user = User.objects.filter(pk=payload.get("user_id")).first()
    if user is None:
        return _user_not_found_response()

    if request.method == "GET":
        question = f"¿Confirmar que <strong>{escape(user.email)}</strong> es tu correo electrónico?"
        return _confirm_form_response(request, token, question)

    update_fields = []
    if user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        update_fields.append("email_verified_at")
    if user.status != User.Status.REJECTED and user.status != User.Status.APPROVED:
        user.status = User.Status.APPROVED
        update_fields.append("status")
    if update_fields:
        user.save(update_fields=update_fields)

    if user.status == User.Status.REJECTED:
        activation_message = (
            "Tu correo quedó verificado, pero esta cuenta fue desactivada. "
            "Contacta a FUNDCORSRD para más información."
        )
    else:
        activation_message = "Tu cuenta ya está activa. Ya puedes iniciar sesión."

    return HttpResponse(
        "<!doctype html><html><head><meta charset=\"utf-8\"></head><body>"
        f"<p>Correo verificado para <strong>{escape(user.email)}</strong>. "
        f"{activation_message}</p>"
        "</body></html>",
        content_type="text/html; charset=utf-8",
    )
