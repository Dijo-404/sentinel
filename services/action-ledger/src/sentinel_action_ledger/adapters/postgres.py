"""PostgreSQL store: FOR UPDATE locks, SKIP LOCKED claims, atomic outbox/audit."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection

from sentinel_action_ledger.application.ports import StoredAction
from sentinel_action_ledger.domain.errors import ConflictError
from sentinel_action_ledger.domain.money import PaymentBalance
from sentinel_action_ledger.domain.types import ActionRecord, Approval, Command, EligibilitySnapshot


def _row_action(row) -> StoredAction:
    return StoredAction(
        tenant_id=row.tenant_id,
        action_id=row.action_id,
        operation_key=row.operation_key,
        provider_ref=row.provider_ref,
        payload=row.payload if isinstance(row.payload, dict) else json.loads(row.payload),
        action_digest=row.action_digest,
        status=row.status,
        amount_minor=row.amount_minor,
        currency=row.currency,
        transaction_ref=row.transaction_ref,
        case_id=row.case_id,
        case_revision=row.case_revision,
        policy_version=row.policy_version,
        approval_id=row.approval_id,
        lease_id=row.lease_id,
        lease_expires_at=row.lease_expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@dataclass
class PostgresUnitOfWork:
    connection: Connection

    def get_action_by_id(self, tenant_id: str, action_id: str) -> StoredAction | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT * FROM actions WHERE tenant_id = :tenant AND action_id = :aid "
                    "FOR UPDATE"
                ),
                {"tenant": tenant_id, "aid": action_id},
            )
            .mappings()
            .first()
        )
        return _row_action(row) if row else None

    def get_action_by_operation_key(
        self, tenant_id: str, operation_key: str
    ) -> StoredAction | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT * FROM actions WHERE tenant_id = :tenant AND operation_key = :ok "
                    "FOR UPDATE"
                ),
                {"tenant": tenant_id, "ok": operation_key},
            )
            .mappings()
            .first()
        )
        return _row_action(row) if row else None

    def insert_action(self, action: StoredAction) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO actions (
                  tenant_id, action_id, operation_key, provider_ref, payload, action_digest,
                  status, amount_minor, currency, transaction_ref, case_id, case_revision,
                  policy_version, approval_id, lease_id, lease_expires_at, created_at, updated_at
                ) VALUES (
                  :tenant_id, :action_id, :operation_key, :provider_ref, CAST(:payload AS jsonb),
                  :action_digest, :status, :amount_minor, :currency, :transaction_ref, :case_id,
                  :case_revision, :policy_version, :approval_id, :lease_id, :lease_expires_at,
                  :created_at, :updated_at
                )
                """
            ),
            {
                **action.__dict__,
                "payload": json.dumps(action.payload, separators=(",", ":"), ensure_ascii=False),
            },
        )

    def update_action(self, action: StoredAction) -> None:
        self.connection.execute(
            text(
                """
                UPDATE actions SET
                  status = :status,
                  approval_id = :approval_id,
                  lease_id = :lease_id,
                  lease_expires_at = :lease_expires_at,
                  updated_at = :updated_at,
                  payload = CAST(:payload AS jsonb),
                  action_digest = :action_digest
                WHERE tenant_id = :tenant_id AND action_id = :action_id
                """
            ),
            {
                "tenant_id": action.tenant_id,
                "action_id": action.action_id,
                "status": action.status,
                "approval_id": action.approval_id,
                "lease_id": action.lease_id,
                "lease_expires_at": action.lease_expires_at,
                "updated_at": action.updated_at,
                "payload": json.dumps(action.payload, separators=(",", ":"), ensure_ascii=False),
                "action_digest": action.action_digest,
            },
        )

    def insert_approval(
        self, *, tenant_id: str, action_id: str, approval: Approval, created_at: str
    ) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO approvals (
                  tenant_id, approval_id, action_id, action_digest, case_revision,
                  policy_version, decision, reviewer_id, expires_at, created_at
                ) VALUES (
                  :tenant_id, :approval_id, :action_id, :action_digest, :case_revision,
                  :policy_version, :decision, :reviewer_id, :expires_at, :created_at
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "approval_id": approval.approval_id,
                "action_id": action_id,
                "action_digest": approval.action_digest,
                "case_revision": approval.case_revision,
                "policy_version": approval.policy_version,
                "decision": approval.decision,
                "reviewer_id": approval.reviewer_id,
                "expires_at": approval.expires_at,
                "created_at": created_at,
            },
        )

    def get_approval(self, tenant_id: str, approval_id: str) -> Approval | None:
        row = (
            self.connection.execute(
                text("SELECT * FROM approvals WHERE tenant_id = :tenant AND approval_id = :aid"),
                {"tenant": tenant_id, "aid": approval_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return Approval(
            approval_id=row.approval_id,
            action_digest=row.action_digest,
            case_revision=row.case_revision,
            policy_version=row.policy_version,
            decision=row.decision,
            reviewer_id=row.reviewer_id,
            expires_at=row.expires_at,
        )

    def get_approval_for_action(self, tenant_id: str, action_id: str) -> Approval | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT * FROM approvals WHERE tenant_id = :tenant AND action_id = :aid "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"tenant": tenant_id, "aid": action_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return Approval(
            approval_id=row.approval_id,
            action_digest=row.action_digest,
            case_revision=row.case_revision,
            policy_version=row.policy_version,
            decision=row.decision,
            reviewer_id=row.reviewer_id,
            expires_at=row.expires_at,
        )

    def lock_payment(self, tenant_id: str, transaction_ref: str) -> PaymentBalance | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT * FROM payment_reservations WHERE tenant_id = :tenant "
                    "AND transaction_ref = :txn FOR UPDATE"
                ),
                {"tenant": tenant_id, "txn": transaction_ref},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return PaymentBalance(
            captured_minor=row.captured_minor,
            reserved_minor=row.reserved_minor,
            pending_minor=row.pending_minor,
            refunded_minor=row.refunded_minor,
        )

    def upsert_payment(
        self,
        *,
        tenant_id: str,
        transaction_ref: str,
        merchant_ref: str,
        captured_minor: int,
        currency: str,
    ) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO payment_reservations (
                  tenant_id, transaction_ref, merchant_ref, captured_minor, reserved_minor,
                  pending_minor, refunded_minor, currency
                ) VALUES (
                  :tenant_id, :transaction_ref, :merchant_ref, :captured_minor, 0, 0, 0, :currency
                )
                ON CONFLICT (tenant_id, transaction_ref) DO UPDATE SET
                  merchant_ref = EXCLUDED.merchant_ref,
                  captured_minor = EXCLUDED.captured_minor,
                  currency = EXCLUDED.currency
                """
            ),
            {
                "tenant_id": tenant_id,
                "transaction_ref": transaction_ref,
                "merchant_ref": merchant_ref,
                "captured_minor": captured_minor,
                "currency": currency,
            },
        )

    def write_payment_balance(
        self, tenant_id: str, transaction_ref: str, balance: PaymentBalance
    ) -> None:
        result = self.connection.execute(
            text(
                """
                UPDATE payment_reservations SET
                  reserved_minor = :reserved_minor,
                  pending_minor = :pending_minor,
                  refunded_minor = :refunded_minor
                WHERE tenant_id = :tenant_id AND transaction_ref = :transaction_ref
                  AND reserved_minor + pending_minor + refunded_minor
                      <= captured_minor
                  AND :reserved_minor + :pending_minor + :refunded_minor
                      <= captured_minor
                """
            ),
            {
                "tenant_id": tenant_id,
                "transaction_ref": transaction_ref,
                "reserved_minor": balance.reserved_minor,
                "pending_minor": balance.pending_minor,
                "refunded_minor": balance.refunded_minor,
            },
        )
        if result.rowcount != 1:
            raise ConflictError(
                "Payment balance update rejected by invariant check",
                code="PAYMENT_BALANCE_CONFLICT",
            )

    def get_eligibility(self, tenant_id: str, transaction_ref: str) -> EligibilitySnapshot | None:
        row = (
            self.connection.execute(
                text(
                    "SELECT * FROM eligibility_snapshots WHERE tenant_id = :tenant "
                    "AND transaction_ref = :txn FOR UPDATE"
                ),
                {"tenant": tenant_id, "txn": transaction_ref},
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return EligibilitySnapshot(
            tenant_id=row.tenant_id,
            transaction_ref=row.transaction_ref,
            case_id=row.case_id,
            subject_ref=row.subject_ref,
            captured_minor=row.captured_minor,
            currency=row.currency,
            payment_status=row.payment_status,
            observed_at=row.observed_at,
            expires_at=row.expires_at,
            evidence_digest=row.evidence_digest,
            external_refunded_minor=row.external_refunded_minor,
            external_pending_minor=row.external_pending_minor,
            version=row.version,
        )

    def upsert_eligibility(self, snapshot: EligibilitySnapshot) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO eligibility_snapshots (
                  tenant_id, transaction_ref, case_id, subject_ref, captured_minor, currency,
                  payment_status, observed_at, expires_at, evidence_digest,
                  external_refunded_minor, external_pending_minor, version
                ) VALUES (
                  :tenant_id, :transaction_ref, :case_id, :subject_ref, :captured_minor, :currency,
                  :payment_status, :observed_at, :expires_at, :evidence_digest,
                  :external_refunded_minor, :external_pending_minor, :version
                )
                ON CONFLICT (tenant_id, transaction_ref) DO UPDATE SET
                  case_id = EXCLUDED.case_id,
                  subject_ref = EXCLUDED.subject_ref,
                  captured_minor = EXCLUDED.captured_minor,
                  currency = EXCLUDED.currency,
                  payment_status = EXCLUDED.payment_status,
                  observed_at = EXCLUDED.observed_at,
                  expires_at = EXCLUDED.expires_at,
                  evidence_digest = EXCLUDED.evidence_digest,
                  external_refunded_minor = EXCLUDED.external_refunded_minor,
                  external_pending_minor = EXCLUDED.external_pending_minor,
                  version = eligibility_snapshots.version + 1
                """
            ),
            asdict(snapshot),
        )

    def insert_outbox(
        self,
        *,
        tenant_id: str,
        action_id: str,
        available_at: str,
        payload: dict[str, Any],
    ) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO outbox (
                  tenant_id, action_id, status, available_at, payload, attempts
                ) VALUES (
                  :tenant_id, :action_id, 'PENDING', :available_at, CAST(:payload AS jsonb), 0
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "action_id": action_id,
                "available_at": available_at,
                "payload": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            },
        )

    def claim_outbox(
        self,
        *,
        tenant_id: str,
        limit: int,
        lease_expires_at: str,
        now: str,
        new_lease_id: Callable[[], str],
    ) -> list[Command]:
        # Peek only — do not FOR UPDATE outbox yet. outcome() locks actions then
        # outbox; holding outbox while waiting on actions deadlocks.
        candidates = (
            self.connection.execute(
                text(
                    """
                    SELECT id, action_id FROM outbox
                    WHERE tenant_id = :tenant
                      AND (
                        (status = 'PENDING' AND available_at <= :now)
                        OR (status = 'CLAIMED' AND lease_expires_at <= :now)
                      )
                    ORDER BY available_at, id
                    LIMIT :limit
                    """
                ),
                {"tenant": tenant_id, "limit": limit, "now": now},
            )
            .mappings()
            .all()
        )
        commands: list[Command] = []
        for row in candidates:
            # Lock action before claiming outbox (same order as outcome()).
            self.connection.execute(
                text(
                    "SELECT action_id FROM actions WHERE tenant_id = :tenant "
                    "AND action_id = :aid FOR UPDATE"
                ),
                {"tenant": tenant_id, "aid": row.action_id},
            )
            lease_id = new_lease_id()
            updated = (
                self.connection.execute(
                    text(
                        """
                        UPDATE outbox
                        SET status = 'CLAIMED',
                            lease_id = :lease_id,
                            lease_expires_at = :lease_expires_at,
                            attempts = attempts + 1
                        WHERE id = :id
                          AND (
                            (status = 'PENDING' AND available_at <= :now)
                            OR (status = 'CLAIMED' AND lease_expires_at <= :now)
                          )
                        RETURNING action_id, payload, lease_id, lease_expires_at
                        """
                    ),
                    {
                        "id": row.id,
                        "lease_id": lease_id,
                        "lease_expires_at": lease_expires_at,
                        "now": now,
                    },
                )
                .mappings()
                .first()
            )
            if updated is None:
                continue
            payload = (
                updated.payload
                if isinstance(updated.payload, dict)
                else json.loads(updated.payload)
            )
            commands.append(
                Command(
                    action_id=updated.action_id,
                    provider_ref=payload["provider_ref"],
                    payload=payload["payload"],
                    action_digest=payload["action_digest"],
                    lease_id=updated.lease_id,
                    lease_expires_at=updated.lease_expires_at,
                    provider_capabilities=payload["provider_capabilities"],
                )
            )
        return commands

    def mark_outbox_done(self, *, tenant_id: str, action_id: str) -> None:
        self.connection.execute(
            text(
                """
                UPDATE outbox
                SET status = 'DONE', lease_id = NULL, lease_expires_at = NULL
                WHERE tenant_id = :tenant AND action_id = :aid
                  AND status <> 'DONE'
                """
            ),
            {"tenant": tenant_id, "aid": action_id},
        )

    def insert_audit(
        self,
        *,
        tenant_id: str,
        action_id: str,
        event_type: str,
        actor_id: str,
        detail: dict[str, Any],
        occurred_at: str,
    ) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO financial_audit (
                  tenant_id, action_id, event_type, actor_id, detail, occurred_at
                ) VALUES (
                  :tenant_id, :action_id, :event_type, :actor_id, CAST(:detail AS jsonb),
                  :occurred_at
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "action_id": action_id,
                "event_type": event_type,
                "actor_id": actor_id,
                "detail": json.dumps(detail, separators=(",", ":"), ensure_ascii=False),
                "occurred_at": occurred_at,
            },
        )

    def record_outcome_event(
        self,
        *,
        tenant_id: str,
        action_id: str,
        event_key: str,
        status: str,
        reason_code: str,
        evidence_ids: Sequence[str],
        occurred_at: str,
    ) -> bool:
        existing = (
            self.connection.execute(
                text(
                    "SELECT status, reason_code, evidence_ids FROM outcome_events "
                    "WHERE tenant_id = :tenant AND action_id = :aid AND event_key = :ek"
                ),
                {"tenant": tenant_id, "aid": action_id, "ek": event_key},
            )
            .mappings()
            .first()
        )
        if existing is not None:
            stored_ids = (
                existing.evidence_ids
                if isinstance(existing.evidence_ids, list)
                else json.loads(existing.evidence_ids)
            )
            if (
                existing.status == status
                and existing.reason_code == reason_code
                and stored_ids == list(evidence_ids)
            ):
                return False
            from sentinel_action_ledger.domain.errors import ConflictError

            raise ConflictError(
                "event_key already used with a different payload",
                code="IDEMPOTENCY_CONFLICT",
            )
        self.connection.execute(
            text(
                """
                INSERT INTO outcome_events (
                  tenant_id, action_id, event_key, status, reason_code, evidence_ids, occurred_at
                ) VALUES (
                  :tenant_id, :action_id, :event_key, :status, :reason_code,
                  CAST(:evidence_ids AS jsonb), :occurred_at
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "action_id": action_id,
                "event_key": event_key,
                "status": status,
                "reason_code": reason_code,
                "evidence_ids": json.dumps(list(evidence_ids)),
                "occurred_at": occurred_at,
            },
        )
        return True

    def to_record(self, action: StoredAction) -> ActionRecord:
        approval = None
        if action.approval_id:
            approval = self.get_approval(action.tenant_id, action.approval_id)
        elif action.status != "PROPOSED":
            approval = self.get_approval_for_action(action.tenant_id, action.action_id)
        return ActionRecord(
            action_id=action.action_id,
            provider_ref=action.provider_ref,
            payload=action.payload,
            action_digest=action.action_digest,
            status=action.status,  # type: ignore[arg-type]
            approval=approval,
        )


class PostgresLedgerStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def transaction(self) -> Iterator[PostgresUnitOfWork]:
        with self._engine.begin() as connection:
            yield PostgresUnitOfWork(connection)
