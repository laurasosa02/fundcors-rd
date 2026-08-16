from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for FUNDCORSRD.

    Authentication is by email (USERNAME_FIELD = "email"), while
    `username` is kept (from AbstractUser) as a required field, set equal
    to the email at registration time.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        APPROVED = "approved", "Aprobado"
        REJECTED = "rejected", "Rechazado"

    email = models.EmailField(unique=True)
    cedula = models.CharField(max_length=20)
    telefono = models.CharField(max_length=20)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        full_name = self.get_full_name()
        display_name = full_name if full_name else self.username
        return f"{display_name} <{self.email}>"
