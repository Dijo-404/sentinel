import json
from pathlib import Path

from sentinel_workflow import CONTRACT_SHA256, CONTRACT_VERSION
from sentinel_workflow.domain.types import Ack, WorkflowRequest


def test_contract_version_and_hash():
    assert CONTRACT_VERSION == "sentinel.task-contracts.v1"
    assert CONTRACT_SHA256 == "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"


def test_workflow_request_and_ack_fixtures():
    root = Path(__file__).resolve().parents[2] / "contracts"
    req = WorkflowRequest.model_validate(json.loads((root / "workflow_request.json").read_text()))
    assert req.event == "START"
    ack = Ack.model_validate(json.loads((root / "workflow_ack.json").read_text()))
    assert ack.accepted is True
