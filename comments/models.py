import uuid

from django.db import models

from documents.models import Document
from users.models import User


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="comments")
    content = models.TextField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.document}"
