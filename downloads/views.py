from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def downloads_view(request):
    """Gated list of Descargas Autorizadas links.

    This is the only place in the entire backend where
    settings.DOWNLOAD_LINKS is ever exposed. Authentication and approval
    are checked manually (rather than via login_required) so that an
    unauthenticated or unapproved request gets a JSON error instead of a
    redirect to a login page.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Debes iniciar sesion"}, status=401)

    if request.user.status != "approved":
        return JsonResponse(
            {"message": "Tu cuenta aun no ha sido aprobada"}, status=403
        )

    return JsonResponse({"downloads": settings.DOWNLOAD_LINKS})
