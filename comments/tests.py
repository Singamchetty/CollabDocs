from django.test import TestCase

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
