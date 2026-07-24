from django import forms
from django.core.exceptions import ValidationError

from .markdown import extract_title, normalize_markdown, read_markdown_upload
from .models import ContentBase


class ContentEditorForm(forms.Form):
    manual_content = forms.CharField(
        required=False,
        label="Write Markdown",
        widget=forms.Textarea(
            attrs={
                "rows": 22,
                "placeholder": "# Required title\n\nWrite your Markdown here...",
                "spellcheck": "true",
            }
        ),
    )
    markdown_file = forms.FileField(
        required=False,
        label="Upload a UTF-8 .md file",
        widget=forms.ClearableFileInput(attrs={"accept": ".md,text/markdown"}),
    )
    visibility = forms.ChoiceField(choices=ContentBase.Visibility.choices)

    def __init__(self, *args, allow_empty_content=False, **kwargs):
        self.allow_empty_content = allow_empty_content
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        manual = cleaned.get("manual_content", "")
        upload = cleaned.get("markdown_file")
        if manual.strip() and upload:
            raise ValidationError("Choose either manual Markdown or a file, not both.")
        if upload:
            try:
                markdown = read_markdown_upload(upload)
            except ValidationError as exc:
                self.add_error("markdown_file", exc)
                return cleaned
        elif manual.strip():
            markdown = normalize_markdown(manual)
        elif self.allow_empty_content:
            markdown = None
        else:
            raise ValidationError("Enter Markdown text or select a .md file.")
        if markdown is not None:
            try:
                extract_title(markdown)
            except ValidationError as exc:
                self.add_error("manual_content" if not upload else "markdown_file", exc)
                return cleaned
        cleaned["markdown"] = markdown
        return cleaned

