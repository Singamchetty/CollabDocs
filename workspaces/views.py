from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Workspace, WorkspaceMember
from .serializers import WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkspaceSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Workspace.objects.annotate(member_count=Count("members"))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            workspace = serializer.save()
            WorkspaceMember.objects.create(
                workspace=workspace, user=workspace.owner, role=WorkspaceMember.Role.ADMIN
            )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
