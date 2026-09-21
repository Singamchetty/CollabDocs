import uuid

from django.db import models

from documents.models import Document


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    documents = models.ManyToManyField(Document, related_name="tags", blank=True)

    def __str__(self):
        return self.name
