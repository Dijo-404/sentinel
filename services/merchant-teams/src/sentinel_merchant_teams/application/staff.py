"""Staff CRUD, role assignment, activity timeline, advisory checks."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import replace

from ..domain.advisory import check_advisory_limit, refuse_financial_authorization
from ..domain.roles import normalize_roles
from ..domain.types import (
    AdvisoryLimitResult,
    MerchantStaff,
    Principal,
    StaffActivity,
)
from .errors import (
    FinancialAuthorityDenied,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .ports import CaseApiPort, Clock, StaffStore

_MANAGE_ROLES = frozenset({"operator", "supervisor", "sandbox-admin"})
_CASE_ACTIVITY_KINDS = frozenset({"CASE_VIEW", "CASE_NOTE", "CASE_ASSIGN"})


def _require_manager(principal: Principal) -> None:
    if not _MANAGE_ROLES.intersection(principal.roles):
        raise UnauthorizedError("Operator or supervisor role required")


def _require_merchant(principal: Principal, merchant_ref: str) -> None:
    if not principal.allows_merchant(merchant_ref):
        raise UnauthorizedError("Unauthorized merchant scope")


def _new_staff_id() -> str:
    return f"staff-{secrets.token_hex(6)}"


def _new_event_id() -> str:
    return f"event-{uuid.uuid4().hex[:12]}"


def _rfc3339(clock: Clock) -> str:
    return clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")


class StaffService:
    def __init__(self, store: StaffStore, cases: CaseApiPort, clock: Clock):
        self._store = store
        self._cases = cases
        self._clock = clock

    def create(
        self,
        principal: Principal,
        *,
        merchant_ref: str,
        display_name: str,
        roles: list[str],
        approval_limit_minor: int | None = None,
        currency: str | None = None,
        staff_id: str | None = None,
    ) -> MerchantStaff:
        _require_manager(principal)
        _require_merchant(principal, merchant_ref)
        if not display_name or not display_name.strip():
            raise ValidationError("display_name is required")
        try:
            role_tuple = normalize_roles(roles)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        if approval_limit_minor is not None:
            if not isinstance(approval_limit_minor, int) or isinstance(approval_limit_minor, bool):
                raise ValidationError("approval_limit_minor must be an integer")
            if approval_limit_minor < 0:
                raise ValidationError("approval_limit_minor must be >= 0")
            if not currency:
                raise ValidationError("currency is required with approval_limit_minor")
        elif currency is not None:
            raise ValidationError("currency requires approval_limit_minor")

        sid = staff_id or _new_staff_id()
        if self._store.get(tenant_id=principal.tenant_id, staff_id=sid) is not None:
            raise ValidationError("staff_id already exists")

        staff = MerchantStaff(
            staff_id=sid,
            tenant_id=principal.tenant_id,
            merchant_ref=merchant_ref,
            display_name=display_name.strip(),
            roles=role_tuple,
            active=True,
            approval_limit_minor=approval_limit_minor,
            currency=currency,
        )
        created = self._store.create(staff)
        self._store.append_activity(
            StaffActivity(
                event_id=_new_event_id(),
                staff_id=created.staff_id,
                at=_rfc3339(self._clock),
                kind="STAFF_CREATED",
                subject_ref=created.merchant_ref,
                summary=f"Created staff {created.display_name}",
            )
        )
        return created

    def get(self, principal: Principal, staff_id: str) -> MerchantStaff:
        _require_manager(principal)
        staff = self._store.get(tenant_id=principal.tenant_id, staff_id=staff_id)
        if staff is None:
            raise NotFoundError("Staff not found")
        _require_merchant(principal, staff.merchant_ref)
        return staff

    def list_staff(self, principal: Principal, merchant_ref: str) -> tuple[MerchantStaff, ...]:
        _require_manager(principal)
        _require_merchant(principal, merchant_ref)
        return self._store.list_for_merchant(
            tenant_id=principal.tenant_id, merchant_ref=merchant_ref
        )

    def update(
        self,
        principal: Principal,
        staff_id: str,
        *,
        display_name: str | None = None,
        roles: list[str] | None = None,
        approval_limit_minor: int | None = None,
        currency: str | None = None,
        clear_approval_limit: bool = False,
    ) -> MerchantStaff:
        staff = self.get(principal, staff_id)
        if not staff.active:
            raise ValidationError("Inactive staff cannot be updated")

        new_name = staff.display_name
        if display_name is not None:
            if not display_name.strip():
                raise ValidationError("display_name is required")
            new_name = display_name.strip()

        new_roles = staff.roles
        if roles is not None:
            try:
                new_roles = normalize_roles(roles)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc

        new_limit = staff.approval_limit_minor
        new_currency = staff.currency
        if clear_approval_limit:
            new_limit = None
            new_currency = None
        elif approval_limit_minor is not None:
            if not isinstance(approval_limit_minor, int) or isinstance(approval_limit_minor, bool):
                raise ValidationError("approval_limit_minor must be an integer")
            if approval_limit_minor < 0:
                raise ValidationError("approval_limit_minor must be >= 0")
            new_limit = approval_limit_minor
            if currency is not None:
                new_currency = currency
            elif new_currency is None:
                raise ValidationError("currency is required with approval_limit_minor")
        elif currency is not None:
            if new_limit is None:
                raise ValidationError("currency requires approval_limit_minor")
            new_currency = currency

        updated = replace(
            staff,
            display_name=new_name,
            roles=new_roles,
            approval_limit_minor=new_limit,
            currency=new_currency,
        )
        saved = self._store.save(updated)
        kind = "ROLE_ASSIGNED" if roles is not None else "STAFF_UPDATED"
        self._store.append_activity(
            StaffActivity(
                event_id=_new_event_id(),
                staff_id=saved.staff_id,
                at=_rfc3339(self._clock),
                kind=kind,
                subject_ref=saved.merchant_ref,
                summary=f"Updated staff {saved.display_name}",
            )
        )
        return saved

    def deactivate(self, principal: Principal, staff_id: str) -> MerchantStaff:
        staff = self.get(principal, staff_id)
        if not staff.active:
            return staff
        saved = self._store.save(replace(staff, active=False))
        self._store.append_activity(
            StaffActivity(
                event_id=_new_event_id(),
                staff_id=saved.staff_id,
                at=_rfc3339(self._clock),
                kind="STAFF_DEACTIVATED",
                subject_ref=saved.merchant_ref,
                summary=f"Deactivated staff {saved.display_name}",
            )
        )
        return saved

    def list_activity(self, principal: Principal, staff_id: str) -> tuple[StaffActivity, ...]:
        self.get(principal, staff_id)
        return self._store.list_activity(staff_id=staff_id)

    def record_activity(
        self,
        principal: Principal,
        staff_id: str,
        *,
        kind: str,
        subject_ref: str,
        summary: str,
    ) -> StaffActivity:
        staff = self.get(principal, staff_id)
        if not kind or not kind.strip():
            raise ValidationError("kind is required")
        if not subject_ref or not subject_ref.strip():
            raise ValidationError("subject_ref is required")
        if not summary or not summary.strip():
            raise ValidationError("summary is required")

        kind_value = kind.strip()
        subject = subject_ref.strip()
        if kind_value in _CASE_ACTIVITY_KINDS:
            if not principal.allows_case(subject):
                raise UnauthorizedError("Unauthorized case scope")
            # Fail closed through the case-api peer; never invent case state.
            self._cases.get_case(subject, principal=principal)

        event = StaffActivity(
            event_id=_new_event_id(),
            staff_id=staff.staff_id,
            at=_rfc3339(self._clock),
            kind=kind_value,
            subject_ref=subject,
            summary=summary.strip(),
        )
        return self._store.append_activity(event)

    def advisory_check(
        self,
        principal: Principal,
        staff_id: str,
        *,
        amount_minor: int,
        currency: str,
    ) -> AdvisoryLimitResult:
        staff = self.get(principal, staff_id)
        if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
            raise ValidationError("amount_minor must be an integer")
        if amount_minor <= 0:
            raise ValidationError("amount_minor must be positive")
        if not currency:
            raise ValidationError("currency is required")
        try:
            return check_advisory_limit(staff, amount_minor=amount_minor, currency=currency)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def authorize_money(
        self,
        principal: Principal,
        staff_id: str,
        *,
        amount_minor: int,
        currency: str,
    ) -> None:
        """Explicit non-capability: advisory limits never authorize money movement."""
        del amount_minor, currency
        self.get(principal, staff_id)
        try:
            refuse_financial_authorization()
        except PermissionError as exc:
            raise FinancialAuthorityDenied(str(exc)) from exc
