"""
DevLensX Core Security & Cryptographic Validation Module
Enforces unique random salts per password, secure JWT signing, and canonical path traversal validation.
"""

import os
import hashlib
import hmac
import base64
import json
import time
from typing import Optional, Dict, Any
from devlensx.core.config import JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hashes password using PBKDF2 HMAC SHA256 with a unique random salt per user."""
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hashed).decode("utf-8")
    return f"{salt_b64}:{hash_b64}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a plain password against stored salt:hash payload."""
    try:
        if ":" not in stored_hash:
            return False
        salt_b64, hash_b64 = stored_hash.split(":", 1)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        computed_hash = hash_password(plain_password, salt)
        return hmac.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """Canonical path validation preventing directory traversal and Zip Slip attacks."""
    try:
        # Reject null bytes
        if "\x00" in target_path:
            return False
        # Reject URL-encoded traversal attempts
        normalized = target_path.replace("%2e", ".").replace("%2E", ".").replace("%2f", "/").replace("%2F", "/")
        # Reject path traversal sequences
        if any(part in ("..",) for part in normalized.split("/")):
            return False
        if any(part in ("..",) for part in normalized.split("\\")):
            return False
        # Reject absolute paths
        if os.path.isabs(normalized):
            return False
        # Windows drive letters
        if len(normalized) >= 2 and normalized[1] == ":":
            return False
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(os.path.join(base_dir, normalized))
        return os.path.commonpath([base_real, target_real]) == base_real
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_delta_minutes: Optional[int] = None) -> str:
    """Creates a signed JWT access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    
    expire_sec = time.time() + ((expires_delta_minutes or ACCESS_TOKEN_EXPIRE_MINUTES) * 60)
    payload = dict(data)
    payload["exp"] = int(expire_sec)
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    
    unsigned_token = f"{_b64url_encode(header_json)}.{_b64url_encode(payload_json)}"
    signature = hmac.new(JWT_SECRET.encode("utf-8"), unsigned_token.encode("utf-8"), hashlib.sha256).digest()
    
    return f"{unsigned_token}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and verifies a signed JWT access token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, sig_b64 = parts
        unsigned_token = f"{header_b64}.{payload_b64}"
        
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), unsigned_token.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        if payload.get("exp") and time.time() > payload["exp"]:
            return None
        
        return payload
    except Exception:
        return None


def wiki_content_sanitize(raw: str, max_len: int = 2000) -> str:
    """Sanitizes wiki heading/content to prevent XSS via html.escape.

    Used by wiki Change Impact and other pages to ensure attacker-controlled
    strings (e.g., class names, claim text, headings) are escaped before storage.
    """
    import html as _html
    if raw is None:
        return ""
    return _html.escape(str(raw))[:max_len]


def wiki_heading_sanitize(raw: str, max_len: int = 200) -> str:
    """Sanitizes wiki heading (shorter limit) via html.escape."""
    import html as _html
    if raw is None:
        return ""
    return _html.escape(str(raw))[:max_len]
