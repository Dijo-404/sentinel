"""Real-peer adapters reject unavailable/malformed/unauthorized peers."""

import pytest
from stubs.finbench import (
    MalformedFinbench,
    UnauthorizedFinbench,
    UnavailableFinbench,
    ValidFinbench,
)
from stubs.finharness_runtime import (
    MalformedRuntime,
    UnauthorizedRuntime,
    UnavailableRuntime,
    ValidRuntime,
)
from stubs.telemetry import UnauthorizedTelemetry, UnavailableTelemetry, ValidTelemetryExporter

from sentinel_finharness_telemetry.adapters import (
    RealFinbenchAdapter,
    RealRuntimeAdapter,
    RealTelemetryExporterAdapter,
)
from sentinel_finharness_telemetry.contracts import PeerError, RecordedMetric, RecordedSpan


def test_valid_runtime_and_finbench_adapters() -> None:
    runtime = RealRuntimeAdapter(ValidRuntime()).observe_case("case-demo-42")
    assert runtime["model_version"] == "demo-model-v1"
    eval_obs = RealFinbenchAdapter(ValidFinbench()).observe_evaluation("finbench-indic-demo")
    assert eval_obs["evaluation_version"] == "finbench-eval-v1"
    assert eval_obs["evidence_mode"] == "fixture"


def test_unavailable_peers_fail_explicitly() -> None:
    with pytest.raises(PeerError) as runtime_exc:
        RealRuntimeAdapter(UnavailableRuntime()).observe_case("case-demo-42")
    assert runtime_exc.value.kind == "unavailable"

    with pytest.raises(PeerError) as finbench_exc:
        RealFinbenchAdapter(UnavailableFinbench()).observe_evaluation("finbench-indic-demo")
    assert finbench_exc.value.kind == "unavailable"

    with pytest.raises(PeerError) as telemetry_exc:
        RealTelemetryExporterAdapter(UnavailableTelemetry()).export_span(
            RecordedSpan(name="x", attributes={})
        )
    assert telemetry_exc.value.kind == "unavailable"


def test_malformed_peers_fail_explicitly() -> None:
    with pytest.raises(PeerError) as runtime_exc:
        RealRuntimeAdapter(MalformedRuntime()).observe_case("case-demo-42")
    assert runtime_exc.value.kind == "malformed"

    with pytest.raises(PeerError) as finbench_exc:
        RealFinbenchAdapter(MalformedFinbench()).observe_evaluation("finbench-indic-demo")
    assert finbench_exc.value.kind == "malformed"


def test_unauthorized_peers_fail_explicitly() -> None:
    with pytest.raises(PeerError) as runtime_exc:
        RealRuntimeAdapter(UnauthorizedRuntime()).observe_case("case-demo-42")
    assert runtime_exc.value.kind == "unauthorized_or_out_of_scope"

    with pytest.raises(PeerError) as finbench_exc:
        RealFinbenchAdapter(UnauthorizedFinbench()).observe_evaluation("finbench-indic-demo")
    assert finbench_exc.value.kind == "unauthorized_or_out_of_scope"

    with pytest.raises(PeerError) as telemetry_exc:
        RealTelemetryExporterAdapter(UnauthorizedTelemetry()).export_metric(
            RecordedMetric(name="m", value=1.0, labels={})
        )
    assert telemetry_exc.value.kind == "unauthorized_or_out_of_scope"


def test_missing_peer_objects_fail_explicitly() -> None:
    with pytest.raises(PeerError) as exc:
        RealRuntimeAdapter(None).observe_case("case-demo-42")
    assert exc.value.kind == "unavailable"

    exporter = ValidTelemetryExporter()
    RealTelemetryExporterAdapter(exporter).export_span(RecordedSpan(name="ok", attributes={}))
    assert len(exporter.collector.spans) == 1
