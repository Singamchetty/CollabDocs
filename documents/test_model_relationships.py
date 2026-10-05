import uuid

from django.core.management import call_command
from django.db import IntegrityError, models, transaction
from django.test import TestCase

from audit_log.models import AuditLog
from comments.models import Comment
from tags.models import Tag
from users.models import User
from workspaces.models import Workspace, WorkspaceMember

from .models import Document, DocumentVersion

ALL_MODELS = [User, Workspace, WorkspaceMember, Document, DocumentVersion, Comment, Tag, AuditLog]


def make_user(n):
    return User.objects.create(
        first_name=f"User{n}", last_name="Test", email=f"user{n}@example.com", phone=f"+1415555{n:04d}"
    )


class SchemaTests(TestCase):
    def test_every_model_has_an_auto_generated_uuid_primary_key(self):
        self.assertEqual(len(ALL_MODELS), 8)
        for model in ALL_MODELS:
            with self.subTest(model=model.__name__):
                pk = model._meta.pk
                self.assertIsInstance(pk, models.UUIDField)
                self.assertFalse(pk.editable)
                self.assertIs(pk.default, uuid.uuid4)

    def test_enums_are_textchoices_wired_to_their_fields(self):
        cases = [
            (Document, "status", Document.Status, {"draft", "published", "archived"}),
            (WorkspaceMember, "role", WorkspaceMember.Role, {"admin", "editor", "viewer"}),
        ]
        for model, field, enum, values in cases:
            with self.subTest(enum=enum.__name__):
                self.assertTrue(issubclass(enum, models.TextChoices))
                self.assertEqual(set(enum.values), values)
                self.assertEqual(model._meta.get_field(field).choices, enum.choices)

    def test_user_email_is_a_plain_unique_charfield(self):
        email = User._meta.get_field("email")
        self.assertIs(type(email), models.CharField)
        self.assertEqual((email.max_length, email.unique), (254, True))
        phone = User._meta.get_field("phone")
        self.assertEqual((phone.max_length, phone.unique), (15, True))

    def test_workspace_member_unique_constraint_is_declared_in_meta(self):
        constraints = {c.name: c for c in WorkspaceMember._meta.constraints}
        constraint = constraints["unique_workspace_member"]
        self.assertIsInstance(constraint, models.UniqueConstraint)
        self.assertEqual(constraint.fields, ("workspace", "user"))

    def test_comment_parent_is_a_self_referential_nullable_foreign_key(self):
        parent = Comment._meta.get_field("parent")
        self.assertIs(parent.related_model, Comment)
        self.assertTrue(parent.null and parent.blank)
        self.assertEqual(parent.remote_field.related_name, "replies")

    def test_tag_documents_is_declared_on_tag_with_reverse_name_tags(self):
        field = Tag._meta.get_field("documents")
        self.assertIsInstance(field, models.ManyToManyField)
        self.assertEqual(field.remote_field.related_name, "tags")

    def test_unique_columns_reject_duplicates(self):
        make_user(1)
        Tag.objects.create(name="python")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(first_name="x", last_name="y", email="user1@example.com", phone="+10000000000")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(first_name="x", last_name="y", email="other@example.com", phone="+14155550001")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tag.objects.create(name="python")

    def test_migrations_cover_every_model_change(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)


class OnDeleteBehaviourTests(TestCase):
    def setUp(self):
        self.owner = make_user(1)
        self.bob = make_user(2)
        self.workspace = Workspace.objects.create(name="Docs", owner=self.owner)
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.owner, role="admin")
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.bob, role="editor")
        self.document = Document.objects.create(
            title="Spec", content="v1", workspace=self.workspace, created_by=self.bob
        )
        self.version = DocumentVersion.objects.create(
            document=self.document, content="v1", version_number=1, saved_by=self.bob
        )
        self.comment = Comment.objects.create(document=self.document, author=self.bob, content="hi")
        self.tag = Tag.objects.create(name="python")
        self.tag.documents.add(self.document)

    def test_deleting_a_user_nulls_authorship_but_keeps_the_content(self):
        self.bob.delete()
        for obj in (self.document, self.version, self.comment):
            obj.refresh_from_db()
        self.assertIsNone(self.document.created_by)
        self.assertIsNone(self.version.saved_by)
        self.assertIsNone(self.comment.author)
        self.assertIsNone(AuditLog.objects.get(object_id=str(self.document.id)).actor)
        self.assertFalse(WorkspaceMember.objects.filter(user_id=self.bob.id).exists())

    def test_deleting_the_owner_cascades_through_the_workspace(self):
        self.owner.delete()
        self.assertEqual(Workspace.objects.count(), 0)
        self.assertEqual(WorkspaceMember.objects.count(), 0)
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(DocumentVersion.objects.count(), 0)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertTrue(User.objects.filter(id=self.bob.id).exists())

    def test_deleting_a_workspace_cascades_but_keeps_users_and_tags(self):
        self.workspace.delete()
        self.assertEqual(Document.objects.count(), 0)
        self.assertEqual(DocumentVersion.objects.count(), 0)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(self.tag.documents.count(), 0)
        self.assertTrue(Tag.objects.filter(id=self.tag.id).exists())

    def test_deleting_a_parent_comment_keeps_replies_as_top_level(self):
        reply = Comment.objects.create(
            document=self.document, author=self.owner, content="reply", parent=self.comment
        )
        self.comment.delete()
        reply.refresh_from_db()
        self.assertIsNone(reply.parent)

    def test_tag_and_document_relations_work_from_both_sides(self):
        self.assertEqual(list(self.document.tags.all()), [self.tag])
        self.assertEqual(list(self.tag.documents.all()), [self.document])
        self.assertEqual(list(Document.objects.filter(tags__name="python")), [self.document])
        self.document.delete()
        self.assertTrue(Tag.objects.filter(id=self.tag.id).exists())
        self.assertEqual(self.tag.documents.count(), 0)
