import io
from contextlib import redirect_stdout

from django.test import TestCase

from audit_log.models import AuditLog
from users.models import User
from workspaces.models import Workspace

from .models import Document


class DocumentAuditLogSignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Grace", last_name="Hopper", email="grace@example.com", phone="+10000000002"
        )
        self.workspace = Workspace.objects.create(name="Research", owner=self.user)

    def test_create_writes_created_audit_log(self):
        document = Document.objects.create(
            title="Doc", content="Hello", workspace=self.workspace, created_by=self.user
        )
        log = AuditLog.objects.get(model_name="Document", object_id=str(document.id))
        self.assertEqual(log.action, "created")
        self.assertEqual(log.actor, self.user)

    def test_update_writes_updated_audit_log(self):
        document = Document.objects.create(
            title="Doc", content="Hello", workspace=self.workspace, created_by=self.user
        )
        document.content = "Updated"
        document.save()
        logs = AuditLog.objects.filter(model_name="Document", object_id=str(document.id)).order_by("timestamp")
        self.assertEqual(logs.count(), 2)
        self.assertEqual(logs.last().action, "updated")


class RequestLoggingMiddlewareTests(TestCase):
    def test_logs_method_path_status_and_duration(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.client.get("/admin/login/")
        output = buffer.getvalue()
        self.assertIn("GET", output)
        self.assertIn("/admin/login/", output)
        self.assertIn("ms", output)
