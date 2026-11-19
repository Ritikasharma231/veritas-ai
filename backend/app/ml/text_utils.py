"""Text preprocessing utilities.

Cleaning is deliberately conservative: we strip markup/URLs noise but preserve
linguistic signals (punctuation runs, capitalization, casing) that are
informative for misinformation analysis. Tokenization for the transformer is
handled by the model's own tokenizer.
"""
import html
import re
import unicodedata

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_unicode(text: str) -> str:
    """NFKC normalization; keeps casing and punctuation intact."""
    return unicodedata.normalize("NFKC", text)


def strip_html(text: str) -> str:
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    return text


def replace_urls(text: str, placeholder: str = " ") -> str:
    return _URL_RE.sub(placeholder, text)


def clean_text(text: str, *, strip_urls: bool = True) -> str:
    """Clean raw input for model consumption and storage."""
    if not text:
        return ""
    text = normalize_unicode(text)
    text = strip_html(text)
    if strip_urls:
        text = replace_urls(text)
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def headline_and_body(text: str) -> tuple[str, str]:
    """Split input into headline (first non-empty line) and body."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return "", ""
    return lines[0], "\n".join(lines[1:])


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # prefer cutting at a sentence/word boundary
    for sep in ("\n\n", ". ", "! ", "? ", " "):
        idx = cut.rfind(sep)
        if idx > max_chars * 0.6:
            return cut[: idx + len(sep)].strip()
    return cut.strip()
