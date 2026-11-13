"""Import settlement batches and produce discrepancy findings."""

from __future__ import annotations

from sentinel_merchant_settlement.application.errors import (
    ConflictError,
    ForbiddenError,
    ValidationError,
)
from sentinel_merchant_settlement.application.ports import (
    EvidencePort,
    FindingStore,
    PaymentProviderPort,
)
from sentinel_merchant_settlement.domain.reconcile import canonical_batch_digest, reconcile
from sentinel_merchant_settlement.domain.types import (
    ImportResult,
    Principal,
    SettlementBatch,
    SettlementRow,
)


class ImportSettlementBatch:
    def __init__(
        self,
        *,
        evidence: EvidencePort,
        provider: PaymentProviderPort,
        store: FindingStore,
    ) -> None:
        self._evidence = evidence
        self._provider = provider
        self._store = store

    def __call__(self, principal: Principal, batch: SettlementBatch) -> ImportResult:
        self._authorize(principal, batch)
        existing = self._store.get_batch(batch.batch_id)
        if existing is not None:
            if existing.source_digest != batch.source_digest:
                raise ConflictError("Key already used with a different payload")
            findings = self._store.list_findings(batch_id=batch.batch_id)
            return ImportResult(batch=existing, findings=findings)

        order_refs = tuple(sorted({r.order_ref for r in batch.rows if r.order_ref}))
        txn_refs = tuple(sorted({r.transaction_ref for r in batch.rows}))
        provider_world = self._provider.load_world(
            principal=principal,
            tenant_id=batch.tenant_id,
            merchant_ref=batch.merchant_ref,
            period_start=batch.period_start,
            period_end=batch.period_end,
            order_refs=order_refs,
            transaction_refs=txn_refs,
        )
        evidence_world = self._evidence.load_world(
            principal=principal,
            tenant_id=batch.tenant_id,
            merchant_ref=batch.merchant_ref,
            order_refs=order_refs,
            transaction_refs=txn_refs,
        )
        world = _merge_worlds(provider_world, evidence_world)
        findings = reconcile(batch, world)
        self._store.save_import(batch, findings)
        return ImportResult(batch=batch, findings=findings)

    def _authorize(self, principal: Principal, batch: SettlementBatch) -> None:
        if not {"operator", "supervisor"} & set(principal.roles):
            raise ForbiddenError("operator or supervisor role required")
        if principal.tenant_id != batch.tenant_id:
            raise ForbiddenError("Tenant scope denied")
        if not principal.allows_merchant(batch.merchant_ref):
            raise ForbiddenError("Merchant scope denied")
        if batch.currency != "INR":
            raise ValidationError("currency must be INR")
        if not batch.rows:
            raise ValidationError("rows must be nonempty")
        for row in batch.rows:
            if row.settled_minor < 0 or row.fee_minor < 0:
                raise ValidationError("money fields must be non-negative integers")


def build_batch_from_dict(body: dict) -> SettlementBatch:
    required = {
        "batch_id",
        "tenant_id",
        "merchant_ref",
        "period_start",
        "period_end",
        "currency",
        "rows",
    }
    extra = set(body) - required - {"source_digest", "csv_text"}
    if extra:
        raise ValidationError("Undeclared fields are not permitted")
    missing = required - set(body)
    if missing:
        raise ValidationError(f"Missing fields: {', '.join(sorted(missing))}")
    if not isinstance(body["rows"], list):
        raise ValidationError("rows must be an array")
    rows: list[SettlementRow] = []
    for item in body["rows"]:
        rows.append(_parse_row(item))
    digest = body.get("source_digest") or canonical_batch_digest(rows)
    if not isinstance(digest, str) or not digest:
        raise ValidationError("source_digest must be a nonempty string")
    return SettlementBatch(
        batch_id=str(body["batch_id"]),
        tenant_id=str(body["tenant_id"]),
        merchant_ref=str(body["merchant_ref"]),
        period_start=str(body["period_start"]),
        period_end=str(body["period_end"]),
        currency=str(body["currency"]),
        rows=tuple(rows),
        source_digest=digest,
    )


def build_batch_from_csv(
    *,
    batch_id: str,
    tenant_id: str,
    merchant_ref: str,
    period_start: str,
    period_end: str,
    currency: str,
    csv_text: str,
) -> SettlementBatch:
    rows = parse_settlement_csv(csv_text)
    return SettlementBatch(
        batch_id=batch_id,
        tenant_id=tenant_id,
        merchant_ref=merchant_ref,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        rows=tuple(rows),
        source_digest=canonical_batch_digest(rows),
    )


def parse_settlement_csv(csv_text: str) -> list[SettlementRow]:
    lines = [line.strip() for line in csv_text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValidationError("CSV body is empty")
    header = [h.strip() for h in lines[0].split(",")]
    required = {"row_id", "transaction_ref", "settled_minor", "fee_minor", "occurred_at"}
    if not required.issubset(set(header)):
        raise ValidationError("CSV header missing required columns")
    rows: list[SettlementRow] = []
    for line in lines[1:]:
        cols = [c.strip() for c in line.split(",")]
        if len(cols) != len(header):
            raise ValidationError("CSV row column count mismatch")
        raw = dict(zip(header, cols, strict=True))
        order_ref = raw.get("order_ref") or None
        try:
            settled = int(raw["settled_minor"])
            fee = int(raw["fee_minor"])
        except ValueError as exc:
            raise ValidationError("CSV money fields must be integers") from exc
        rows.append(
            SettlementRow(
                row_id=raw["row_id"],
                transaction_ref=raw["transaction_ref"],
                order_ref=order_ref if order_ref else None,
                settled_minor=settled,
                fee_minor=fee,
                occurred_at=raw["occurred_at"],
            )
        )
    return rows


def _parse_row(item: object) -> SettlementRow:
    if not isinstance(item, dict):
        raise ValidationError("each row must be an object")
    allowed = {
        "row_id",
        "transaction_ref",
        "order_ref",
        "settled_minor",
        "fee_minor",
        "occurred_at",
    }
    if set(item) - allowed:
        raise ValidationError("Undeclared row fields are not permitted")
    for key in ("row_id", "transaction_ref", "settled_minor", "fee_minor", "occurred_at"):
        if key not in item:
            raise ValidationError(f"row.{key} is required")
    settled = item["settled_minor"]
    fee = item["fee_minor"]
    if type(settled) is not int or type(fee) is not int:
        raise ValidationError("settled_minor and fee_minor must be integers")
    order_ref = item.get("order_ref")
    if order_ref is not None and not isinstance(order_ref, str):
        raise ValidationError("order_ref must be a string when present")
    return SettlementRow(
        row_id=str(item["row_id"]),
        transaction_ref=str(item["transaction_ref"]),
        order_ref=order_ref,
        settled_minor=settled,
        fee_minor=fee,
        occurred_at=str(item["occurred_at"]),
    )


def _merge_worlds(provider_world, evidence_world):
    from sentinel_merchant_settlement.domain.types import PeerWorld

    return PeerWorld(
        payments=provider_world.payments,
        orders=provider_world.orders,
        evidence=evidence_world.evidence,
    )
