import uuid

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document
from users.models import User
from workspaces.models import Workspace

from .models import Comment
from .serializers import CommentSerializer


class CommentSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            first_name="Bob", last_name="Smith", email="bob@example.com", phone="+10000000004"
        )
        self.workspace = Workspace.objects.create(name="Docs", owner=self.user)
        self.doc_a = Document.objects.create(title="A", content="a", workspace=self.workspace, created_by=self.user)
        self.doc_b = Document.objects.create(title="B", content="b", workspace=self.workspace, created_by=self.user)

    def test_reply_must_match_parent_document(self):
        parent = Comment.objects.create(document=self.doc_a, author=self.user, content="root")
        serializer = CommentSerializer(
            data={
                "document": self.doc_b.id,
                "author": self.user.id,
                "content": "reply",
                "parent": parent.id,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_reply_count(self):
        parent = Comment.objects.create(document=self.doc_a, author=self.user, content="root")
        Comment.objects.create(document=self.doc_a, author=self.user, content="reply", parent=parent)
        data = CommentSerializer(parent).data
        self.assertEqual(data["reply_count"], 1)


class CommentApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create(first_name="Alice", last_name="A", email="alice@example.com", phone="+14155550001")
        self.bob = User.objects.create(first_name="Bob", last_name="B", email="bob@example.com", phone="+14155550002")
        self.workspace = Workspace.objects.create(name="Docs", owner=self.alice)
        self.doc = Document.objects.create(title="Spec", content="x", workspace=self.workspace, created_by=self.alice)
        self.other_doc = Document.objects.create(title="Other", content="y", workspace=self.workspace, created_by=self.alice)

    def post(self, **overrides):
        body = {"document": str(self.doc.id), "author": str(self.alice.id), "content": "hello", **overrides}
        return self.client.post("/api/comments/", body, format="json")

    def test_create_top_level_comment(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["parent"])
        self.assertEqual(response.data["reply_count"], 0)

    def test_create_reply_to_a_comment(self):
        parent_id = self.post().data["id"]
        response = self.post(parent=parent_id, author=str(self.bob.id), content="reply")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["parent"]), str(parent_id))
        self.assertEqual(Comment.objects.get(id=parent_id).replies.count(), 1)

    def test_reply_to_a_comment_on_another_document_is_rejected(self):
        parent_id = self.post().data["id"]
        response = self.post(document=str(self.other_doc.id), parent=parent_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_validation_errors(self):
        cases = {
            "document": {"document": str(uuid.uuid4())},
            "author": {"author": str(uuid.uuid4())},
            "parent": {"parent": str(uuid.uuid4())},
            "content": {"content": "   "},
        }
        for field, override in cases.items():
            with self.subTest(field=field):
                response = self.post(**override)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertEqual(Comment.objects.count(), 0)

    def test_author_is_required(self):
        response = self.client.post(
            "/api/comments/", {"document": str(self.doc.id), "content": "hi"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("author", response.data)

    def build_thread(self):
        root = Comment.objects.create(document=self.doc, author=self.alice, content="root")
        reply = Comment.objects.create(document=self.doc, author=self.bob, content="reply", parent=root)
        Comment.objects.create(document=self.doc, author=self.alice, content="nested", parent=reply)
        Comment.objects.create(document=self.doc, author=self.bob, content="second reply", parent=root)
        Comment.objects.create(document=self.doc, author=self.bob, content="another root")
        Comment.objects.create(document=self.other_doc, author=self.bob, content="elsewhere")
        return root

    def test_list_returns_a_threaded_tree_for_the_document(self):
        self.build_thread()
        response = self.client.get(f"/api/comments/?document={self.doc.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roots = response.data
        self.assertEqual([c["content"] for c in roots], ["root", "another root"])
        self.assertEqual([r["content"] for r in roots[0]["replies"]], ["reply", "second reply"])
        self.assertEqual(roots[0]["replies"][0]["replies"][0]["content"], "nested")
        self.assertEqual(roots[1]["replies"], [])
        self.assertEqual(roots[0]["author"], {"id": str(self.alice.id), "first_name": "Alice", "last_name": "A"})

    def test_list_uses_a_fixed_number_of_queries(self):
        self.build_thread()
        with self.assertNumQueries(2):
            self.client.get(f"/api/comments/?document={self.doc.id}")

    def test_list_for_document_without_comments_is_empty(self):
        response = self.client.get(f"/api/comments/?document={self.doc.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_query_param_errors(self):
        self.assertEqual(self.client.get("/api/comments/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get("/api/comments/?document=nope").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.client.get(f"/api/comments/?document={uuid.uuid4()}").status_code, status.HTTP_404_NOT_FOUND
        )

    def test_get_single_comment_and_unsupported_methods(self):
        comment_id = self.post().data["id"]
        self.assertEqual(self.client.get(f"/api/comments/{comment_id}/").status_code, 200)
        self.assertEqual(self.client.put(f"/api/comments/{comment_id}/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/comments/{comment_id}/").status_code, 405)
