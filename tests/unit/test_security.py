"""
DevLensX Unit Tests: Cryptographic Security & Path Traversal Validation
"""

import sys
import os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.core.security import hash_password, verify_password, is_safe_path, create_access_token, decode_access_token


def test_password_hashing_and_verification():
    h = hash_password("SecurePassword123")
    assert ":" in h, "Password hash must contain salt separator!"
    assert verify_password("SecurePassword123", h), "Valid password verification failed!"
    assert not verify_password("WrongPassword", h), "Invalid password accepted!"
    print("  🟢 Unit Test: Password Hashing & Verification Passed")


def test_canonical_path_traversal():
    base_dir = os.path.realpath(".")
    assert is_safe_path(base_dir, "devlensx/core/config.py"), "Valid relative path rejected!"
    assert not is_safe_path(base_dir, "../../secret.txt"), "Path traversal attempt allowed!"
    print("  🟢 Unit Test: Canonical Path Traversal Protection Passed")


def test_jwt_token_creation_and_decoding():
    token = create_access_token({"sub": "123", "email": "test@devlensx.local"})
    payload = decode_access_token(token)
    assert payload is not None, "Valid JWT decoding failed!"
    assert payload.get("sub") == "123", "JWT subject claim mismatch!"
    assert payload.get("email") == "test@devlensx.local", "JWT email claim mismatch!"
    print("  🟢 Unit Test: JWT Token Signing & Verification Passed")


if __name__ == "__main__":
    print("Running Unit Test Suite: Security...")
    test_password_hashing_and_verification()
    test_canonical_path_traversal()
    test_jwt_token_creation_and_decoding()
    print("Unit Test Suite Security Complete: 100% Passed\n")
