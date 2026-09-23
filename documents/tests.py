import io
from contextlib import redirect_stdout

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.test import TestCase

from audit_log.models import AuditLog
from config.exceptions import custom_exception_handler
from users.models import User
from workspaces.models import Workspace

from .models import Document, DocumentVersion
from .serializers import DocumentSerializer


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


class DocumentSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Ada", last_name="Lovelace", email="ada2@example.com", phone="+10000000003"
        )
        self.workspace = Workspace.objects.create(name="Design", owner=self.user)

    def test_blank_title_is_rejected(self):
        serializer = DocumentSerializer(
            data={
                "title": "   ",
                "content": "Body",
                "workspace": self.workspace.id,
                "status": Document.Status.DRAFT,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_tag_names_and_latest_version_number(self):
        document = Document.objects.create(
            title="Doc", content="Body", workspace=self.workspace, created_by=self.user
        )
        DocumentVersion.objects.create(document=document, content="v1", version_number=1)
        DocumentVersion.objects.create(document=document, content="v2", version_number=2)
        data = DocumentSerializer(document).data
        self.assertEqual(data["latest_version_number"], 2)
        self.assertEqual(data["tag_names"], [])


class ExceptionHandlerTests(TestCase):
    def test_does_not_exist_maps_to_404(self):
        response = custom_exception_handler(ObjectDoesNotExist(), {})
        self.assertEqual(response.status_code, 404)

    def test_integrity_error_maps_to_409(self):
        response = custom_exception_handler(IntegrityError(), {})
        self.assertEqual(response.status_code, 409)


class RequestLoggingMiddlewareTests(TestCase):
    def test_logs_method_path_status_and_duration(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.client.get("/admin/login/")
        output = buffer.getvalue()
        self.assertIn("GET", output)
        self.assertIn("/admin/login/", output)
        self.assertIn("ms", output)
