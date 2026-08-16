from django.urls import path

from . import views

app_name = "downloads"

urlpatterns = [
    path("", views.downloads_view, name="downloads"),
]
