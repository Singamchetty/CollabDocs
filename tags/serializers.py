from rest_framework import serializers

from .models import Tag


class TagSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "document_count"]
        read_only_fields = ["id"]

    def get_document_count(self, obj):
        return obj.documents.count()

    def validate_name(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("Tag name cannot be blank.")
        return normalized
