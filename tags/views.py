from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Tag
from .serializers import TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Tag.objects.annotate(document_count=Count("documents")).order_by("name")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            name = serializer.validated_data["name"]
            return Response({"detail": f"Tag '{name}' already exists."}, status=status.HTTP_409_CONFLICT)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
