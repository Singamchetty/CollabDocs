from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Workspace, WorkspaceMember


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "workspace", "user", "user_id", "role", "joined_at"]
        read_only_fields = ["id", "workspace", "joined_at"]


class WorkspaceSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ["id", "name", "owner", "is_active", "created_at", "member_count"]
        read_only_fields = ["id", "owner", "created_at"]

    def get_member_count(self, obj):
        return obj.members.count()
