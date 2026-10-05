"""Comment Serialization Repair Engine.

Ported and extended from Alibaba's OpenCodeReview (internal/tool/comment_args_repair.go).
Solves the #1 failure mode in LLM code reviews: model outputs malformed JSON with
unescaped prose quotes, raw control characters, broken backslashes, trailing commas,
or truncated tokens.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

CONTENT_FIELD_PATTERN = re.compile(r'"content"\s*:')

KNOWN_COMMENT_FIELDS: Set[str] = {
    "content",
    "existing_code",
    "suggestion_code",
    "category",
    "severity",
    "path",
    "thinking",
    "line",
    "start_line",
    "end_line",
    "evidence_refs",
    "requires_user_action",
    "verification_status",
}

COMMENT_TEXT_FIELDS: Tuple[str, ...] = (
    "content",
    "existing_code",
    "suggestion_code",
    "path",
)


def is_hex_digit(c: str) -> bool:
    return c in "0123456789abcdefABCDEF"


def is_legal_escape(s: str, i: int) -> bool:
    """Check whether s[i] opens a valid JSON escape sequence after a backslash."""
    if i >= len(s):
        return False
    ch = s[i]
    if ch in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't'):
        return True
    if ch == 'u':
        if i + 5 > len(s):
            return False
        return all(is_hex_digit(c) for c in s[i + 1 : i + 5])
    return False


def escape_control(c: str) -> str:
    """Return JSON escape representation for a control character (< 0x20)."""
    if c == '\n':
        return r'\n'
    if c == '\r':
        return r'\r'
    if c == '\t':
        return r'\t'
    if c == '\b':
        return r'\b'
    if c == '\f':
        return r'\f'
    code = ord(c)
    return f"\\u{code:04x}"


def next_significant_char(s: str, i: int) -> int:
    """Return the index of the next non-whitespace character at or after i, or -1."""
    while i < len(s):
        if s[i] not in (' ', '\t', '\r', '\n'):
            return i
        i += 1
    return -1


def is_json_structural(c: str) -> bool:
    """Check whether char c can legally follow a string's closing quote in JSON."""
    return c in (',', '}', ']', ':')


def repair_serialized_comments(s: str) -> Tuple[str, int]:
    """Scan and escape unescaped prose quotes, bare control chars, and illegal backslashes.

    A real string terminator is always followed by ',', '}', ']', ':', or end of text.
    A quote followed by anything else in prose is treated as an unescaped inner quote.
    Returns (repaired_string, escaped_count).
    """
    out: List[str] = []
    escaped = 0
    in_string = False
    i = 0
    n = len(s)

    while i < n:
        c = s[i]
        if not in_string:
            if c == '"':
                in_string = True
            out.append(c)
            i += 1
            continue

        if c == '\\':
            if is_legal_escape(s, i + 1):
                out.append(c)
                i += 1
                out.append(s[i])
                i += 1
                continue
            out.append(r'\\')
            escaped += 1
            i += 1
        elif c == '"':
            nxt = next_significant_char(s, i + 1)
            if nxt < 0 or is_json_structural(s[nxt]):
                in_string = False
                out.append(c)
            else:
                out.append(r'\"')
                escaped += 1
            i += 1
        elif ord(c) < 0x20:
            out.append(escape_control(c))
            escaped += 1
            i += 1
        else:
            out.append(c)
            i += 1

    return "".join(out), escaped


def has_odd_quotes(v: str) -> bool:
    """Check if value has an odd number of unescaped quotes indicating truncation."""
    unescaped = 0
    escaped = False
    for char in v:
        if char == '\\':
            escaped = not escaped
        elif char == '"':
            if not escaped:
                unescaped += 1
            escaped = False
        else:
            escaped = False
    return unescaped % 2 == 1


def has_suspect_truncation(entries: List[Dict[str, Any]]) -> bool:
    """Reject batches where a misjudged terminator may have cut fields short."""
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        for field in COMMENT_TEXT_FIELDS:
            val = raw.get(field)
            if isinstance(val, str) and has_odd_quotes(val):
                return True
    return False


def repaired_comments_acceptable(entries: List[Any], original: str) -> bool:
    """Validate that repaired comments retain integrity and didn't fuse objects."""
    if not entries:
        return False

    for raw in entries:
        if not isinstance(raw, dict):
            return False
        content = raw.get("content")
        if not isinstance(content, str) or not content.strip():
            return False
        for field in raw.keys():
            if field not in KNOWN_COMMENT_FIELDS:
                return False

    orig_content_matches = len(CONTENT_FIELD_PATTERN.findall(original))
    if orig_content_matches > 0 and len(entries) < orig_content_matches:
        return False

    return True


def repair_trailing_commas_and_brackets(s: str) -> str:
    """Remove trailing commas before closing braces/brackets and auto-close unclosed structures."""
    cleaned = re.sub(r',\s*([}\]])', r'\1', s)
    open_brackets = cleaned.count('[') - cleaned.count(']')
    open_braces = cleaned.count('{') - cleaned.count('}')

    if open_braces > 0:
        cleaned += '}' * open_braces
    if open_brackets > 0:
        cleaned += ']' * open_brackets
    return cleaned


def extract_json_payload(raw_text: str) -> str:
    """Extract JSON payload from markdown fences or surrounding prose."""
    s = raw_text.strip()
    if s.startswith("```"):
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()
    first_bracket = s.find('[')
    first_brace = s.find('{')
    start = -1
    if first_bracket != -1 and first_brace != -1:
        start = min(first_bracket, first_brace)
    elif first_bracket != -1:
        start = first_bracket
    elif first_brace != -1:
        start = first_brace

    last_bracket = s.rfind(']')
    last_brace = s.rfind('}')
    end = max(last_bracket, last_brace)

    if start != -1 and end != -1 and end > start:
        return s[start : end + 1]
    return s


def parse_and_repair_comments(
    raw_text: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Robustly parse serialized LLM comments, repairing malformed JSON if needed.

    Returns (comments_list, repair_metadata).
    """
    metadata: Dict[str, Any] = {
        "repaired": False,
        "escaped_chars": 0,
        "error": None,
        "fallback_used": False,
    }

    if not raw_text or not raw_text.strip():
        return [], metadata

    payload = extract_json_payload(raw_text)

    # 1. Direct JSON parse attempt
    try:
        data = json.loads(payload)
        if isinstance(data, list):
            return data, metadata
        if isinstance(data, dict):
            for k in ("comments", "findings", "reviews"):
                if isinstance(data.get(k), list):
                    return data[k], metadata
            return [data], metadata
    except Exception as exc:
        metadata["initial_error"] = str(exc)

    # 2. Repair serialized quotes, controls, backslashes
    repaired_str, escaped_count = repair_serialized_comments(payload)
    repaired_str = repair_trailing_commas_and_brackets(repaired_str)

    try:
        data = json.loads(repaired_str)
        metadata["repaired"] = True
        metadata["escaped_chars"] = escaped_count

        comments: List[Dict[str, Any]] = []
        if isinstance(data, list):
            comments = data
        elif isinstance(data, dict):
            for k in ("comments", "findings", "reviews"):
                if isinstance(data.get(k), list):
                    comments = data[k]
                    break
            else:
                comments = [data]

        if repaired_comments_acceptable(comments, payload) and not has_suspect_truncation(comments):
            return comments, metadata
        else:
            metadata["warning"] = "Repaired comments failed acceptance check or suspect truncation"
    except Exception as exc:
        metadata["repaired_error"] = str(exc)

    # 3. Last-ditch object extractor
    recovered_objects: List[Dict[str, Any]] = []
    for obj_match in re.finditer(r'\{[^{}]*"(?:content|suggestion_code)"[^{}]*\}', payload):
        try:
            cand = json.loads(obj_match.group(0))
            if isinstance(cand, dict) and "content" in cand:
                recovered_objects.append(cand)
        except Exception:
            continue

    if recovered_objects:
        metadata["fallback_used"] = True
        metadata["repaired"] = True
        return recovered_objects, metadata

    metadata["error"] = "Failed to parse or repair comments JSON"
    return [], metadata
