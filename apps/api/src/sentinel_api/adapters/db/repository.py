"""PostgreSQL case repository."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError

from sentinel_api.adapters.db import schema
from sentinel_api.domain.rules import idempotency_payload_equal
from sentinel_api.domain.types import (
    CONTRACT_VERSION,
    Case,
    CaseCreate,
    CaseCreated,
    CaseEvent,
    CaseInput,
    CaseMessage,
    CaseResult,
    DomainError,
    Principal,
    WorkflowRequest,
)

# Claimed jobs become reclaimable after this lease window (crash recovery).
WORKFLOW_JOB_LEASE_SECONDS = 30

# Ops history alias: terminal case statuses for supervisor History pages.
HISTORY_STATUSES: tuple[str, ...] = ("VERIFIED_RESOLVED", "CLOSED_NO_ACTION")


def _resolve_status_filter(status: str | None) -> tuple[str, ...] | None:
    """Expand HISTORY alias and optional comma-separated CaseState filters."""
    if not status:
        return None
    if status == "HISTORY":
        return HISTORY_STATUSES
    parts = tuple(part.strip() for part in status.split(",") if part.strip())
    return parts or None


def _hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json_loads(raw: str) -> Any:
    return json.loads(raw)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _workflow_request_from_payload(data: dict[str, Any]) -> WorkflowRequest:
    return WorkflowRequest(
        case_id=data["case_id"],
        case_revision=data["case_revision"],
        job_key=data["job_key"],
        event=data["event"],
        order_reference=data.get("order_reference"),
    )


def _outbox_row_id(tenant_id: str, job_key: str) -> str:
    return hashlib.sha256(f"{tenant_id}:{job_key}".encode()).hexdigest()[:32]


class SqlCaseRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def ping(self) -> None:
        with self._engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")

    def create_case(
        self,
        *,
        principal: Principal,
        create: CaseCreate,
        idempotency_key: str,
        case_id: str,
        message_id: str,
        event_id: str,
        occurred_at: str,
        start_job: WorkflowRequest | None = None,
    ) -> tuple[CaseCreated, Case, bool]:
        request_payload = {
            "message": create.message,
            "language": create.language,
            "order_reference": create.order_reference,
            "channel": create.channel,
        }
        request_hash = _hash(request_payload)
        subject_ref = (
            principal.subject_refs[0]
            if principal.subject_refs
            else f"subject:{principal.principal_id}"
        )
        with self._engine.begin() as conn:
            existing = (
                conn.execute(
                    select(schema.idempotency_keys).where(
                        schema.idempotency_keys.c.tenant_id == principal.tenant_id,
                        schema.idempotency_keys.c.scope == "POST:/v1/cases",
                        schema.idempotency_keys.c.idempotency_key == idempotency_key,
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise DomainError(
                        "IDEMPOTENCY_CONFLICT",
                        "Key already used with a different payload",
                        409,
                    )
                created = CaseCreated(**_json_loads(existing["response_json"]))
                case = self._load_case(conn, principal.tenant_id, created.case_id)
                assert case is not None
                return created, case, True

            case = Case(
                case_id=case_id,
                revision=1,
                status="RECEIVED",
                language=create.language,
                intent="UNCLASSIFIED",
                evidence_ids=(),
            )
            created = CaseCreated(
                case_id=case_id, status="RECEIVED", status_url=f"/v1/cases/{case_id}"
            )
            conn.execute(
                schema.cases.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    revision=1,
                    status="RECEIVED",
                    language=create.language,
                    intent="UNCLASSIFIED",
                    evidence_ids_json="[]",
                    action_id=None,
                    subject_ref=subject_ref,
                    order_reference=create.order_reference,
                    original_text=create.message,
                    channel=create.channel,
                )
            )
            message = CaseMessage(
                message_id=message_id,
                text=create.message,
                language=create.language,
                author="CUSTOMER" if principal.has_role("customer") else "OPERATOR",
                occurred_at=occurred_at,
            )
            conn.execute(
                schema.messages.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    message_id=message_id,
                    text=message.text,
                    language=message.language,
                    author=message.author,
                    occurred_at=occurred_at,
                    revision_introduced=1,
                    sequence=1,
                )
            )
            snapshot = CaseInput(
                case_id=case_id,
                case_revision=1,
                original_text=create.message,
                language=create.language,
                order_reference=create.order_reference,
                messages=(message,),
            )
            conn.execute(
                schema.input_snapshots.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    case_revision=1,
                    snapshot_json=_json_dumps(snapshot.to_dict()),
                )
            )
            payload = {
                "status": "RECEIVED",
                "evidence_ids": [],
                "reason_code": "RECEIVED",
            }
            conn.execute(
                schema.events.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    sequence=1,
                    event_id=event_id,
                    case_revision=1,
                    type="CASE_CREATED",
                    occurred_at=occurred_at,
                    payload_json=_json_dumps(payload),
                )
            )
            conn.execute(
                schema.idempotency_keys.insert().values(
                    tenant_id=principal.tenant_id,
                    scope="POST:/v1/cases",
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    response_json=_json_dumps(created.to_dict()),
                    case_id=case_id,
                )
            )
            if start_job is not None:
                self._insert_workflow_outbox(conn, tenant_id=principal.tenant_id, request=start_job)
            return created, case, False

    def get_case(self, *, tenant_id: str, case_id: str) -> Case | None:
        with self._engine.connect() as conn:
            return self._load_case(conn, tenant_id, case_id)

    def get_case_meta(self, *, tenant_id: str, case_id: str) -> dict | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    select(schema.cases).where(
                        schema.cases.c.tenant_id == tenant_id,
                        schema.cases.c.case_id == case_id,
                    )
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def add_message(
        self,
        *,
        principal: Principal,
        case_id: str,
        message: str,
        language: str,
        expected_revision: int,
        message_id: str,
        event_id: str,
        author: str,
        occurred_at: str,
    ) -> Case:
        with self._engine.begin() as conn:
            row = self._lock_case(conn, principal.tenant_id, case_id)
            if row["revision"] != expected_revision:
                raise DomainError("REVISION_CONFLICT", "expected_revision does not match", 409)
            new_revision = expected_revision + 1
            seq = self._next_message_sequence(conn, principal.tenant_id, case_id)
            event_seq = self._next_event_sequence(conn, principal.tenant_id, case_id)
            conn.execute(
                schema.messages.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    message_id=message_id,
                    text=message,
                    language=language,
                    author=author,
                    occurred_at=occurred_at,
                    revision_introduced=new_revision,
                    sequence=seq,
                )
            )
            conn.execute(
                schema.cases.update()
                .where(
                    schema.cases.c.tenant_id == principal.tenant_id,
                    schema.cases.c.case_id == case_id,
                )
                .values(revision=new_revision, language=language)
            )
            messages = self._messages_through(conn, principal.tenant_id, case_id, new_revision)
            snapshot = CaseInput(
                case_id=case_id,
                case_revision=new_revision,
                original_text=row["original_text"],
                language=language,
                order_reference=row["order_reference"],
                messages=tuple(messages),
            )
            conn.execute(
                schema.input_snapshots.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    case_revision=new_revision,
                    snapshot_json=_json_dumps(snapshot.to_dict()),
                )
            )
            payload = {
                "status": row["status"],
                "evidence_ids": _json_loads(row["evidence_ids_json"]),
                "reason_code": "MESSAGE_ADDED",
            }
            if row["action_id"]:
                payload["action_id"] = row["action_id"]
            conn.execute(
                schema.events.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    sequence=event_seq,
                    event_id=event_id,
                    case_revision=new_revision,
                    type="MESSAGE_ADDED",
                    occurred_at=occurred_at,
                    payload_json=_json_dumps(payload),
                )
            )
            case = self._load_case(conn, principal.tenant_id, case_id)
            assert case is not None
            return case

    def list_events(self, *, tenant_id: str, case_id: str, after_sequence: int) -> list[CaseEvent]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    select(schema.events)
                    .where(
                        schema.events.c.tenant_id == tenant_id,
                        schema.events.c.case_id == case_id,
                        schema.events.c.sequence > after_sequence,
                    )
                    .order_by(schema.events.c.sequence.asc())
                )
                .mappings()
                .all()
            )
            return [
                CaseEvent(
                    event_id=row["event_id"],
                    sequence=int(row["sequence"]),
                    case_id=case_id,
                    case_revision=int(row["case_revision"]),
                    type=row["type"],
                    occurred_at=row["occurred_at"],
                    payload=_json_loads(row["payload_json"]),
                )
                for row in rows
            ]

    def list_queue(
        self, *, tenant_id: str, status: str | None, after: str | None, limit: int
    ) -> tuple[list[Case], str | None]:
        statuses = _resolve_status_filter(status)
        with self._engine.connect() as conn:
            stmt = select(schema.cases).where(schema.cases.c.tenant_id == tenant_id)
            if statuses:
                stmt = stmt.where(schema.cases.c.status.in_(statuses))
            stmt = stmt.order_by(schema.cases.c.case_id.asc())
            rows = conn.execute(stmt).mappings().all()
            started = after is None
            cases: list[Case] = []
            next_cursor = None
            for row in rows:
                if not started:
                    if row["case_id"] == after:
                        started = True
                    continue
                cases.append(self._row_to_case(row))
                if len(cases) >= limit:
                    next_cursor = row["case_id"]
                    break
            return cases, next_cursor

    def list_ops_messages(
        self, *, tenant_id: str, after: str | None, limit: int
    ) -> tuple[list[dict[str, Any]], str | None]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    select(schema.messages)
                    .where(schema.messages.c.tenant_id == tenant_id)
                    .order_by(
                        schema.messages.c.occurred_at.desc(),
                        schema.messages.c.case_id.desc(),
                        schema.messages.c.message_id.desc(),
                    )
                )
                .mappings()
                .all()
            )
            started = after is None
            messages: list[dict[str, Any]] = []
            next_cursor = None
            for row in rows:
                cursor = f"{row['case_id']}:{row['message_id']}"
                if not started:
                    if cursor == after:
                        started = True
                    continue
                messages.append(
                    {
                        "case_id": row["case_id"],
                        "message_id": row["message_id"],
                        "text": row["text"],
                        "language": row["language"],
                        "author": row["author"],
                        "occurred_at": row["occurred_at"],
                    }
                )
                if len(messages) >= limit:
                    next_cursor = cursor
                    break
            return messages, next_cursor

    def list_ops_audit_events(
        self, *, tenant_id: str, after: str | None, limit: int
    ) -> tuple[list[dict[str, Any]], str | None]:
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    select(schema.events)
                    .where(schema.events.c.tenant_id == tenant_id)
                    .order_by(
                        schema.events.c.occurred_at.desc(),
                        schema.events.c.case_id.desc(),
                        schema.events.c.sequence.desc(),
                    )
                )
                .mappings()
                .all()
            )
            started = after is None
            events: list[dict[str, Any]] = []
            next_cursor = None
            for row in rows:
                cursor = f"{row['case_id']}:{row['sequence']}"
                if not started:
                    if cursor == after:
                        started = True
                    continue
                events.append(
                    {
                        "case_id": row["case_id"],
                        "sequence": int(row["sequence"]),
                        "type": row["type"],
                        "occurred_at": row["occurred_at"],
                        "payload": _json_loads(row["payload_json"]),
                    }
                )
                if len(events) >= limit:
                    next_cursor = cursor
                    break
            return events, next_cursor

    def escalate(
        self,
        *,
        principal: Principal,
        case_id: str,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
        event_id: str,
        occurred_at: str,
    ) -> Case:
        with self._engine.begin() as conn:
            row = self._lock_case(conn, principal.tenant_id, case_id)
            if row["revision"] != expected_revision:
                raise DomainError("REVISION_CONFLICT", "expected_revision does not match", 409)
            new_revision = expected_revision + 1
            event_seq = self._next_event_sequence(conn, principal.tenant_id, case_id)
            conn.execute(
                schema.cases.update()
                .where(
                    schema.cases.c.tenant_id == principal.tenant_id,
                    schema.cases.c.case_id == case_id,
                )
                .values(
                    revision=new_revision,
                    status="ESCALATED",
                    owner_queue=owner_queue,
                )
            )
            # Immutable snapshot: copy prior messages through new revision.
            messages = self._messages_through(conn, principal.tenant_id, case_id, new_revision)
            snapshot = CaseInput(
                case_id=case_id,
                case_revision=new_revision,
                original_text=row["original_text"],
                language=row["language"],
                order_reference=row["order_reference"],
                messages=tuple(messages),
            )
            conn.execute(
                schema.input_snapshots.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    case_revision=new_revision,
                    snapshot_json=_json_dumps(snapshot.to_dict()),
                )
            )
            payload = {
                "status": "ESCALATED",
                "evidence_ids": _json_loads(row["evidence_ids_json"]),
                "reason_code": reason_code,
            }
            if row["action_id"]:
                payload["action_id"] = row["action_id"]
            conn.execute(
                schema.events.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    sequence=event_seq,
                    event_id=event_id,
                    case_revision=new_revision,
                    type="ESCALATED",
                    occurred_at=occurred_at,
                    payload_json=_json_dumps(payload),
                )
            )
            case = self._load_case(conn, principal.tenant_id, case_id)
            assert case is not None
            return case

    def claim_case(
        self,
        *,
        principal: Principal,
        case_id: str,
        event_id: str,
        occurred_at: str,
    ) -> Case:
        with self._engine.begin() as conn:
            row = self._lock_case(conn, principal.tenant_id, case_id)
            current_owner = row["assigned_principal_id"]
            if current_owner and current_owner != principal.principal_id:
                raise DomainError(
                    "ASSIGNMENT_CONFLICT",
                    "Case already claimed by another operator",
                    409,
                )
            if current_owner == principal.principal_id:
                case = self._load_case(conn, principal.tenant_id, case_id)
                assert case is not None
                return case
            new_revision = int(row["revision"]) + 1
            event_seq = self._next_event_sequence(conn, principal.tenant_id, case_id)
            conn.execute(
                schema.cases.update()
                .where(
                    schema.cases.c.tenant_id == principal.tenant_id,
                    schema.cases.c.case_id == case_id,
                )
                .values(
                    revision=new_revision,
                    assigned_principal_id=principal.principal_id,
                )
            )
            messages = self._messages_through(conn, principal.tenant_id, case_id, new_revision)
            snapshot = CaseInput(
                case_id=case_id,
                case_revision=new_revision,
                original_text=row["original_text"],
                language=row["language"],
                order_reference=row["order_reference"],
                messages=tuple(messages),
            )
            conn.execute(
                schema.input_snapshots.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    case_revision=new_revision,
                    snapshot_json=_json_dumps(snapshot.to_dict()),
                )
            )
            payload = {
                "status": row["status"],
                "evidence_ids": _json_loads(row["evidence_ids_json"]),
                "reason_code": "CASE_CLAIMED",
                "assigned_principal_id": principal.principal_id,
            }
            if row["action_id"]:
                payload["action_id"] = row["action_id"]
            conn.execute(
                schema.events.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    sequence=event_seq,
                    event_id=event_id,
                    case_revision=new_revision,
                    type="CASE_CLAIMED",
                    occurred_at=occurred_at,
                    payload_json=_json_dumps(payload),
                )
            )
            case = self._load_case(conn, principal.tenant_id, case_id)
            assert case is not None
            return case

    def list_case_rows(
        self,
        *,
        tenant_id: str,
        subject_refs: tuple[str, ...] | None = None,
    ) -> list[dict]:
        with self._engine.connect() as conn:
            stmt = select(schema.cases).where(schema.cases.c.tenant_id == tenant_id)
            if subject_refs is not None:
                if not subject_refs:
                    return []
                stmt = stmt.where(schema.cases.c.subject_ref.in_(subject_refs))
            stmt = stmt.order_by(schema.cases.c.case_id.asc())
            return [dict(row) for row in conn.execute(stmt).mappings().all()]

    def get_input(self, *, tenant_id: str, case_id: str, revision: int) -> CaseInput | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    select(schema.input_snapshots).where(
                        schema.input_snapshots.c.tenant_id == tenant_id,
                        schema.input_snapshots.c.case_id == case_id,
                        schema.input_snapshots.c.case_revision == revision,
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            data = _json_loads(row["snapshot_json"])
            messages = tuple(
                CaseMessage(
                    message_id=m["message_id"],
                    text=m["text"],
                    language=m["language"],
                    author=m["author"],
                    occurred_at=m["occurred_at"],
                )
                for m in data["messages"]
            )
            return CaseInput(
                case_id=data["case_id"],
                case_revision=data["case_revision"],
                original_text=data["original_text"],
                language=data["language"],
                order_reference=data["order_reference"],
                messages=messages,
            )

    def apply_result(
        self,
        *,
        principal: Principal,
        case_id: str,
        result: CaseResult,
        event_id: str,
        occurred_at: str,
        assessment_ref: str | None,
    ) -> Case:
        payload = result.to_dict()
        payload_hash = _hash(payload)
        with self._engine.begin() as conn:
            existing = (
                conn.execute(
                    select(schema.result_keys).where(
                        schema.result_keys.c.tenant_id == principal.tenant_id,
                        schema.result_keys.c.case_id == case_id,
                        schema.result_keys.c.event_key == result.event_key,
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                if existing["payload_hash"] != payload_hash:
                    raise DomainError(
                        "IDEMPOTENCY_CONFLICT",
                        "Key already used with a different payload",
                        409,
                    )
                snap = _json_loads(existing["case_snapshot_json"])
                return Case(
                    case_id=snap["case_id"],
                    revision=snap["revision"],
                    status=snap["status"],
                    language=snap["language"],
                    intent=snap["intent"],
                    evidence_ids=tuple(snap["evidence_ids"]),
                    action_id=snap.get("action_id"),
                    assigned_principal_id=snap.get("assigned_principal_id"),
                    contract_version=snap.get("contract_version", CONTRACT_VERSION),
                )

            row = self._lock_case(conn, principal.tenant_id, case_id)
            if row["revision"] != result.expected_revision:
                raise DomainError("REVISION_CONFLICT", "expected_revision does not match", 409)
            new_revision = result.expected_revision + 1
            event_seq = self._next_event_sequence(conn, principal.tenant_id, case_id)
            evidence_json = _json_dumps(list(result.evidence_ids))
            conn.execute(
                schema.cases.update()
                .where(
                    schema.cases.c.tenant_id == principal.tenant_id,
                    schema.cases.c.case_id == case_id,
                )
                .values(
                    revision=new_revision,
                    status=result.status,
                    evidence_ids_json=evidence_json,
                    action_id=result.action_id,
                    assessment_id=assessment_ref,
                    # Preserve operator claim across workflow result transitions.
                    assigned_principal_id=row["assigned_principal_id"],
                )
            )
            if result.action_id:
                conn.execute(
                    schema.action_case_index.delete().where(
                        schema.action_case_index.c.tenant_id == principal.tenant_id,
                        schema.action_case_index.c.action_id == result.action_id,
                    )
                )
                conn.execute(
                    schema.action_case_index.insert().values(
                        tenant_id=principal.tenant_id,
                        action_id=result.action_id,
                        case_id=case_id,
                    )
                )
            messages = self._messages_through(conn, principal.tenant_id, case_id, new_revision)
            snapshot = CaseInput(
                case_id=case_id,
                case_revision=new_revision,
                original_text=row["original_text"],
                language=row["language"],
                order_reference=row["order_reference"],
                messages=tuple(messages),
            )
            conn.execute(
                schema.input_snapshots.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    case_revision=new_revision,
                    snapshot_json=_json_dumps(snapshot.to_dict()),
                )
            )
            event_payload: dict[str, Any] = {
                "status": result.status,
                "evidence_ids": list(result.evidence_ids),
                "reason_code": result.reason_code,
            }
            if result.action_id is not None:
                event_payload["action_id"] = result.action_id
            conn.execute(
                schema.events.insert().values(
                    tenant_id=principal.tenant_id,
                    case_id=case_id,
                    sequence=event_seq,
                    event_id=event_id,
                    case_revision=new_revision,
                    type="CASE_RESULT",
                    occurred_at=occurred_at,
                    payload_json=_json_dumps(event_payload),
                )
            )
            case = self._load_case(conn, principal.tenant_id, case_id)
            assert case is not None
            try:
                conn.execute(
                    schema.result_keys.insert().values(
                        tenant_id=principal.tenant_id,
                        case_id=case_id,
                        event_key=result.event_key,
                        payload_hash=payload_hash,
                        case_snapshot_json=_json_dumps(case.to_dict()),
                    )
                )
            except IntegrityError as exc:
                raise DomainError(
                    "IDEMPOTENCY_CONFLICT",
                    "Key already used with a different payload",
                    409,
                ) from exc
            return case

    def find_case_for_action(self, *, tenant_id: str, action_id: str) -> str | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(schema.action_case_index.c.case_id).where(
                    schema.action_case_index.c.tenant_id == tenant_id,
                    schema.action_case_index.c.action_id == action_id,
                )
            ).first()
            return row[0] if row else None

    def enqueue_workflow(self, *, tenant_id: str, request: WorkflowRequest) -> None:
        with self._engine.begin() as conn:
            self._insert_workflow_outbox(conn, tenant_id=tenant_id, request=request)

    def claim_workflow_jobs(
        self,
        *,
        limit: int = 20,
        now: datetime | None = None,
        lease_seconds: int = WORKFLOW_JOB_LEASE_SECONDS,
    ) -> list[tuple[str, WorkflowRequest]]:
        """Claim PENDING jobs, or CLAIMED jobs whose lease expired (crash reclaim)."""
        claim_now = now or datetime.now(UTC)
        lease_expires = claim_now + timedelta(seconds=lease_seconds)
        with self._engine.begin() as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        WITH picked AS (
                          SELECT id FROM workflow_outbox
                          WHERE status = 'PENDING'
                             OR (
                               status = 'CLAIMED'
                               AND (
                                 lease_expires_at IS NULL
                                 OR lease_expires_at < :now
                               )
                             )
                          ORDER BY created_at ASC
                          FOR UPDATE SKIP LOCKED
                          LIMIT :limit
                        )
                        UPDATE workflow_outbox AS o
                        SET status = 'CLAIMED',
                            lease_expires_at = :lease_expires,
                            detail = ''
                        FROM picked
                        WHERE o.id = picked.id
                        RETURNING o.id, o.payload_json
                        """
                    ),
                    {"limit": limit, "now": claim_now, "lease_expires": lease_expires},
                )
                .mappings()
                .all()
            )
            return [
                (row["id"], _workflow_request_from_payload(_json_loads(row["payload_json"])))
                for row in rows
            ]

    def mark_workflow_job(self, *, job_row_id: str, status: str, detail: str = "") -> None:
        with self._engine.begin() as conn:
            conn.execute(
                schema.workflow_outbox.update()
                .where(schema.workflow_outbox.c.id == job_row_id)
                .values(status=status, detail=detail, lease_expires_at=None)
            )

    def _insert_workflow_outbox(self, conn, *, tenant_id: str, request: WorkflowRequest) -> None:
        payload = request.to_dict()
        row_id = _outbox_row_id(tenant_id, request.job_key)
        existing = (
            conn.execute(
                select(schema.workflow_outbox).where(
                    schema.workflow_outbox.c.tenant_id == tenant_id,
                    schema.workflow_outbox.c.job_key == request.job_key,
                )
            )
            .mappings()
            .first()
        )
        if existing is not None:
            if not idempotency_payload_equal(_json_loads(existing["payload_json"]), payload):
                raise DomainError(
                    "IDEMPOTENCY_CONFLICT",
                    "Key already used with a different payload",
                    409,
                )
            return
        conn.execute(
            schema.workflow_outbox.insert().values(
                id=row_id,
                tenant_id=tenant_id,
                job_key=request.job_key,
                payload_json=_json_dumps(payload),
                status="PENDING",
            )
        )

    def _lock_case(self, conn, tenant_id: str, case_id: str):
        row = (
            conn.execute(
                select(schema.cases)
                .where(
                    schema.cases.c.tenant_id == tenant_id,
                    schema.cases.c.case_id == case_id,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if row is None:
            raise DomainError("NOT_FOUND", "Case not found", 404)
        return row

    def _load_case(self, conn, tenant_id: str, case_id: str) -> Case | None:
        row = (
            conn.execute(
                select(schema.cases).where(
                    schema.cases.c.tenant_id == tenant_id,
                    schema.cases.c.case_id == case_id,
                )
            )
            .mappings()
            .first()
        )
        return self._row_to_case(row) if row else None

    def _row_to_case(self, row) -> Case:
        return Case(
            case_id=row["case_id"],
            revision=int(row["revision"]),
            status=row["status"],
            language=row["language"],
            intent=row["intent"],
            evidence_ids=tuple(_json_loads(row["evidence_ids_json"])),
            action_id=row["action_id"],
            assigned_principal_id=row.get("assigned_principal_id"),
        )

    def _next_event_sequence(self, conn, tenant_id: str, case_id: str) -> int:
        row = conn.execute(
            select(schema.events.c.sequence)
            .where(
                schema.events.c.tenant_id == tenant_id,
                schema.events.c.case_id == case_id,
            )
            .order_by(schema.events.c.sequence.desc())
            .limit(1)
        ).first()
        return int(row[0]) + 1 if row else 1

    def _next_message_sequence(self, conn, tenant_id: str, case_id: str) -> int:
        row = conn.execute(
            select(schema.messages.c.sequence)
            .where(
                schema.messages.c.tenant_id == tenant_id,
                schema.messages.c.case_id == case_id,
            )
            .order_by(schema.messages.c.sequence.desc())
            .limit(1)
        ).first()
        return int(row[0]) + 1 if row else 1

    def _messages_through(self, conn, tenant_id: str, case_id: str, revision: int):
        rows = (
            conn.execute(
                select(schema.messages)
                .where(
                    schema.messages.c.tenant_id == tenant_id,
                    schema.messages.c.case_id == case_id,
                    schema.messages.c.revision_introduced <= revision,
                )
                .order_by(schema.messages.c.sequence.asc())
            )
            .mappings()
            .all()
        )
        return [
            CaseMessage(
                message_id=row["message_id"],
                text=row["text"],
                language=row["language"],
                author=row["author"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        ]
