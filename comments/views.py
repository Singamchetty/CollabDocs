import uuid
from collections import defaultdict

from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.response import Response

from documents.models import Document

from .models import Comment
from .serializers import CommentSerializer, CommentThreadSerializer


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        document_id = request.query_params.get("document")
        if not document_id:
            raise serializers.ValidationError({"document": "This query parameter is required."})
        try:
            uuid.UUID(document_id)
        except ValueError:
            raise serializers.ValidationError({"document": "Must be a valid UUID."})
        document = get_object_or_404(Document, pk=document_id)

        comments = list(
            Comment.objects.filter(document=document).select_related("author").order_by("created_at", "id")
        )
        known_ids = {comment.id for comment in comments}
        children = defaultdict(list)
        roots = []
        for comment in comments:
            if comment.parent_id in known_ids:
                children[comment.parent_id].append(comment)
            else:
                roots.append(comment)
        for comment in comments:
            comment._children = children.get(comment.id, [])

        return Response(CommentThreadSerializer(roots, many=True).data)
