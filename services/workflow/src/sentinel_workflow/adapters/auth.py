"""Synthetic bearer-token principal resolution. Headers/body never establish identity."""

from __future__ import annotations

from sentinel_workflow.application.errors import UnauthorizedError, ValidationError
from sentinel_workflow.domain.types import Principal


class TokenMapAuth:
    def __init__(self, tokens: dict[str, Principal]) -> None:
        self._tokens = tokens

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        principal = self._tokens.get(token)
        if principal is None:
            raise UnauthorizedError("Unknown token")
        return principal

    def require_run_principal(self, principal: Principal, case_id: str) -> None:
        roles = set(principal.roles)
        if not roles.intersection({"workflow", "verifier"}):
            raise UnauthorizedError("Role cannot start workflow runs")
        if case_id not in principal.case_ids and "*" not in principal.case_ids:
            raise UnauthorizedError("Case out of scope")


def parse_token_map(raw: dict[str, dict]) -> dict[str, Principal]:
    out: dict[str, Principal] = {}
    for token, body in raw.items():
        try:
            out[token] = Principal.model_validate(body)
        except Exception as exc:
            raise ValidationError(f"Invalid auth token map entry for {token}") from exc
    return out
