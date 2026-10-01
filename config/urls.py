from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from documents.views import DocumentViewSet
from users.views import UserViewSet
from workspaces.views import WorkspaceViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
