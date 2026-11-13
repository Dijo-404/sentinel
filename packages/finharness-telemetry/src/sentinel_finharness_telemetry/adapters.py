"""Real-peer adapters: reject unavailable/malformed/unauthorized peers; no fixture fallback."""

from __future__ import annotations

from typing import Any

from .contracts import PeerError, RecordedMetric, RecordedSpan


def _require_mapping(payload: object, port: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PeerError(port, "malformed", "peer response must be an object")
    return payload


class RealTelemetryExporterAdapter:
    """Wraps a telemetry.v1 exporter peer. Failures stay visible."""

    def __init__(self, peer: Any) -> None:
        self._peer = peer

    def export_span(self, span: RecordedSpan) -> None:
        if self._peer is None:
            raise PeerError("telemetry.v1", "unavailable", "exporter peer missing")
        try:
            self._peer.export_span(span)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("telemetry.v1", "unavailable", str(exc)) from exc

    def export_metric(self, metric: RecordedMetric) -> None:
        if self._peer is None:
            raise PeerError("telemetry.v1", "unavailable", "exporter peer missing")
        try:
            self._peer.export_metric(metric)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("telemetry.v1", "unavailable", str(exc)) from exc


class RealRuntimeAdapter:
    """Wraps finharness-runtime.v1 observation peer."""

    REQUIRED = frozenset(
        {"case_id", "action_id", "model_version", "runtime_version", "contract_version"}
    )

    def __init__(self, peer: Any) -> None:
        self._peer = peer

    def observe_case(self, case_id: str) -> dict[str, Any]:
        if self._peer is None:
            raise PeerError("finharness-runtime.v1", "unavailable", "runtime peer missing")
        try:
            raw = self._peer.observe_case(case_id)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("finharness-runtime.v1", "unavailable", str(exc)) from exc
        payload = _require_mapping(raw, "finharness-runtime.v1")
        missing = self.REQUIRED - set(payload)
        if missing:
            raise PeerError(
                "finharness-runtime.v1",
                "malformed",
                f"missing fields: {sorted(missing)}",
            )
        if payload.get("case_id") != case_id:
            raise PeerError(
                "finharness-runtime.v1",
                "unauthorized_or_out_of_scope",
                "case scope mismatch",
            )
        return dict(payload)


class RealFinbenchAdapter:
    """Wraps finbench.v1 evaluation observation peer."""

    REQUIRED = frozenset(
        {
            "suite_id",
            "evaluation_version",
            "dataset_version",
            "hard_safety_pass",
            "contract_version",
        }
    )

    def __init__(self, peer: Any) -> None:
        self._peer = peer

    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        if self._peer is None:
            raise PeerError("finbench.v1", "unavailable", "finbench peer missing")
        try:
            raw = self._peer.observe_evaluation(suite_id)
        except PeerError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PeerError("finbench.v1", "unavailable", str(exc)) from exc
        payload = _require_mapping(raw, "finbench.v1")
        missing = self.REQUIRED - set(payload)
        if missing:
            raise PeerError("finbench.v1", "malformed", f"missing fields: {sorted(missing)}")
        if payload.get("suite_id") != suite_id:
            raise PeerError(
                "finbench.v1",
                "unauthorized_or_out_of_scope",
                "suite scope mismatch",
            )
        return dict(payload)
