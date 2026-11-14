"""Composition root: wire adapters once."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import sessionmaker

from sentinel_workflow.adapters.auth import TokenMapAuth, parse_token_map
from sentinel_workflow.adapters.db import (
    SqlDecisionStore,
    SqlJobStore,
    SqlOutbox,
    make_engine,
    migrate,
)
from sentinel_workflow.adapters.http_api import create_app
from sentinel_workflow.adapters.model import FakeModelAdapter, HttpModelAdapter
from sentinel_workflow.adapters.peers_http import (
    HttpCaseApi,
    HttpEvidence,
    HttpLedger,
    HttpPolicy,
    HttpRisk,
    HttpVerifier,
)
from sentinel_workflow.adapters.settings import Settings
from sentinel_workflow.application.service import WorkflowService
from sentinel_workflow.graph.build import compile_workflow
from sentinel_workflow.graph.context import GraphDeps


@dataclass
class AppContainer:
    settings: Settings
    app: Any
    service: WorkflowService
    engine: Any
    checkpointer: Any


def build_container(
    settings: Settings | None = None,
    *,
    peers: dict[str, Any] | None = None,
    checkpointer: Any | None = None,
) -> AppContainer:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    migrate(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    if checkpointer is None:
        checkpointer = _postgres_checkpointer(settings.database_url)
    graph = compile_workflow(checkpointer)

    if peers is None:
        peers = _default_peers(settings)

    model = peers.get("model")
    if model is None:
        if settings.model_mode == "http":
            model = HttpModelAdapter(settings.peer_model_url, settings.outbound_bearer)
        else:
            model = FakeModelAdapter(
                scenario=settings.fake_model_scenario,
                policy_version=settings.policy_version,
            )

    deps = GraphDeps(
        case_api=peers["case_api"],
        evidence=peers["evidence"],
        policy=peers["policy"],
        ledger=peers["ledger"],
        verifier=peers["verifier"],
        model=model,
        outbox=SqlOutbox(
            session_factory,
            max_attempts=settings.outbox_max_attempts,
            backoff_base_seconds=settings.outbox_backoff_base_seconds,
        ),
        risk=peers["risk"],
        policy_version=settings.policy_version,
    )
    service = WorkflowService(
        jobs=SqlJobStore(session_factory),
        outbox=deps.outbox,
        decisions=SqlDecisionStore(session_factory),
        case_api=deps.case_api,
        graph=graph,
        deps=deps,
        investigation_budget=settings.investigation_budget,
        model_retry_budget=settings.model_retry_budget,
    )
    auth = TokenMapAuth(parse_token_map(settings.token_map_raw()))
    app = create_app(service=service, auth=auth, mode=settings.mode)
    return AppContainer(
        settings=settings,
        app=app,
        service=service,
        engine=engine,
        checkpointer=checkpointer,
    )


def _default_peers(settings: Settings) -> dict[str, Any]:
    if settings.mode == "real-peers":
        token = settings.outbound_bearer
        return {
            "case_api": HttpCaseApi(settings.peer_case_api_url, token),
            "evidence": HttpEvidence(settings.peer_evidence_url, token),
            "policy": HttpPolicy(settings.peer_policy_url, token),
            "ledger": HttpLedger(settings.peer_ledger_url, token),
            "verifier": HttpVerifier(settings.peer_verifier_url, token),
            "risk": HttpRisk(settings.peer_risk_url, token),
        }
    from sentinel_workflow.adapters.fixture_peers import (
        FixtureCaseApi,
        FixtureEvidence,
        FixtureLedger,
        FixturePolicy,
        FixtureRisk,
        FixtureVerifier,
    )

    return {
        "case_api": FixtureCaseApi(),
        "evidence": FixtureEvidence(),
        "policy": FixturePolicy(),
        "ledger": FixtureLedger(),
        "verifier": FixtureVerifier(),
        "risk": FixtureRisk(),
    }


def _postgres_checkpointer(database_url: str) -> Any:
    # langgraph-checkpoint-postgres expects a psycopg connection string.
    from langgraph.checkpoint.postgres import PostgresSaver

    dsn = database_url
    if dsn.startswith("postgresql+psycopg://"):
        dsn = "postgresql://" + dsn.removeprefix("postgresql+psycopg://")
    saver = PostgresSaver.from_conn_string(dsn)
    # from_conn_string returns a context manager in some versions; normalize.
    if hasattr(saver, "__enter__"):
        # Keep the context open for process lifetime.
        cm = saver
        saver = cm.__enter__()
        saver.setup()
        return saver
    saver.setup()
    return saver
