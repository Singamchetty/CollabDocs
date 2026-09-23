from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "document", "author", "content", "parent", "created_at", "reply_count"]
        read_only_fields = ["id", "created_at"]

    def get_reply_count(self, obj):
        return obj.replies.count()

    def validate(self, attrs):
        parent = attrs.get("parent")
        document = attrs.get("document")
        if parent and document and parent.document_id != document.id:
            raise serializers.ValidationError(
                "A reply must belong to the same document as its parent comment."
            )
        return attrs
