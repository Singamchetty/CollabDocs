from rest_framework.routers import DefaultRouter

from .views import CommentViewSet

router = DefaultRouter()
# Every app is mounted at /api/, so no single app's router should own the API root page.
router.include_root_view = False
router.register("comments", CommentViewSet, basename="comment")

urlpatterns = router.urls
