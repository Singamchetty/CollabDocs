import io
import uuid
from contextlib import redirect_stdout
from unittest import mock

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from audit_log.models import AuditLog
from config.exceptions import custom_exception_handler
from users.models import User
from tags.models import Tag
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


def make_user(n):
    return User.objects.create(
        first_name=f"User{n}", last_name="Test", email=f"user{n}@example.com", phone=f"+1415555{n:04d}"
    )


class DocumentWriteApiTests(APITestCase):
    def setUp(self):
        self.author = make_user(1)
        self.editor = make_user(2)
        self.workspace = Workspace.objects.create(name="Docs", owner=self.author)
        self.payload = {
            "title": "Launch plan",
            "content": "v1 content",
            "workspace": str(self.workspace.id),
            "created_by": str(self.author.id),
            "status": "draft",
        }

    def test_create_document_also_creates_first_version(self):
        response = self.client.post("/api/documents/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["latest_version_number"], 1)
        document = Document.objects.get(id=response.data["id"])
        version = document.versions.get()
        self.assertEqual((version.version_number, version.content, version.saved_by), (1, "v1 content", self.author))
        self.assertEqual(AuditLog.objects.get(object_id=str(document.id)).action, "created")

    def test_create_rolls_back_document_and_audit_log_if_version_fails(self):
        self.client.raise_request_exception = False
        with mock.patch("documents.views.DocumentVersion.objects.create", side_effect=RuntimeError("boom")):
            response = self.client.post("/api/documents/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(DocumentVersion.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_create_validation_errors(self):
        cases = {
            "title": {"title": "  "},
            "workspace": {"workspace": str(uuid.uuid4())},
            "status": {"status": "frozen"},
            "created_by": {"created_by": str(uuid.uuid4())},
        }
        for field, override in cases.items():
            with self.subTest(field=field):
                response = self.client.post("/api/documents/", {**self.payload, **override}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertEqual(Document.objects.count(), 0)

    def test_create_missing_content_returns_400(self):
        del self.payload["content"]
        response = self.client.post("/api/documents/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_put_saves_a_new_version_and_logs_update(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        update = {**self.payload, "content": "v2 content", "saved_by": str(self.editor.id)}
        response = self.client.put(f"/api/documents/{document_id}/", update, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["latest_version_number"], 2)
        versions = list(DocumentVersion.objects.filter(document_id=document_id).order_by("version_number"))
        self.assertEqual([v.version_number for v in versions], [1, 2])
        self.assertEqual((versions[1].content, versions[1].saved_by), ("v2 content", self.editor))
        self.assertEqual(versions[0].content, "v1 content")
        actions = list(AuditLog.objects.filter(object_id=document_id).order_by("timestamp").values_list("action", flat=True))
        self.assertEqual(actions, ["created", "updated"])

    def test_put_without_saved_by_attributes_version_to_creator(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        self.client.put(f"/api/documents/{document_id}/", {**self.payload, "content": "v2"}, format="json")
        self.assertEqual(DocumentVersion.objects.get(document_id=document_id, version_number=2).saved_by, self.author)

    def test_put_cannot_change_created_by(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        update = {**self.payload, "content": "v2", "created_by": str(self.editor.id)}
        response = self.client.put(f"/api/documents/{document_id}/", update, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Document.objects.get(id=document_id).created_by, self.author)

    def test_put_rolls_back_content_change_if_version_fails(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        self.client.raise_request_exception = False
        with mock.patch("documents.views.DocumentVersion.objects.create", side_effect=RuntimeError("boom")):
            response = self.client.put(
                f"/api/documents/{document_id}/", {**self.payload, "content": "v2"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Document.objects.get(id=document_id).content, "v1 content")
        self.assertEqual(AuditLog.objects.filter(object_id=document_id).count(), 1)

    def test_invalid_put_does_not_create_a_version(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        response = self.client.put(f"/api/documents/{document_id}/", {**self.payload, "title": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DocumentVersion.objects.filter(document_id=document_id).count(), 1)

    def test_put_unknown_document_returns_404(self):
        response = self.client.put(f"/api/documents/{uuid.uuid4()}/", self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_document_and_unsupported_methods(self):
        document_id = self.client.post("/api/documents/", self.payload, format="json").data["id"]
        self.assertEqual(self.client.get(f"/api/documents/{document_id}/").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/documents/{document_id}/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/documents/{document_id}/").status_code, 405)


class DocumentListApiTests(APITestCase):
    def setUp(self):
        self.user = make_user(1)
        self.workspace = Workspace.objects.create(name="Docs", owner=self.user)
        self.other_workspace = Workspace.objects.create(name="Other", owner=self.user)
        self.python_tag = Tag.objects.create(name="python")
        self.django_tag = Tag.objects.create(name="django")
        self.draft = self.make_doc("Python basics", "intro to loops", status="draft", tags=[self.python_tag])
        self.published = self.make_doc(
            "Web guide", "uses Django views", status="published", tags=[self.python_tag, self.django_tag]
        )
        self.archived = self.make_doc("Old notes", "legacy", status="archived")
        self.elsewhere = self.make_doc("Elsewhere", "other", workspace=self.other_workspace)

    def make_doc(self, title, content, status="draft", workspace=None, tags=()):
        document = Document.objects.create(
            title=title, content=content, workspace=workspace or self.workspace, created_by=self.user, status=status
        )
        DocumentVersion.objects.create(document=document, content=content, version_number=1, saved_by=self.user)
        for tag in tags:
            tag.documents.add(document)
        return document

    def list_ids(self, query=""):
        response = self.client.get(f"/api/documents/{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return {item["id"] for item in response.data["results"]}

    def test_list_returns_all_documents_paginated(self):
        response = self.client.get("/api/documents/")
        self.assertEqual(response.data["count"], 4)
        self.assertIn("results", response.data)

    def test_filter_by_workspace(self):
        self.assertEqual(self.list_ids(f"?workspace={self.other_workspace.id}"), {str(self.elsewhere.id)})

    def test_filter_by_status_and_multiple_statuses(self):
        self.assertEqual(self.list_ids("?status=published"), {str(self.published.id)})
        self.assertEqual(
            self.list_ids("?status=draft,archived&workspace=" + str(self.workspace.id)),
            {str(self.draft.id), str(self.archived.id)},
        )

    def test_filter_by_tag_name_is_case_insensitive(self):
        self.assertEqual(self.list_ids("?tag=Python"), {str(self.draft.id), str(self.published.id)})
        self.assertEqual(self.list_ids("?tag=django"), {str(self.published.id)})
        self.assertEqual(self.list_ids("?tag=nope"), set())

    def test_search_matches_title_or_content_case_insensitively(self):
        self.assertEqual(self.list_ids("?search=PYTHON"), {str(self.draft.id)})
        self.assertEqual(self.list_ids("?search=django"), {str(self.published.id)})
        self.assertEqual(self.list_ids("?search=zzz"), set())

    def test_filters_combine(self):
        self.assertEqual(self.list_ids("?tag=python&status=draft"), {str(self.draft.id)})

    def test_invalid_filters_return_400(self):
        for query, field in [("?workspace=nope", "workspace"), ("?status=frozen", "status")]:
            with self.subTest(query=query):
                response = self.client.get(f"/api/documents/{query}")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_list_includes_tags_and_latest_version(self):
        response = self.client.get("/api/documents/?search=web")
        item = response.data["results"][0]
        self.assertEqual(item["tag_names"], ["django", "python"])
        self.assertEqual(item["latest_version_number"], 1)

    def test_list_query_count_does_not_grow_with_documents(self):
        with self.assertNumQueries(3):
            self.client.get("/api/documents/")
        for n in range(10):
            self.make_doc(f"Extra {n}", "x", tags=[self.python_tag])
        with self.assertNumQueries(3):
            self.client.get("/api/documents/")
