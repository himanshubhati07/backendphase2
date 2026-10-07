"""Authentication routes, mounted by the project below `/api/v1/`."""

from django.urls import path

from accounts.views import LoginView, RegistrationView

app_name = "accounts"

urlpatterns = [
    path("auth/register", RegistrationView.as_view(), name="register"),
    path("auth/login", LoginView.as_view(), name="login"),
]
