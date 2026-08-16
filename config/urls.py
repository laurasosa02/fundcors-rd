"""
URL configuration for the FUNDCORSRD backend.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Mounted at django-admin/ (not the default admin/) to avoid
    # ambiguity with other tooling.
    path("django-admin/", admin.site.urls),
    path("auth/", include("accounts.urls")),
    path("stations/", include("stations.urls")),
    path("downloads/", include("downloads.urls")),
    path("inscripcion/", include("inscripciones.urls")),
]
