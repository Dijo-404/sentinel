"""Ingest and list tenant-scoped telemetry signals (never financial audit)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ..domain.types import FEED_LIMIT, Principal, Signal
from .errors import UnauthorizedError, ValidationError
from .ports import SignalStore


class ObservabilityService:
    def __init__(self, store: SignalStore):
        self._store = store

    def list_signals(self, principal: Principal) -> list[Signal]:
        _require_admin(principal)
        return self._store.list_signals(principal.tenant_id, limit=FEED_LIMIT)

    def list_spans(self, principal: Principal) -> list[Signal]:
        return [s for s in self.list_signals(principal) if s.kind == "span"]

    def ingest(self, principal: Principal, body: dict[str, Any]) -> int:
        _require_admin(principal)
        if not isinstance(body, dict):
            raise ValidationError("ingest body must be an object")
        signals = self._parse_ingest_body(body, tenant_id=principal.tenant_id)
        for signal in signals:
            self._store.put(signal)
        return len(signals)

    def _parse_ingest_body(self, body: dict[str, Any], *, tenant_id: str) -> list[Signal]:
        if "signals" in body:
            raw_list = body["signals"]
            if not isinstance(raw_list, list):
                raise ValidationError("signals must be an array")
            return [self._signal_from_wire(item, tenant_id=tenant_id) for item in raw_list]
        if "spans" in body:
            raw_list = body["spans"]
            if not isinstance(raw_list, list):
                raise ValidationError("spans must be an array")
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            out: list[Signal] = []
            for item in raw_list:
                if not isinstance(item, dict):
                    raise ValidationError("span must be an object")
                name = item.get("name")
                if not isinstance(name, str) or not name:
                    raise ValidationError("span.name must be a nonempty string")
                attributes = item.get("attributes") or {}
                events = item.get("events") or []
                if not isinstance(attributes, dict):
                    raise ValidationError("span.attributes must be an object")
                if not isinstance(events, list):
                    raise ValidationError("span.events must be an array")
                out.append(
                    Signal(
                        signal_id=f"sig-{uuid.uuid4().hex[:16]}",
                        tenant_id=tenant_id,
                        kind="span",
                        name=name,
                        attributes=dict(attributes),
                        events=list(events),
                        recorded_at=now,
                    )
                )
            return out
        raise ValidationError("ingest requires signals or spans")

    def _signal_from_wire(self, item: Any, *, tenant_id: str) -> Signal:
        if not isinstance(item, dict):
            raise ValidationError("signal must be an object")
        signal_id = item.get("signal_id")
        if not isinstance(signal_id, str) or not signal_id:
            raise ValidationError("signal_id must be a nonempty string")
        kind = item.get("kind", "span")
        if kind not in ("span", "metric"):
            raise ValidationError("kind must be span or metric")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValidationError("name must be a nonempty string")
        attributes = item.get("attributes") or {}
        events = item.get("events") or []
        recorded_at = item.get("recorded_at") or ""
        if not isinstance(attributes, dict):
            raise ValidationError("attributes must be an object")
        if not isinstance(events, list):
            raise ValidationError("events must be an array")
        if not isinstance(recorded_at, str):
            raise ValidationError("recorded_at must be a string")
        return Signal(
            signal_id=signal_id,
            tenant_id=tenant_id,
            kind=kind,  # type: ignore[arg-type]
            name=name,
            attributes=dict(attributes),
            events=list(events),
            recorded_at=recorded_at,
        )


def _require_admin(principal: Principal) -> None:
    if not principal.is_admin():
        raise UnauthorizedError("platform admin role required")
