from django.db import IntegrityError, transaction
from django.test import TestCase

from users.models import User

from .models import Workspace, WorkspaceMember


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
