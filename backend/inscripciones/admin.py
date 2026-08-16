from django.contrib import admin

from .models import Inscripcion


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula", "telefono", "correo", "created_at")
    list_filter = ("created_at",)
    search_fields = ("nombre", "cedula", "correo")
    ordering = ("-created_at",)
    readonly_fields = ("nombre", "cedula", "telefono", "correo", "created_at")

    def has_add_permission(self, request):
        # Entries are only ever created via the public inscripcion form,
        # never fabricated manually from the admin. Staff can view, search,
        # and delete, but not create.
        return False
