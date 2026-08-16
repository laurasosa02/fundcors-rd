from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("csrf/", views.csrf_view, name="csrf"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.me_view, name="me"),
    path("magic-approve/", views.magic_approve_view, name="magic-approve"),
    path("magic-reject/", views.magic_reject_view, name="magic-reject"),
]
