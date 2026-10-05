from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document
from users.models import User
from workspaces.models import Workspace

from .models import Tag
from .serializers import TagSerializer


class TagSerializerTests(TestCase):
    def test_name_is_normalized(self):
        serializer = TagSerializer(data={"name": "  Python  "})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        tag = serializer.save()
        self.assertEqual(tag.name, "python")

    def test_blank_name_rejected(self):
        serializer = TagSerializer(data={"name": "   "})
        self.assertFalse(serializer.is_valid())


class TagApiTests(APITestCase):
    def test_create_tag(self):
        response = self.client.post("/api/tags/", {"name": "Python"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "python")
        self.assertEqual(response.data["document_count"], 0)
        self.assertEqual(Tag.objects.count(), 1)

    def test_duplicate_name_returns_409_regardless_of_case_or_padding(self):
        self.client.post("/api/tags/", {"name": "python"}, format="json")
        for name in ["python", "Python", "  PYTHON "]:
            with self.subTest(name=name):
                response = self.client.post("/api/tags/", {"name": name}, format="json")
                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
                self.assertIn("python", response.data["detail"])
        self.assertEqual(Tag.objects.count(), 1)

    def test_invalid_names_return_400(self):
        for body in [{}, {"name": ""}, {"name": "   "}, {"name": "x" * 101}]:
            with self.subTest(body=body):
                response = self.client.post("/api/tags/", body, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("name", response.data)
        self.assertEqual(Tag.objects.count(), 0)

    def test_tag_created_here_is_reused_when_tagging_a_document(self):
        user = User.objects.create(first_name="A", last_name="B", email="a@example.com", phone="+14155550001")
        workspace = Workspace.objects.create(name="Docs", owner=user)
        document = Document.objects.create(title="Spec", content="x", workspace=workspace, created_by=user)
        tag_id = self.client.post("/api/tags/", {"name": "python"}, format="json").data["id"]
        response = self.client.post(f"/api/documents/{document.id}/tags/", {"tags": ["Python"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(self.client.get(f"/api/tags/{tag_id}/").data["document_count"], 1)

    def test_get_tag_and_unsupported_methods(self):
        tag_id = self.client.post("/api/tags/", {"name": "python"}, format="json").data["id"]
        self.assertEqual(self.client.get(f"/api/tags/{tag_id}/").status_code, 200)
        self.assertEqual(self.client.put(f"/api/tags/{tag_id}/", {"name": "x"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/tags/{tag_id}/").status_code, 405)
