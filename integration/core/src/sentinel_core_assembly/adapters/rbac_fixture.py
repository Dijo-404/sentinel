"""Fixture-mode RBAC probes (AUTH-01 invite + AUTH-06 decide deny).

Path label: rbac-fixture. Does not exercise SN-009 ledger authority or the
full case→workflow→dispatcher money path. Local doubles only — not live peers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_core_assembly.adapters.sandbox_matrix import rbac_path_label
from sentinel_core_assembly.domain.types import CONTRACT_VERSION, Capabilities

_PRIVILEGED_REGISTER_FIELDS = frozenset(
    {"role", "roles", "role_id", "account_type", "tenant_id", "subject_refs"}
)
_STAFF_ROLES = frozenset(
    {"operator", "supervisor", "platform_admin", "risk_officer", "admin", "merchant"}
)


@dataclass
class RbacFixtureWorld:
    """In-process synthetic identity + decision gate state."""

    accounts: dict[str, dict[str, object]] = field(default_factory=dict)
    invitations: dict[str, dict[str, object]] = field(default_factory=dict)
    ledger_decision_calls: list[dict[str, object]] = field(default_factory=list)
    invite_seq: int = 0


@dataclass
class RbacFixtureProbe:
    """AUTH probes against local doubles for identity + decision authz.

    Optional peer ports identity.v1 / risk.v1 appear in capabilities for matrix
    alignment; probes do not call live HTTP and never set sn009 authority.
    """

    world: RbacFixtureWorld = field(default_factory=RbacFixtureWorld)
    path: str = field(default_factory=rbac_path_label)
    sn009_authority_exercised: bool = False

    def capabilities_by_port(self) -> dict[str, Capabilities]:
        return {
            "identity.v1": Capabilities(
                contract_version=CONTRACT_VERSION,
                component="reference-identity",
                mode="fixture",
                port="identity.v1",
            ),
            "risk.v1": Capabilities(
                contract_version=CONTRACT_VERSION,
                component="reference-risk",
                mode="fixture",
                port="risk.v1",
            ),
            "case-api.v1": Capabilities(
                contract_version=CONTRACT_VERSION,
                component="reference-case-api",
                mode="fixture",
                port="case-api.v1",
            ),
        }

    def customer_register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        extra_fields: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """AUTH-01 / AUTH-02: reject privileged self-register fields."""
        extra = dict(extra_fields or {})
        privileged = sorted(k for k in extra if k in _PRIVILEGED_REGISTER_FIELDS)
        if privileged:
            return {
                "status_code": 422,
                "denied": True,
                "reason_code": "PRIVILEGED_REGISTER_FIELD_REJECTED",
                "rejected_fields": privileged,
                "account_created": False,
                "path": self.path,
                "sn009_authority_exercised": False,
            }
        if email in self.world.accounts:
            return {
                "status_code": 409,
                "denied": True,
                "reason_code": "EMAIL_EXISTS",
                "account_created": False,
                "path": self.path,
                "sn009_authority_exercised": False,
            }
        self.world.accounts[email] = {
            "email": email,
            "password": password,
            "display_name": display_name,
            "account_type": "customer",
            "role_id": "customer",
        }
        return {
            "status_code": 201,
            "denied": False,
            "account_created": True,
            "account_type": "customer",
            "role_id": "customer",
            "path": self.path,
            "sn009_authority_exercised": False,
        }

    def admin_invite_staff(
        self,
        *,
        actor_role: str,
        work_email: str,
        role_id: str,
        tenant_id: str = "tenant-demo",
        display_name: str = "Invited Staff",
    ) -> dict[str, object]:
        """Platform admin may invite staff; customer role invite denied (AUTH-11)."""
        if actor_role != "platform_admin":
            return {
                "status_code": 403,
                "denied": True,
                "reason_code": "ADMIN_REQUIRED",
                "invitation_created": False,
                "path": self.path,
                "sn009_authority_exercised": False,
            }
        if role_id == "customer" or role_id not in _STAFF_ROLES:
            return {
                "status_code": 422,
                "denied": True,
                "reason_code": "STAFF_INVITE_ROLE_INVALID",
                "invitation_created": False,
                "path": self.path,
                "sn009_authority_exercised": False,
            }
        self.world.invite_seq += 1
        invitation_id = f"inv-fixture-{self.world.invite_seq}"
        self.world.invitations[invitation_id] = {
            "invitation_id": invitation_id,
            "work_email": work_email,
            "role_id": role_id,
            "tenant_id": tenant_id,
            "display_name": display_name,
            "status": "pending",
        }
        return {
            "status_code": 201,
            "denied": False,
            "invitation_created": True,
            "invitation_id": invitation_id,
            "role_id": role_id,
            "work_email": work_email,
            "path": self.path,
            "sn009_authority_exercised": False,
        }

    def decide(
        self,
        *,
        actor_role: str,
        action_id: str,
        decision: str = "APPROVE",
    ) -> dict[str, object]:
        """AUTH-06: only supervisor may decide; operator denied; ledger untouched."""
        if actor_role != "supervisor":
            return {
                "status_code": 403,
                "denied": True,
                "reason_code": "SUPERVISOR_REQUIRED",
                "ledger_called": False,
                "ledger_decision_count": len(self.world.ledger_decision_calls),
                "action_id": action_id,
                "path": self.path,
                "sn009_authority_exercised": False,
            }
        # Fixture probe records intent only — still not SN-009 authority evidence.
        self.world.ledger_decision_calls.append(
            {"action_id": action_id, "decision": decision, "actor_role": actor_role}
        )
        return {
            "status_code": 202,
            "denied": False,
            "ledger_called": True,
            "ledger_decision_count": len(self.world.ledger_decision_calls),
            "action_id": action_id,
            "path": self.path,
            "sn009_authority_exercised": False,
        }

    def run_auth_probes(self) -> dict[str, object]:
        """AUTH-01 staff-role register deny, admin invite, AUTH-06 operator decide."""
        register = self.customer_register(
            email="rbac-probe-customer@example.test",
            password="demo-password-not-secret",
            display_name="RBAC Probe Customer",
            extra_fields={"role": "admin"},
        )
        invite = self.admin_invite_staff(
            actor_role="platform_admin",
            work_email="rbac-probe-operator@example.test",
            role_id="operator",
            display_name="RBAC Probe Operator",
        )
        before = len(self.world.ledger_decision_calls)
        decide = self.decide(
            actor_role="operator",
            action_id="action-rbac-auth06",
            decision="APPROVE",
        )
        after = len(self.world.ledger_decision_calls)
        ok = (
            register.get("denied") is True
            and register.get("status_code") == 422
            and not register.get("account_created")
            and invite.get("invitation_created") is True
            and invite.get("status_code") == 201
            and decide.get("denied") is True
            and decide.get("status_code") == 403
            and before == after == 0
            and decide.get("ledger_called") is False
        )
        return {
            "path": self.path,
            "sn009_authority_exercised": False,
            "auth01_register_denied": register,
            "admin_invite_staff": invite,
            "auth06_operator_decide": decide,
            "probes_passed": ok,
        }
