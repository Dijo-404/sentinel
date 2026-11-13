"""Dispute state transitions and evidence-gate rules."""

from __future__ import annotations

from datetime import UTC, datetime

from .types import (
    REQUIRED_EVIDENCE_KINDS,
    DisputeCase,
    DisputeStatus,
    EvidencePacket,
    TerminalStatus,
)

OPEN_STATUSES: frozenset[DisputeStatus] = frozenset({"OPEN", "EVIDENCE_PENDING"})
TERMINAL: frozenset[DisputeStatus] = frozenset({"WON", "LOST", "WITHDRAWN"})


def parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def format_rfc3339(instant: datetime) -> str:
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_overdue(*, deadline_at: str, now: datetime) -> bool:
    return now >= parse_rfc3339(deadline_at)


def missing_required_kinds(packets: tuple[EvidencePacket, ...]) -> tuple[str, ...]:
    present = {kind for packet in packets for kind in packet.kinds}
    return tuple(kind for kind in REQUIRED_EVIDENCE_KINDS if kind not in present)


def after_packet_collected(dispute: DisputeCase) -> DisputeStatus:
    if dispute.status == "OPEN":
        return "EVIDENCE_PENDING"
    return dispute.status


def assert_can_collect(dispute: DisputeCase) -> None:
    if dispute.status in TERMINAL or dispute.status == "SUBMITTED":
        raise ValueError(f"Cannot collect evidence in status {dispute.status}")


def assert_can_submit(
    dispute: DisputeCase,
    packets: tuple[EvidencePacket, ...],
    *,
    now: datetime,
) -> None:
    if dispute.status not in OPEN_STATUSES:
        raise ValueError(f"Cannot submit from status {dispute.status}")
    if is_overdue(deadline_at=dispute.deadline_at, now=now):
        raise DeadlineError("Dispute deadline has passed")
    missing = missing_required_kinds(packets)
    if missing:
        raise MissingEvidenceError(missing)


def assert_can_resolve(dispute: DisputeCase, outcome: TerminalStatus) -> None:
    if outcome == "WITHDRAWN":
        if dispute.status in TERMINAL:
            raise ValueError(f"Cannot withdraw from status {dispute.status}")
        return
    if dispute.status != "SUBMITTED":
        raise ValueError(f"Cannot resolve to {outcome} from status {dispute.status}")


class MissingEvidenceError(Exception):
    def __init__(self, missing: tuple[str, ...]):
        self.missing = missing
        super().__init__(f"Missing required evidence kinds: {', '.join(missing)}")


class DeadlineError(Exception):
    pass
