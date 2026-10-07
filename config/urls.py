"""Project URL routing and OpenAPI documentation."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("api/v1/", include("api.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("openapi.json", SpectacularAPIView.as_view(), name="openapi-json"),
    path("docs", SpectacularSwaggerView.as_view(url_name="openapi-json"), name="docs"),
]
