from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/", include("workspaces.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("comments.urls")),
    path("api/", include("tags.urls")),
    path("api/", include("audit_log.urls")),
]
