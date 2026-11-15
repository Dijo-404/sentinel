"""Optional HTTP model reply. Fail closed — never invent success."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..application.errors import PeerUnavailableError, ValidationError


class HttpModelReply:
    """POST {text} → {text, evidence_mode}. Requires operator-configured base URL."""

    def __init__(self, base_url: str, *, timeout_s: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def generate(self, *, text: str) -> tuple[str, str]:
        payload = json.dumps({"text": text}).encode("utf-8")
        req = Request(
            f"{self._base}/v1/replies",
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self._timeout_s) as resp:  # noqa: S310 — operator URL
                raw = resp.read().decode("utf-8")
        except (OSError, URLError, HTTPError, TimeoutError) as exc:
            raise PeerUnavailableError(f"assistant model peer unavailable: {exc}") from exc
        try:
            data: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError("assistant model peer returned malformed JSON") from exc
        if not isinstance(data, dict):
            raise ValidationError("assistant model peer returned non-object")
        reply = data.get("text")
        mode = data.get("evidence_mode")
        if not isinstance(reply, str) or not reply.strip():
            raise ValidationError("assistant model peer missing text")
        if mode not in {"sandbox", "recorded", "live", "fake"}:
            raise ValidationError("assistant model peer missing evidence_mode")
        return reply.strip(), mode
