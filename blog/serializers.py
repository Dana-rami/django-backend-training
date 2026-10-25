from rest_framework import serializers

from .models import Post


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title", "content", "is_published", "created_at"]
        read_only_fields = ["created_at"]

    def validate_title(self, value):
        if "spam" in value.lower():
            raise serializers.ValidationError("Title cannot contain the word spam.")
        return value

    def validate(self, attrs):
        title = attrs.get("title")
        content = attrs.get("content")
        if self.instance is not None:
            if title is None:
                title = self.instance.title
            if content is None:
                content = self.instance.content
        if title is not None and content is not None and title == content:
            raise serializers.ValidationError(
                "Title and content cannot be exactly the same."
            )
        return attrs
