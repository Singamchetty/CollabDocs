import uuid

from django.db import transaction
from django.db.models import Count, Max, Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from tags.models import Tag

from .models import Document, DocumentVersion
from .serializers import DocumentSerializer, DocumentTagsSerializer, DocumentVersionSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    http_method_names = ["get", "post", "put", "head", "options"]

    def get_queryset(self):
        queryset = Document.objects.prefetch_related("tags").order_by("-updated_at", "id")
        if self.action == "list":
            queryset = self._apply_list_filters(queryset).annotate(latest_version=Max("versions__version_number"))
        return queryset

    def _apply_list_filters(self, queryset):
        params = self.request.query_params

        workspace = params.get("workspace")
        if workspace:
            try:
                uuid.UUID(workspace)
            except ValueError:
                raise serializers.ValidationError({"workspace": ["Must be a valid UUID."]})
            queryset = queryset.filter(workspace_id=workspace)

        statuses = [value.strip() for value in params.get("status", "").split(",") if value.strip()]
        if statuses:
            invalid = [value for value in statuses if value not in Document.Status.values]
            if invalid:
                raise serializers.ValidationError(
                    {"status": [f"Invalid status {invalid}. Choose from {list(Document.Status.values)}."]}
                )
            queryset = queryset.filter(status__in=statuses)

        tag = params.get("tag", "").strip()
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag)

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        return queryset

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
            # Serialize concurrent PUTs so two of them can't read the same versions.count().
            Document.objects.select_for_update().get(pk=document.pk)
            document = serializer.save()
            self._create_version(document, saved_by)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        document = self.get_object()
        versions = document.versions.order_by("version_number")
        return Response(DocumentVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        document = self.get_object()
        totals = Document.objects.filter(pk=document.pk).aggregate(
            version_count=Count("versions", distinct=True),
            comment_count=Count("comments", distinct=True),
            contributor_count=Count("versions__saved_by", distinct=True),
        )
        return Response({"document": document.id, **totals})

    @action(detail=True, methods=["post"])
    def tags(self, request, pk=None):
        document = self.get_object()
        serializer = DocumentTagsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            tags = [Tag.objects.get_or_create(name=name)[0] for name in serializer.validated_data["tags"]]
            attached_ids = set(document.tags.values_list("id", flat=True))
            document.tags.add(*[tag for tag in tags if tag.id not in attached_ids])
        return Response(DocumentSerializer(document).data)
