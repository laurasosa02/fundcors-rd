from django.db import models


class Inscripcion(models.Model):
    """A membership (Inscripcion) request submitted via the public form.

    This is intentionally independent from the accounts app's
    login/approval system: a person can submit this form without ever
    registering a login account, and vice versa. It only records the
    submitted contact details for staff follow-up; it grants no access to
    RINEX or any other part of the site.
    """

    nombre = models.CharField(max_length=200, verbose_name="nombre y apellido")
    cedula = models.CharField(max_length=20, verbose_name="cedula")
    telefono = models.CharField(max_length=20, verbose_name="telefono")
    correo = models.EmailField(verbose_name="correo")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nombre} ({self.correo})"
