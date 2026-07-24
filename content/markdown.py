import re

import markdown2
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe


MAX_CONTENT_BYTES = 2 * 1024 * 1024
H1_PATTERN = re.compile(r"^#(?!#)\s+(.+?)\s*$")


def normalize_markdown(markdown):
    if not isinstance(markdown, str):
        raise ValidationError("Markdown content must be UTF-8 text.")
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    if len(markdown.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise ValidationError("Markdown content cannot exceed 2 MB.")
    return markdown


def read_markdown_upload(uploaded_file):
    if not uploaded_file.name.lower().endswith(".md"):
        raise ValidationError("Only .md files are accepted.")
    if uploaded_file.size > MAX_CONTENT_BYTES:
        raise ValidationError("Markdown files cannot exceed 2 MB.")
    try:
        payload = uploaded_file.read().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("Markdown files must use UTF-8 encoding.") from exc
    finally:
        uploaded_file.seek(0)
    return normalize_markdown(payload)


def extract_title(markdown):
    markdown = normalize_markdown(markdown)
    for line in markdown.splitlines():
        if not line.strip():
            continue
        match = H1_PATTERN.fullmatch(line.strip())
        if not match or not match.group(1).strip():
            raise ValidationError(
                "The first non-empty line must be a Markdown H1 such as '# Title'."
            )
        return match.group(1).strip()
    raise ValidationError("Markdown content must begin with a non-empty H1 title.")


def body_without_title(markdown):
    lines = normalize_markdown(markdown).splitlines()
    for index, line in enumerate(lines):
        if line.strip():
            return "\n".join(lines[:index] + lines[index + 1 :])
    return ""


def render_markdown(markdown):
    # Raw HTML intentionally remains enabled per the product requirement. See README.
    html = markdown2.markdown(
        body_without_title(markdown),
        extras=["fenced-code-blocks", "tables", "strike", "cuddled-lists"],
    )
    return mark_safe(html)


def markdown_preview(markdown, line_count=5):
    preview_lines = []
    lines = body_without_title(markdown).splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("```"):
            continue
        line = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"^[#>*+\-\d.\s]+", "", line)
        line = re.sub(r"[`_*~]", "", line).strip()
        if line:
            preview_lines.append(line)
        if len(preview_lines) == line_count:
            break
    remaining = len([line for line in lines if line.strip()]) > len(preview_lines)
    text = "\n".join(preview_lines)
    return f"{text}\n..." if text and remaining else text
