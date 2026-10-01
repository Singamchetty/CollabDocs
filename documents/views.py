from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Document, DocumentVersion
from .serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    http_method_names = ["get", "post", "put", "head", "options"]

    def get_queryset(self):
        return Document.objects.prefetch_related("tags").order_by("-updated_at", "id")

    @staticmethod
    def _create_version(document, saved_by):
        return DocumentVersion.objects.create(
            document=document,
            content=document.content,
            version_number=document.versions.count() + 1,
            saved_by=saved_by,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("saved_by", None)
        with transaction.atomic():
            document = serializer.save()
            self._create_version(document, document.created_by)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        document = self.get_object()
        serializer = self.get_serializer(document, data=request.data)
        serializer.is_valid(raise_exception=True)
        saved_by = serializer.validated_data.pop("saved_by", None) or document.created_by
        with transaction.atomic():
            document = serializer.save()
            self._create_version(document, saved_by)
        return Response(serializer.data)
