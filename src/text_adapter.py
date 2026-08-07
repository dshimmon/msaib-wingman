"""Extract normalized units from inert UTF-8 text and Markdown files."""

import re
from pathlib import Path

from document_errors import (
    DocumentDecodingError,
    NoReadableContentError,
)


ATX_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
SETEXT_UNDERLINE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")


def decode_utf8_text(file_path):
    """Decode UTF-8 deterministically, accepting an optional UTF-8 BOM."""
    path = Path(file_path)
    try:
        return path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentDecodingError(
            f"{path.suffix.lower() or 'Text'} document must be valid UTF-8."
        ) from error


def line_location(start_line, end_line):
    """Return a stable one-line or inclusive line-range location."""
    if start_line == end_line:
        return f"Line {start_line}"
    return f"Lines {start_line}-{end_line}"


def extract_text_units(file_path):
    """Extract one normalized unit per contiguous non-blank line group."""
    lines = decode_utf8_text(file_path).splitlines()
    units = []
    group = []
    start_line = None

    def append_group(end_line):
        nonlocal group, start_line
        if not group:
            return
        units.append(
            {
                "heading": None,
                "location": line_location(start_line, end_line),
                "text": "\n".join(group),
            }
        )
        group = []
        start_line = None

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            append_group(line_number - 1)
            continue
        if start_line is None:
            start_line = line_number
        group.append(line.rstrip())

    append_group(len(lines))
    if not units:
        raise NoReadableContentError(
            "Text document contains no readable content."
        )
    return units


def markdown_heading(lines, index):
    """Return a literal Markdown heading without executing Markdown."""
    match = ATX_HEADING.match(lines[index])
    if match:
        return match.group(2).strip(), 1
    if (
        index + 1 < len(lines)
        and lines[index].strip()
        and SETEXT_UNDERLINE.match(lines[index + 1])
    ):
        return lines[index].strip(), 2
    return None, 0


def extract_markdown_units(file_path):
    """Extract heading-aware Markdown sections with stable source lines."""
    lines = decode_utf8_text(file_path).splitlines()
    units = []
    current_heading = None
    current_lines = []
    start_line = None
    fence_marker = None

    def append_section(end_line):
        nonlocal current_lines, start_line
        text = "\n".join(current_lines).strip()
        if text:
            units.append(
                {
                    "heading": current_heading,
                    "location": line_location(start_line, end_line),
                    "text": text,
                }
            )
        current_lines = []
        start_line = None

    index = 0
    while index < len(lines):
        stripped = lines[index].lstrip()
        if fence_marker is not None:
            current_lines.append(lines[index].rstrip())
            if stripped.startswith(fence_marker):
                fence_marker = None
            index += 1
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if start_line is None:
                start_line = index + 1
            fence_marker = stripped[:3]
            current_lines.append(lines[index].rstrip())
            index += 1
            continue
        heading, consumed = markdown_heading(lines, index)
        line_number = index + 1
        if heading is not None:
            if current_lines:
                append_section(line_number - 1)
            current_heading = heading
            start_line = line_number
            current_lines.extend(lines[index : index + consumed])
            index += consumed
            continue
        if lines[index].strip():
            if start_line is None:
                start_line = line_number
            current_lines.append(lines[index].rstrip())
        elif current_lines:
            current_lines.append("")
        index += 1

    if current_lines:
        append_section(len(lines))
    if not units:
        raise NoReadableContentError(
            "Markdown document contains no readable content."
        )
    return units
