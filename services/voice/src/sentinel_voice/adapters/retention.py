"""In-process retention store; mode none stores nothing."""

from __future__ import annotations

from sentinel_voice.contracts import RetentionMode
from sentinel_voice.domain.retention import assert_retention_allows_store


class InMemoryRetentionStore:
    def __init__(self, mode: RetentionMode = "none") -> None:
        self._mode = mode
        self._rows: list[dict[str, str]] = []

    @property
    def mode(self) -> RetentionMode:
        return self._mode

    def remember(self, *, original_text: str, language: str, request_id: str) -> None:
        if self._mode == "none":
            return
        assert_retention_allows_store(self._mode)
        # Never persist secrets; callers must already redact.
        self._rows.append(
            {
                "request_id": request_id,
                "language": language,
                "original_text": original_text,
                "retention_mode": self._mode,
            }
        )

    def stored(self) -> tuple[dict[str, str], ...]:
        return tuple(self._rows)
