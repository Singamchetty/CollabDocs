from rest_framework import serializers

from .models import Document, DocumentVersion


class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = ["id", "document", "content", "version_number", "saved_by", "saved_at"]
        read_only_fields = fields


class DocumentSerializer(serializers.ModelSerializer):
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
            "status",
            "updated_at",
            "tag_names",
            "latest_version_number",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_tag_names(self, obj):
        return list(obj.tags.values_list("name", flat=True))

    def get_latest_version_number(self, obj):
        latest = obj.versions.order_by("-version_number").first()
        return latest.version_number if latest else None

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank or whitespace only.")
        return value.strip()
