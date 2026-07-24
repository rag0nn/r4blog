from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from content.markdown import extract_title, normalize_markdown, read_markdown_upload
from content.models import ContentBase


class ContentWriteSerializer(serializers.Serializer):
    markdown = serializers.CharField(required=False, allow_blank=False, write_only=True)
    file = serializers.FileField(required=False, write_only=True)
    visibility = serializers.ChoiceField(
        choices=ContentBase.Visibility.choices, required=False
    )

    def validate(self, attrs):
        markdown = attrs.get("markdown")
        upload = attrs.get("file")
        if markdown is not None and upload is not None:
            raise serializers.ValidationError(
                "Choose either the markdown field or a .md file, not both."
            )
        if self.context.get("creating") and markdown is None and upload is None:
            raise serializers.ValidationError("Markdown text or a .md file is required.")
        try:
            if upload is not None:
                markdown = read_markdown_upload(upload)
            elif markdown is not None:
                markdown = normalize_markdown(markdown)
            if markdown is not None:
                extract_title(markdown)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"content": list(exc.messages)}
            ) from exc
        attrs["parsed_markdown"] = markdown
        return attrs


def content_response(instance):
    return {
        "title": instance.title,
        "slug": instance.slug,
        "visibility": instance.visibility,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
    }

