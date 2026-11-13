import json
from pathlib import Path

from sentinel_workflow import CONTRACT_SHA256, CONTRACT_VERSION
from sentinel_workflow.domain.types import Ack, WorkflowRequest


def test_contract_version_and_hash():
    assert CONTRACT_VERSION == "sentinel.task-contracts.v1"
    assert CONTRACT_SHA256 == "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"


def test_workflow_request_and_ack_fixtures():
    root = Path(__file__).resolve().parents[2] / "contracts"
    req = WorkflowRequest.model_validate(json.loads((root / "workflow_request.json").read_text()))
    assert req.event == "START"
    ack = Ack.model_validate(json.loads((root / "workflow_ack.json").read_text()))
    assert ack.accepted is True
