import uuid
from unittest import mock

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

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


def make_user(n):
    return User.objects.create(
        first_name=f"User{n}", last_name="Test", email=f"user{n}@example.com", phone=f"+1415555{n:04d}"
    )


class WorkspaceApiTests(APITestCase):
    def setUp(self):
        self.owner = make_user(1)

    def test_create_workspace_adds_owner_as_admin_member(self):
        response = self.client.post(
            "/api/workspaces/", {"name": "Engineering", "owner": str(self.owner.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["member_count"], 1)
        member = WorkspaceMember.objects.get(workspace_id=response.data["id"])
        self.assertEqual(member.user, self.owner)
        self.assertEqual(member.role, WorkspaceMember.Role.ADMIN)

    def test_create_workspace_rolls_back_if_member_creation_fails(self):
        self.client.raise_request_exception = False
        with mock.patch("workspaces.views.WorkspaceMember.objects.create", side_effect=RuntimeError("boom")):
            response = self.client.post(
                "/api/workspaces/", {"name": "Engineering", "owner": str(self.owner.id)}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Workspace.objects.count(), 0)
        self.assertEqual(WorkspaceMember.objects.count(), 0)

    def test_create_workspace_with_unknown_owner_is_rejected(self):
        response = self.client.post(
            "/api/workspaces/", {"name": "Engineering", "owner": str(uuid.uuid4())}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner", response.data)
        self.assertEqual(Workspace.objects.count(), 0)

    def test_create_workspace_with_blank_name_is_rejected(self):
        response = self.client.post("/api/workspaces/", {"name": "   ", "owner": str(self.owner.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_get_workspace_includes_member_count(self):
        workspace = Workspace.objects.create(name="Ops", owner=self.owner)
        WorkspaceMember.objects.create(workspace=workspace, user=self.owner, role=WorkspaceMember.Role.ADMIN)
        WorkspaceMember.objects.create(workspace=workspace, user=make_user(2), role=WorkspaceMember.Role.VIEWER)
        response = self.client.get(f"/api/workspaces/{workspace.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["member_count"], 2)

    def test_get_unknown_workspace_returns_404(self):
        response = self.client.get(f"/api/workspaces/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WorkspaceMembersApiTests(APITestCase):
    def setUp(self):
        self.owner = make_user(1)
        self.workspace = Workspace.objects.create(name="Ops", owner=self.owner)
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.owner, role=WorkspaceMember.Role.ADMIN)
        self.url = f"/api/workspaces/{self.workspace.id}/members/"

    def test_add_member_with_role(self):
        newcomer = make_user(2)
        response = self.client.post(self.url, {"user_id": str(newcomer.id), "role": "editor"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "editor")
        self.assertEqual(response.data["user"]["email"], newcomer.email)
        self.assertTrue(
            WorkspaceMember.objects.filter(workspace=self.workspace, user=newcomer, role="editor").exists()
        )

    def test_duplicate_member_returns_409(self):
        response = self.client.post(self.url, {"user_id": str(self.owner.id), "role": "viewer"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace).count(), 1)

    def test_unknown_user_returns_404(self):
        response = self.client.post(self.url, {"user_id": str(uuid.uuid4()), "role": "viewer"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_role_returns_400(self):
        response = self.client.post(self.url, {"user_id": str(make_user(2).id), "role": "owner"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    def test_missing_fields_return_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"user_id", "role"})

    def test_unknown_workspace_returns_404(self):
        response = self.client.get(f"/api/workspaces/{uuid.uuid4()}/members/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_members_with_roles_uses_constant_queries(self):
        for n in range(2, 6):
            WorkspaceMember.objects.create(
                workspace=self.workspace, user=make_user(n), role=WorkspaceMember.Role.VIEWER
            )
        with self.assertNumQueries(2):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        self.assertEqual(response.data[0]["role"], "admin")
        self.assertEqual(response.data[0]["user"]["email"], self.owner.email)

