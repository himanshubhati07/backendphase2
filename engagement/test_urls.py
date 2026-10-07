"""URLConf used by engagement's isolated API tests."""

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("engagement.urls")),
]
