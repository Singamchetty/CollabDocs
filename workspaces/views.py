from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import User

from .models import Workspace, WorkspaceMember
from .serializers import WorkspaceMemberSerializer, WorkspaceSerializer


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

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        workspace = self.get_object()
        if request.method == "GET":
            members = workspace.members.select_related("user").order_by("joined_at")
            return Response(WorkspaceMemberSerializer(members, many=True).data)

        serializer = WorkspaceMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(pk=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            with transaction.atomic():
                member = WorkspaceMember.objects.create(
                    workspace=workspace, user=user, role=serializer.validated_data["role"]
                )
        except IntegrityError:
            return Response(
                {"detail": "User is already a member of this workspace."}, status=status.HTTP_409_CONFLICT
            )
        return Response(WorkspaceMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        workspace = self.get_object()
        totals = Workspace.objects.filter(pk=workspace.pk).aggregate(
            document_count=Count("documents", distinct=True),
            member_count=Count("members", distinct=True),
            comment_count=Count("documents__comments", distinct=True),
        )
        return Response({"workspace": workspace.id, **totals})
