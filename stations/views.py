from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import services


@require_GET
def stations_view(request):
    """Public NTRIP station list for the map.

    No authentication required - the map of stations is publicly visible
    by design; only the (separate) download endpoints are meant to be
    gated behind auth.
    """
    result = services.get_stations()
    return JsonResponse({
        "stations": result["stations"],
        "stale": result["stale"],
        "updated_at": result["updated_at"],
    })
