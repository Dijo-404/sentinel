import pytest
from pydantic import ValidationError

from sentinel_finharness import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    CaseManifest,
    ConfigurationError,
    RuntimeConfig,
)


def test_defaults_disable_routing_writes_and_notifications():
    config = RuntimeConfig()
    assert config.enabled is False
    assert config.execution_mode == "legacy"
    assert config.financial_writes is False
    assert config.notifications is False
    assert config.routing_active() is False
    assert config.contract_version == CONTRACT_VERSION
    assert CONTRACT_SHA256.startswith("0db3ba2b")


def test_contract_version_pin_rejected():
    with pytest.raises((ConfigurationError, ValidationError)):
        RuntimeConfig.from_mapping({"contract_version": "other.v0"})


def test_manifest_requires_version_pins():
    with pytest.raises(ValidationError):
        CaseManifest.from_mapping(
            {
                "contract_version": CONTRACT_VERSION,
                "workflow_name": "duplicate_payment",
            }
        )


def test_manifest_roundtrip(manifest):
    assert manifest.workflow_name == "duplicate_payment"
    assert manifest.policy_version == "demo-policy-v1"
    assert manifest.model_adapter_version == "fake-model.v1"
