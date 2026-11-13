from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import PeerError

from ._payloads import SDK_READ_RESULT


class ValidFinHarnessSdk:
    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(SDK_READ_RESULT)


class UnavailableFinHarnessSdk:
    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("finharness-sdk.v1", "unavailable", "sdk peer not reachable")


class MalformedFinHarnessSdk:
    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"outcome": "PROPOSAL"}


class UnauthorizedFinHarnessSdk:
    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "finharness-sdk.v1",
            "unauthorized_or_out_of_scope",
            "sdk principal denied for tenant",
        )
