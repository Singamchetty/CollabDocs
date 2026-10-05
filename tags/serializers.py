from rest_framework import serializers

from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "document_count"]
        read_only_fields = ["id"]

    def get_document_count(self, obj):
        if hasattr(obj, "document_count"):
            return obj.document_count
        return obj.documents.count()

    def validate_name(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("Tag name cannot be blank.")
        return normalized
