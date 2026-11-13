"""Module-owned PostgreSQL job store, decision store, and result outbox."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from sentinel_workflow.application.errors import IdempotencyConflictError
from sentinel_workflow.domain.types import Approval

metadata = MetaData(schema="workflow")


class Base(DeclarativeBase):
    metadata = metadata


class JobRow(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("tenant_id", "job_key", name="uq_jobs_tenant_key"),)

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    job_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="accepted")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class OutboxRow(Base):
    __tablename__ = "result_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", "event_key", name="uq_outbox_event"),
    )

    outbox_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class DecisionRow(Base):
    __tablename__ = "decisions"

    thread_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    approval_json: Mapped[str] = mapped_column(Text, nullable=False)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, hide_parameters=True)


def migrate(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS workflow"))
    Base.metadata.create_all(engine)


class SqlJobStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def accept_job(
        self,
        *,
        tenant_id: str,
        job_key: str,
        payload: dict[str, Any],
        thread_id: str,
    ) -> tuple[str, bool]:
        import hashlib

        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self._sessions() as session:
            existing = session.scalar(
                select(JobRow).where(JobRow.tenant_id == tenant_id, JobRow.job_key == job_key)
            )
            if existing is not None:
                if existing.payload_digest != digest:
                    raise IdempotencyConflictError()
                return existing.job_id, False
            job_id = f"job-{uuid.uuid4().hex[:12]}"
            session.add(
                JobRow(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    job_key=job_key,
                    payload_json=json.dumps(payload, sort_keys=True),
                    payload_digest=digest,
                    thread_id=thread_id,
                    status="accepted",
                )
            )
            session.commit()
            return job_id, True

    def get_job(self, tenant_id: str, job_key: str) -> dict[str, Any] | None:
        with self._sessions() as session:
            row = session.scalar(
                select(JobRow).where(JobRow.tenant_id == tenant_id, JobRow.job_key == job_key)
            )
            if row is None:
                return None
            return {
                "job_id": row.job_id,
                "tenant_id": row.tenant_id,
                "job_key": row.job_key,
                "payload": json.loads(row.payload_json),
                "thread_id": row.thread_id,
                "status": row.status,
                "detail": row.detail,
            }

    def mark_job_status(self, job_id: str, status: str, detail: str | None = None) -> None:
        with self._sessions() as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return
            row.status = status
            row.detail = detail
            session.commit()


class SqlOutbox:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def enqueue_result(
        self,
        *,
        tenant_id: str,
        case_id: str,
        event_key: str,
        payload: dict[str, Any],
    ) -> None:
        with self._sessions() as session:
            existing = session.scalar(
                select(OutboxRow).where(
                    OutboxRow.tenant_id == tenant_id,
                    OutboxRow.case_id == case_id,
                    OutboxRow.event_key == event_key,
                )
            )
            if existing is not None:
                # Identical event_key is idempotent; do not overwrite a different payload.
                if existing.payload_json != json.dumps(payload, sort_keys=True):
                    raise IdempotencyConflictError("Outbox event_key conflict")
                return
            session.add(
                OutboxRow(
                    outbox_id=f"outbox-{uuid.uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    case_id=case_id,
                    event_key=event_key,
                    payload_json=json.dumps(payload, sort_keys=True),
                    status="pending",
                )
            )
            session.commit()

    def pending(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._sessions() as session:
            rows = session.scalars(
                select(OutboxRow)
                .where(OutboxRow.status == "pending")
                .order_by(OutboxRow.created_at)
                .limit(limit)
            ).all()
            return [
                {
                    "outbox_id": r.outbox_id,
                    "tenant_id": r.tenant_id,
                    "case_id": r.case_id,
                    "event_key": r.event_key,
                    "payload": json.loads(r.payload_json),
                    "attempts": r.attempts,
                }
                for r in rows
            ]

    def mark_delivered(self, outbox_id: str) -> None:
        with self._sessions() as session:
            row = session.get(OutboxRow, outbox_id)
            if row is None:
                return
            row.status = "delivered"
            session.commit()

    def mark_retry(self, outbox_id: str, error: str) -> None:
        with self._sessions() as session:
            row = session.get(OutboxRow, outbox_id)
            if row is None:
                return
            row.attempts += 1
            row.last_error = error
            session.commit()


class SqlDecisionStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def put_decision(self, thread_id: str, approval: Approval, principal_id: str) -> None:
        with self._sessions() as session:
            row = session.get(DecisionRow, thread_id)
            payload = approval.model_dump(exclude_none=True)
            if row is None:
                session.add(
                    DecisionRow(
                        thread_id=thread_id,
                        tenant_id="unknown",
                        approval_json=json.dumps(payload, sort_keys=True),
                        principal_id=principal_id,
                    )
                )
            else:
                row.approval_json = json.dumps(payload, sort_keys=True)
                row.principal_id = principal_id
            session.commit()

    def get_decision(self, thread_id: str) -> dict[str, Any] | None:
        with self._sessions() as session:
            row = session.get(DecisionRow, thread_id)
            if row is None:
                return None
            return {
                "approval": json.loads(row.approval_json),
                "principal_id": row.principal_id,
            }
