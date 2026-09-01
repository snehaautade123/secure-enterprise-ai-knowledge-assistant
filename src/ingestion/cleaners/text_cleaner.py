"""Cleaning utilities for extracted document content."""

import re
from typing import Optional


def clean_text(text: Optional[str]) -> str:
    """Normalize extracted text while preserving meaningful content."""
    if text is None:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def is_meaningful_text(text: Optional[str]) -> bool:
    """Return True when text contains meaningful non-whitespace content."""
    if text is None:
        return False

    return bool(clean_text(text))
