from django.db import IntegrityError, transaction
from django.test import TestCase

from users.models import User

from .models import Workspace, WorkspaceMember
from .serializers import WorkspaceMemberSerializer, WorkspaceSerializer


class WorkspaceMemberConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Ada", last_name="Lovelace", email="ada@example.com", phone="+10000000001"
        )
        self.workspace = Workspace.objects.create(name="Engineering", owner=self.user)

    def test_duplicate_membership_raises_integrity_error(self):
        WorkspaceMember.objects.create(
            workspace=self.workspace, user=self.user, role=WorkspaceMember.Role.ADMIN
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkspaceMember.objects.create(
                    workspace=self.workspace, user=self.user, role=WorkspaceMember.Role.VIEWER
                )


class WorkspaceSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Eve", last_name="Adams", email="eve@example.com", phone="+10000000005"
        )
        self.workspace = Workspace.objects.create(name="Ops", owner=self.user)

    def test_member_count(self):
        WorkspaceMember.objects.create(
            workspace=self.workspace, user=self.user, role=WorkspaceMember.Role.ADMIN
        )
        data = WorkspaceSerializer(self.workspace).data
        self.assertEqual(data["member_count"], 1)


class WorkspaceMemberSerializerTests(TestCase):
    def test_nested_user_representation(self):
        user = User.objects.create(
            first_name="Sam", last_name="Lee", email="sam@example.com", phone="+10000000006"
        )
        workspace = Workspace.objects.create(name="Support", owner=user)
        member = WorkspaceMember.objects.create(workspace=workspace, user=user, role=WorkspaceMember.Role.EDITOR)
        data = WorkspaceMemberSerializer(member).data
        self.assertEqual(data["user"]["email"], "sam@example.com")
