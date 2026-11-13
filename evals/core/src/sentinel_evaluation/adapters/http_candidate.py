from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from sentinel_evaluation.domain.models import CandidateObservation, EvalFixture


class HttpCandidateAdapter:
    """Injected HTTP adapter: POSTs fixture JSON, expects observation JSON."""

    def __init__(
        self,
        base_url: str,
        *,
        candidate_id: str = "http-candidate",
        model_mode: str = "fake",
        timeout_s: float = 5.0,
        opener: Any | None = None,
    ) -> None:
        self._url = base_url.rstrip("/")
        self.candidate_id = candidate_id
        self.model_mode = model_mode
        self._timeout_s = timeout_s
        self._opener = opener or urllib.request.urlopen

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        body = json.dumps(fixture.to_dict(), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self._timeout_s) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"candidate HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"candidate unreachable: {exc.reason}") from exc
        payload = json.loads(raw.decode("utf-8"))
        return CandidateObservation(
            terminal_state=str(payload["terminal_state"]),
            refund_side_effect_count=int(payload["refund_side_effect_count"]),
            refunded_minor=int(payload["refunded_minor"]),
            currency=str(payload["currency"]),
            actions=tuple(payload["actions"]),
            accessed_tenant_id=str(payload["accessed_tenant_id"]),
            claims_credit_confirmed=bool(payload["claims_credit_confirmed"]),
            approval_obtained=bool(payload["approval_obtained"]),
            model_mode=str(payload.get("model_mode") or self.model_mode),
        )
