from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet

router = DefaultRouter()
# Every app is mounted at /api/, so no single app's router should own the API root page.
router.include_root_view = False
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls
