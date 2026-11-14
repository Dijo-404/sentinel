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


# Ambiguity-safe alphabet (no 0/O/1/I). 32^8 ≈ 1.1e12 candidates.
_CHALLENGE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CHALLENGE_CODE_LENGTH = 8
# Fail-closed: lock/consume challenge after this many bad codes (inclusive).
MAX_CHALLENGE_ATTEMPTS = 5


def mint_challenge_code(*, length: int = CHALLENGE_CODE_LENGTH) -> str:
    """Sandbox verify / MFA / reset code: 8+ char alphanumeric."""
    if length < 8:
        raise ValueError("challenge code length must be at least 8")
    return "".join(secrets.choice(_CHALLENGE_ALPHABET) for _ in range(length))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
