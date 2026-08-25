from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail

from .models import User


@admin.register(User)
class FundcorsrdUserAdmin(UserAdmin):
    list_display = (
        "email",
        "get_full_name",
        "cedula",
        "telefono",
        "status",
        "is_email_verified",
        "is_staff",
    )
    list_filter = ("status", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "cedula")
    ordering = ("email",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "FUNDCORSRD",
            {"fields": ("cedula", "telefono", "status", "email_verified_at")},
        ),
    )

    actions = ["approve_users", "reject_users"]

    @admin.display(description="Nombre completo")
    def get_full_name(self, obj):
        return obj.get_full_name()

    @admin.display(description="Correo verificado", boolean=True)
    def is_email_verified(self, obj):
        return obj.email_verified_at is not None

    @admin.action(description="Aprobar usuarios seleccionados")
    def approve_users(self, request, queryset):
        updated = queryset.update(status=User.Status.APPROVED)
        # The database write above must always succeed regardless of email
        # delivery, so notification emails are sent with fail_silently=True
        # and never gate/undo the status update.
        for user in queryset:
            send_mail(
                subject="Tu cuenta de FUNDCORSRD ha sido aprobada",
                message=(
                    f"Hola {user.get_full_name() or user.username},\n\n"
                    "Tu cuenta en el portal de FUNDCORSRD ha sido aprobada. "
                    "Ya puedes iniciar sesión.\n\n"
                    "FUNDCORSRD"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        self.message_user(request, f"{updated} usuario(s) aprobado(s).")

    @admin.action(description="Rechazar usuarios seleccionados")
    def reject_users(self, request, queryset):
        updated = queryset.update(status=User.Status.REJECTED)
        self.message_user(request, f"{updated} usuario(s) rechazado(s).")
