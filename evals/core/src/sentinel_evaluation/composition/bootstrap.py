from __future__ import annotations

from pathlib import Path

from sentinel_evaluation.adapters.assembly import RejectingRealAssemblyPeer, StubAssemblyPeer
from sentinel_evaluation.adapters.candidates import build_candidate
from sentinel_evaluation.adapters.fixtures import FileFixtureDataset
from sentinel_evaluation.adapters.http_candidate import HttpCandidateAdapter
from sentinel_evaluation.application.evaluate import EvaluateService


def build_service(
    *,
    candidate: str = "conforming",
    mode: str = "fixture",
    assembly_stub: str = "valid",
    candidate_url: str | None = None,
    dataset_root: Path | None = None,
    output_dir: Path | None = None,
) -> EvaluateService:
    dataset = FileFixtureDataset(dataset_root)
    if candidate_url:
        runner = HttpCandidateAdapter(candidate_url, model_mode="fake")
    else:
        runner = build_candidate(candidate)
    if mode == "real-peers":
        # Explicit stub selection exercises negative peer cases; no silent fixture fallback.
        if assembly_stub and assembly_stub != "live":
            assembly = StubAssemblyPeer(assembly_stub)
        else:
            assembly = RejectingRealAssemblyPeer(candidate_url)
    else:
        assembly = StubAssemblyPeer(assembly_stub)
    return EvaluateService(dataset, runner, assembly, output_dir=output_dir)


def build_fixture_runner(**kwargs) -> EvaluateService:
    return build_service(mode="fixture", **kwargs)
