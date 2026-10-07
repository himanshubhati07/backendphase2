"""Version-relative aggregate routes for the canonical API apps.

Include this module below ``/api/v1/`` (for example,
``path('api/v1/', include('api.urls'))``) to expose the existing account,
story, and engagement routes without copying their endpoint declarations.
"""

from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("stories.urls")),
    path("", include("engagement.urls")),
]
