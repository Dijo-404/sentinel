"""Password and session-token helpers (stdlib PBKDF2 + SHA-256)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

MIN_PASSWORD_LENGTH = 8


def normalize_email(email: str) -> str:
    return email.strip().lower()


def assert_password_acceptable(password: str) -> None:
    """Reject empty or short passwords on register / new-invite accept."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")


def hash_password(password: str, *, iterations: int = 210_000) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters_s, salt, digest = encoded.split("$", 3)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iters_s)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)


def mint_token() -> str:
    return secrets.token_urlsafe(32)


def mint_numeric_code(*, digits: int = 6) -> str:
    """Sandbox MFA / verify / reset code (numeric string, zero-padded)."""
    if digits < 4 or digits > 10:
        raise ValueError("digits must be between 4 and 10")
    return f"{secrets.randbelow(10**digits):0{digits}d}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
