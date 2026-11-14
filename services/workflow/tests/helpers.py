"""Shared test wiring."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import sessionmaker

from sentinel_workflow.adapters.auth import TokenMapAuth, parse_token_map
from sentinel_workflow.adapters.db import SqlDecisionStore, SqlJobStore, SqlOutbox
from sentinel_workflow.adapters.http_api import create_app
from sentinel_workflow.adapters.model import FakeModelAdapter
from sentinel_workflow.adapters.settings import Settings
from sentinel_workflow.application.service import WorkflowService
from sentinel_workflow.graph.build import compile_workflow
from sentinel_workflow.graph.context import GraphDeps
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy, StubVerifier


def build_test_app(
    *,
    session_factory: sessionmaker,
    checkpointer: Any | None = None,
    model_scenario: str = "proposal",
    evidence_missing: bool = False,
    verifier_status: str = "WAITING",
    investigation_budget: int = 8,
    model_retry_budget: int = 2,
    outbox_max_attempts: int = 10,
    case_api: StubCaseApi | None = None,
    evidence: StubEvidence | None = None,
    policy: StubPolicy | None = None,
    ledger: StubLedger | None = None,
    verifier: StubVerifier | None = None,
):
    case_api = case_api or StubCaseApi()
    evidence = evidence or StubEvidence(missing=evidence_missing)
    policy = policy or StubPolicy()
    ledger = ledger or StubLedger()
    verifier = verifier or StubVerifier(assessment_status=verifier_status)
    outbox = SqlOutbox(session_factory, max_attempts=outbox_max_attempts)
    deps = GraphDeps(
        case_api=case_api,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        verifier=verifier,
        model=FakeModelAdapter(scenario=model_scenario),
        outbox=outbox,
    )
    graph = compile_workflow(checkpointer or MemorySaver())
    service = WorkflowService(
        jobs=SqlJobStore(session_factory),
        outbox=outbox,
        decisions=SqlDecisionStore(session_factory),
        case_api=case_api,
        graph=graph,
        deps=deps,
        investigation_budget=investigation_budget,
        model_retry_budget=model_retry_budget,
    )
    settings = Settings()
    auth = TokenMapAuth(parse_token_map(settings.token_map_raw()))
    app = create_app(service=service, auth=auth, mode="fixture")
    return (
        app,
        service,
        {
            "case_api": case_api,
            "evidence": evidence,
            "policy": policy,
            "ledger": ledger,
            "verifier": verifier,
        },
    )
