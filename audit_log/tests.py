import uuid
from datetime import datetime, timezone as dt_timezone

from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document
from users.models import User
from workspaces.models import Workspace

from .models import AuditLog


def utc(*args):
    return datetime(*args, tzinfo=dt_timezone.utc)


class AuditLogApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create(first_name="Alice", last_name="A", email="alice@example.com", phone="+14155550001")
        self.bob = User.objects.create(first_name="Bob", last_name="B", email="bob@example.com", phone="+14155550002")
        workspace = Workspace.objects.create(name="Docs", owner=self.alice)
        # Each document save writes an AuditLog row through the post_save signal.
        self.doc_a = Document.objects.create(title="A", content="x", workspace=workspace, created_by=self.alice)
        self.doc_b = Document.objects.create(title="B", content="x", workspace=workspace, created_by=self.bob)
        self.doc_a.content = "changed"
        self.doc_a.save()
        self.log_a_created, self.log_b_created, self.log_a_updated = AuditLog.objects.order_by("timestamp")
        AuditLog.objects.filter(pk=self.log_a_created.pk).update(timestamp=utc(2026, 1, 1, 23, 59))
        AuditLog.objects.filter(pk=self.log_b_created.pk).update(timestamp=utc(2026, 1, 2, 12, 0))
        AuditLog.objects.filter(pk=self.log_a_updated.pk).update(timestamp=utc(2026, 1, 3, 0, 0))

    def ids(self, query=""):
        response = self.client.get(f"/api/audit-logs/{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return [item["id"] for item in response.data["results"]]

    def test_list_is_newest_first_and_has_expected_fields(self):
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(self.log_a_updated.id), str(self.log_b_created.id), str(self.log_a_created.id)],
        )
        first = response.data["results"][0]
        self.assertEqual(set(first), {"id", "actor", "action", "model_name", "object_id", "timestamp"})
        self.assertEqual((first["action"], first["model_name"]), ("updated", "Document"))
        self.assertEqual(first["object_id"], str(self.doc_a.id))

    def test_filter_by_actor(self):
        self.assertEqual(
            self.ids(f"?actor={self.alice.id}"), [str(self.log_a_updated.id), str(self.log_a_created.id)]
        )
        self.assertEqual(self.ids(f"?actor={self.bob.id}"), [str(self.log_b_created.id)])
        self.assertEqual(self.ids(f"?actor={uuid.uuid4()}"), [])

    def test_date_from_is_inclusive_from_the_start_of_the_day(self):
        self.assertEqual(self.ids("?date_from=2026-01-02"), [str(self.log_a_updated.id), str(self.log_b_created.id)])

    def test_date_to_includes_the_whole_day(self):
        self.assertEqual(self.ids("?date_to=2026-01-02"), [str(self.log_b_created.id), str(self.log_a_created.id)])

    def test_date_range(self):
        self.assertEqual(self.ids("?date_from=2026-01-02&date_to=2026-01-02"), [str(self.log_b_created.id)])
        self.assertEqual(self.ids("?date_from=2026-02-01"), [])

    def test_datetime_bounds_respect_the_given_offset(self):
        self.assertEqual(self.ids("?date_from=2026-01-02T00:00:00Z&date_to=2026-01-02T12:00:00Z"), [str(self.log_b_created.id)])
        self.assertEqual(self.ids("?date_from=2026-01-02T13:00:00%2B01:00&date_to=2026-01-02T13:00:00%2B01:00"), [str(self.log_b_created.id)])

    def test_actor_and_date_range_combine(self):
        self.assertEqual(self.ids(f"?actor={self.alice.id}&date_from=2026-01-02"), [str(self.log_a_updated.id)])

    def test_invalid_filters_return_400(self):
        for query, field in [
            ("?actor=nope", "actor"),
            ("?date_from=yesterday", "date_from"),
            ("?date_to=2026-13-45", "date_to"),
            ("?date_from=2026-02-01&date_to=2026-01-01", "date_to"),
        ]:
            with self.subTest(query=query):
                response = self.client.get(f"/api/audit-logs/{query}")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)

    def test_logs_are_read_only(self):
        url = f"/api/audit-logs/{self.log_a_created.id}/"
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post("/api/audit-logs/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.put(url, {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
