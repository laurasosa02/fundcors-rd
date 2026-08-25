import json
import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Inscripcion

logger = logging.getLogger(__name__)

# Dominican cedula: three digits, optional dash, seven digits, optional
# dash, one digit. Accepts either the dashed format (000-0000000-0) or 11
# raw digits.
CEDULA_RE = re.compile(r"^\d{3}-?\d{7}-?\d$")


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


def _validate_inscripcion(data):
    """Validate the inscripcion_view payload, collecting every problem found.

    Returns a dict shaped like {field: [message, ...]}, empty if valid.
    """
    errors = {}

    def add_error(field, message):
        errors.setdefault(field, []).append(message)

    nombre = data.get("nombre")
    if not isinstance(nombre, str) or not nombre.strip():
        add_error("nombre", "Este campo es obligatorio.")

    cedula = data.get("cedula")
    if not isinstance(cedula, str) or not cedula.strip():
        add_error("cedula", "Este campo es obligatorio.")
    elif not CEDULA_RE.match(cedula.strip()):
        add_error("cedula", "La cédula no es válida.")

    telefono = data.get("telefono")
    if not isinstance(telefono, str) or not telefono.strip():
        add_error("telefono", "Este campo es obligatorio.")

    correo = data.get("correo")
    if not isinstance(correo, str) or not correo.strip():
        add_error("correo", "Este campo es obligatorio.")
    else:
        correo_value = correo.strip()
        at_index = correo_value.find("@")
        if at_index == -1 or "." not in correo_value[at_index:]:
            add_error("correo", "El correo electrónico no es válido.")

    return errors


def _send_admin_inscripcion_email(inscripcion):
    message = (
        "Nueva solicitud de inscripción en el portal de FUNDCORSRD.\n\n"
        f"Nombre: {inscripcion.nombre}\n"
        f"Cédula: {inscripcion.cedula}\n"
        f"Teléfono: {inscripcion.telefono}\n"
        f"Correo: {inscripcion.correo}\n"
    )

    # The database save must always succeed regardless of email delivery,
    # so this is fail_silently. If it does fail, log it rather than
    # swallowing it without a trace.
    sent = send_mail(
        subject="Nueva solicitud de inscripción - FUNDCORSRD",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_NOTIFY_EMAIL],
        fail_silently=True,
    )
    if not sent:
        logger.warning(
            "Failed to send admin inscripcion-notification email for "
            "inscripcion id=%s correo=%s",
            inscripcion.id,
            inscripcion.correo,
        )


@require_POST
def inscripcion_view(request):
    data, error_response = _parse_json_body(request)
    if error_response is not None:
        return error_response

    errors = _validate_inscripcion(data)
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    inscripcion = Inscripcion.objects.create(
        nombre=data["nombre"].strip(),
        cedula=data["cedula"].strip(),
        telefono=data["telefono"].strip(),
        correo=data["correo"].strip(),
    )

    _send_admin_inscripcion_email(inscripcion)

    return JsonResponse(
        {"message": "Solicitud de inscripción recibida"}, status=201
    )
