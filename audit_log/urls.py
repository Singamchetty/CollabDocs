from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

router = DefaultRouter()
# Every app is mounted at /api/, so no single app's router should own the API root page.
router.include_root_view = False
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
