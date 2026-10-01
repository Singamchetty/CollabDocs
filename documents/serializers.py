from django.db.models import Max
from rest_framework import serializers

from users.models import User

from .models import Document, DocumentVersion


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ["id", "document", "content", "version_number", "saved_by", "saved_at"]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
    saved_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True, required=False)
    tag_names = serializers.SerializerMethodField()
    latest_version_number = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "workspace",
            "created_by",
            "saved_by",
            "status",
            "updated_at",
            "tag_names",
            "latest_version_number",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_tag_names(self, obj):
        return sorted(tag.name for tag in obj.tags.all())

    def get_latest_version_number(self, obj):
        if hasattr(obj, "latest_version"):
            return obj.latest_version
        return obj.versions.aggregate(latest=Max("version_number"))["latest"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank or whitespace only.")
        return value.strip()

    def update(self, instance, validated_data):
        validated_data.pop("created_by", None)
        return super().update(instance, validated_data)
