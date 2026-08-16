from django.urls import path

from . import views

app_name = "inscripciones"

urlpatterns = [
    path("", views.inscripcion_view, name="inscripcion"),
]
