"""SQLite dispute store for durable real-peers runs (stdlib only)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ..application.errors import ConflictError
from ..domain.types import DisputeCase, EvidencePacket


def sqlite_path_from_url(database_url: str) -> Path:
    url = database_url.strip()
    if not url:
        raise ValueError("database URL is empty")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///"))
    return Path(url)


def _fingerprint(dispute: DisputeCase) -> str:
    return "|".join(
        [
            dispute.tenant_id,
            dispute.merchant_ref,
            dispute.case_id,
            dispute.reason_code,
            dispute.deadline_at,
            dispute.order_reference,
        ]
    )


def _dispute_dict(dispute: DisputeCase) -> dict:
    return {
        "dispute_id": dispute.dispute_id,
        "tenant_id": dispute.tenant_id,
        "merchant_ref": dispute.merchant_ref,
        "case_id": dispute.case_id,
        "reason_code": dispute.reason_code,
        "deadline_at": dispute.deadline_at,
        "evidence_packet_ids": list(dispute.evidence_packet_ids),
        "status": dispute.status,
        "order_reference": dispute.order_reference,
        "case_revision": dispute.case_revision,
    }


def _dispute_from(raw: dict) -> DisputeCase:
    return DisputeCase(
        dispute_id=str(raw["dispute_id"]),
        tenant_id=str(raw["tenant_id"]),
        merchant_ref=str(raw["merchant_ref"]),
        case_id=str(raw["case_id"]),
        reason_code=str(raw["reason_code"]),
        deadline_at=str(raw["deadline_at"]),
        evidence_packet_ids=tuple(raw.get("evidence_packet_ids") or ()),
        status=raw["status"],
        order_reference=str(raw.get("order_reference") or ""),
        case_revision=int(raw.get("case_revision") or 1),
    )


def _packet_dict(packet: EvidencePacket) -> dict:
    return {
        "packet_id": packet.packet_id,
        "dispute_id": packet.dispute_id,
        "case_id": packet.case_id,
        "evidence_ids": list(packet.evidence_ids),
        "kinds": list(packet.kinds),
        "assembled_at": packet.assembled_at,
    }


def _packet_from(raw: dict) -> EvidencePacket:
    return EvidencePacket(
        packet_id=str(raw["packet_id"]),
        dispute_id=str(raw["dispute_id"]),
        case_id=str(raw["case_id"]),
        evidence_ids=tuple(raw.get("evidence_ids") or ()),
        kinds=tuple(raw.get("kinds") or ()),
        assembled_at=str(raw["assembled_at"]),
    )


class SqliteDisputeStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if self._path.parent and str(self._path.parent) not in {"", "."}:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def from_url(cls, database_url: str) -> SqliteDisputeStore:
        return cls(sqlite_path_from_url(database_url))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS disputes (
                    dispute_id TEXT PRIMARY KEY,
                    body_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_packets (
                    packet_id TEXT PRIMARY KEY,
                    dispute_id TEXT NOT NULL,
                    body_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dispute_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    dispute_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create(self, dispute: DisputeCase, *, idempotency_key: str | None) -> DisputeCase:
        if idempotency_key:
            fingerprint = _fingerprint(dispute)
            with self._connect() as conn:
                existing = conn.execute(
                    """
                    SELECT dispute_id, fingerprint FROM dispute_idempotency
                    WHERE idempotency_key = ?
                    """,
                    (idempotency_key,),
                ).fetchone()
                if existing is not None:
                    if existing["fingerprint"] != fingerprint:
                        raise ConflictError("Idempotency-Key already used with a different payload")
                    row = conn.execute(
                        "SELECT body_json FROM disputes WHERE dispute_id = ?",
                        (existing["dispute_id"],),
                    ).fetchone()
                    if row is None:
                        raise ConflictError("Idempotency mapping missing dispute")
                    return _dispute_from(json.loads(row["body_json"]))
                conn.execute(
                    """
                    INSERT INTO dispute_idempotency (idempotency_key, dispute_id, fingerprint)
                    VALUES (?, ?, ?)
                    """,
                    (idempotency_key, dispute.dispute_id, fingerprint),
                )
                conn.execute(
                    """
                    INSERT INTO disputes (dispute_id, body_json) VALUES (?, ?)
                    """,
                    (dispute.dispute_id, json.dumps(_dispute_dict(dispute))),
                )
                conn.commit()
            return dispute
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO disputes (dispute_id, body_json) VALUES (?, ?)
                """,
                (dispute.dispute_id, json.dumps(_dispute_dict(dispute))),
            )
            conn.commit()
        return dispute

    def get(self, dispute_id: str) -> DisputeCase | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body_json FROM disputes WHERE dispute_id = ?",
                (dispute_id,),
            ).fetchone()
        if row is None:
            return None
        return _dispute_from(json.loads(row["body_json"]))

    def list(self, *, tenant_id: str, merchant_ref: str) -> tuple[DisputeCase, ...]:
        with self._connect() as conn:
            rows = conn.execute("SELECT body_json FROM disputes").fetchall()
        items = [
            dispute
            for dispute in (_dispute_from(json.loads(row["body_json"])) for row in rows)
            if dispute.tenant_id == tenant_id and dispute.merchant_ref == merchant_ref
        ]
        return tuple(sorted(items, key=lambda d: d.dispute_id))

    def save(self, dispute: DisputeCase) -> DisputeCase:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM disputes WHERE dispute_id = ?",
                (dispute.dispute_id,),
            ).fetchone()
            if existing is None:
                raise ConflictError("Unknown dispute")
            conn.execute(
                """
                UPDATE disputes SET body_json = ? WHERE dispute_id = ?
                """,
                (json.dumps(_dispute_dict(dispute)), dispute.dispute_id),
            )
            conn.commit()
        return dispute

    def save_packet(self, packet: EvidencePacket) -> EvidencePacket:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evidence_packets (packet_id, dispute_id, body_json)
                VALUES (?, ?, ?)
                ON CONFLICT(packet_id) DO UPDATE SET
                    dispute_id = excluded.dispute_id,
                    body_json = excluded.body_json
                """,
                (packet.packet_id, packet.dispute_id, json.dumps(_packet_dict(packet))),
            )
            conn.commit()
        return packet

    def list_packets(self, dispute_id: str) -> tuple[EvidencePacket, ...]:
        dispute = self.get(dispute_id)
        if dispute is None:
            return ()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT body_json FROM evidence_packets WHERE dispute_id = ?
                """,
                (dispute_id,),
            ).fetchall()
        packets = [_packet_from(json.loads(row["body_json"])) for row in rows]
        by_id = {packet.packet_id: packet for packet in packets}
        return tuple(
            by_id[packet_id] for packet_id in dispute.evidence_packet_ids if packet_id in by_id
        )
