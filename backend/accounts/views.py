import json
import logging
import ssl
import urllib.parse
import urllib.request

import certifi

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
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
        return None, JsonResponse({"message": "JSON invalido"}, status=400)
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
        add_error("email", "El correo electronico no es valido.")

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
        add_error("password_confirm", "Las contrasenas no coinciden.")

    # Only bother checking uniqueness once the email has passed the basic
    # shape checks above.
    if "email" not in errors and isinstance(email, str) and email.strip():
        if User.objects.filter(email=email.strip()).exists():
            add_error("email", "Ya existe una cuenta con este correo electronico.")

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


def _send_admin_registration_email(request, user):
    approve_token = make_approval_token(user.id, "approve")
    reject_token = make_approval_token(user.id, "reject")
    approve_url = request.build_absolute_uri(
        f"/auth/magic-approve/?token={approve_token}"
    )
    reject_url = request.build_absolute_uri(
        f"/auth/magic-reject/?token={reject_token}"
    )

    message = (
        "Nueva solicitud de registro en el portal de FUNDCORSRD.\n\n"
        f"Nombre: {user.get_full_name() or user.username}\n"
        f"Cedula: {user.cedula}\n"
        f"Telefono: {user.telefono}\n"
        f"Correo: {user.email}\n\n"
        f"Aprobar: {approve_url}\n"
        f"Rechazar: {reject_url}\n"
    )

    # Registration must succeed even if email delivery fails, so this is
    # fail_silently. If it does fail, log it rather than swallowing it
    # without a trace.
    sent = send_mail(
        subject="Nueva solicitud de registro - FUNDCORSRD",
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


def _send_approval_notification_email(user):
    """Applicant-facing "your account was approved" email.

    Content mirrors the notification sent by the approve_users admin
    action.
    """
    sent = send_mail(
        subject="Tu cuenta de FUNDCORSRD ha sido aprobada",
        message=(
            f"Hola {user.get_full_name() or user.username},\n\n"
            "Tu cuenta en el portal de FUNDCORSRD ha sido aprobada. "
            "Ya puedes iniciar sesion.\n\n"
            "FUNDCORSRD"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    if not sent:
        logger.warning(
            "Failed to send approval-notification email for user id=%s email=%s",
            user.id,
            user.email,
        )


def _send_verification_email(request, user):
    """Sent immediately on registration - separate from and in addition to
    the admin-approval flow. Confirms the applicant actually controls the
    email address they registered with, independent of whether an admin
    has reviewed the account yet.
    """
    token = make_approval_token(user.id, "verify_email")
    verify_url = request.build_absolute_uri(f"/auth/verify-email/?token={token}")

    sent = send_mail(
        subject="Verifica tu correo electronico - FUNDCORSRD",
        message=(
            f"Hola {user.get_full_name() or user.username},\n\n"
            "Gracias por registrarte en el portal de FUNDCORSRD. Antes de "
            "poder iniciar sesion necesitamos confirmar que esta direccion "
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
            "Verificacion de seguridad fallida. Intenta de nuevo."
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
                    "email": ["Ya existe una cuenta con este correo electronico."]
                }
            },
            status=400,
        )

    _send_admin_registration_email(request, user)
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
        return JsonResponse({"message": "Credenciales invalidas"}, status=401)

    if user.email_verified_at is None:
        return JsonResponse(
            {
                "message": (
                    "Debes verificar tu correo electronico antes de iniciar "
                    "sesion. Revisa tu bandeja de entrada."
                ),
                "status": "unverified",
            },
            status=403,
        )

    if user.status == User.Status.PENDING:
        return JsonResponse(
            {
                "message": "Tu cuenta aun esta pendiente de aprobacion",
                "status": "pending",
            },
            status=403,
        )

    if user.status == User.Status.REJECTED:
        return JsonResponse(
            {
                "message": (
                    "Tu solicitud de registro fue rechazada. Contacta a "
                    "FUNDCORSRD para mas informacion."
                ),
                "status": "rejected",
            },
            status=403,
        )

    login(request, user)
    return JsonResponse(
        {"status": "approved", "nombre": user.get_full_name() or user.username}
    )


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"message": "Sesion cerrada"})


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
        "<p>Enlace invalido o expirado</p>", status=400, content_type="text/html"
    )


def _user_not_found_response():
    return HttpResponse(
        "<p>Usuario no encontrado</p>", status=404, content_type="text/html"
    )


def _confirm_form_response(request, token, question_html):
    """Renders a GET-safe confirmation page with a POST form.

    Used by every one-click email link that mutates state (account
    approve/reject, email verification): the actual mutation never
    happens on a bare GET - mail clients, antivirus link-scanners, and
    chat/webmail link-unfurlers routinely prefetch every URL found in an
    email body, which would otherwise silently trigger the mutation
    before a human ever looks at it. Callers are responsible for
    HTML-escaping any user-controlled values in question_html.
    """
    csrf_token = get_token(request)
    return HttpResponse(
        "<!doctype html><html><body>"
        f"<p>{question_html}</p>"
        f'<form method="post">'
        f'<input type="hidden" name="csrfmiddlewaretoken" value="{escape(csrf_token)}">'
        f'<input type="hidden" name="token" value="{escape(token)}">'
        f'<button type="submit">Confirmar</button>'
        f"</form>"
        "</body></html>",
        content_type="text/html",
    )


def _result_page_response(user, message):
    return HttpResponse(
        "<!doctype html><html><body>"
        f"<p>{message} para "
        f"<strong>{escape(user.get_full_name() or user.username)}</strong> "
        f"({escape(user.email)}).</p>"
        "</body></html>",
        content_type="text/html",
    )


def _account_question_html(user, action_label):
    return (
        f"{action_label} la cuenta de "
        f"<strong>{escape(user.get_full_name() or user.username)}</strong> "
        f"({escape(user.email)}, cedula {escape(user.cedula)}, "
        f"telefono {escape(user.telefono)})?"
    )


@require_http_methods(["GET", "POST"])
def magic_approve_view(request):
    token = request.GET.get("token", "") if request.method == "GET" else request.POST.get("token", "")
    payload = read_approval_token(token)
    if payload is None or payload.get("action") != "approve":
        return _invalid_link_response()

    user = User.objects.filter(pk=payload.get("user_id")).first()
    if user is None:
        return _user_not_found_response()

    if request.method == "GET":
        return _confirm_form_response(request, token, _account_question_html(user, "Aprobar"))

    user.status = User.Status.APPROVED
    user.save()
    _send_approval_notification_email(user)
    return _result_page_response(user, "Cuenta aprobada")


@require_http_methods(["GET", "POST"])
def magic_reject_view(request):
    token = request.GET.get("token", "") if request.method == "GET" else request.POST.get("token", "")
    payload = read_approval_token(token)
    if payload is None or payload.get("action") != "reject":
        return _invalid_link_response()

    user = User.objects.filter(pk=payload.get("user_id")).first()
    if user is None:
        return _user_not_found_response()

    if request.method == "GET":
        return _confirm_form_response(request, token, _account_question_html(user, "Rechazar"))

    user.status = User.Status.REJECTED
    user.save()
    return _result_page_response(user, "Cuenta rechazada")


@require_http_methods(["GET", "POST"])
def verify_email_view(request):
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

    if user.email_verified_at is None:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])

    return HttpResponse(
        "<!doctype html><html><body>"
        f"<p>Correo verificado para <strong>{escape(user.email)}</strong>. "
        "Ya puedes iniciar sesión una vez tu cuenta sea aprobada por un "
        "administrador.</p>"
        "</body></html>",
        content_type="text/html",
    )
