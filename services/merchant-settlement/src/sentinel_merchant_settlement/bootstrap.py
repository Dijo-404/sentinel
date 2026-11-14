"""Composition root: config, tokens, peers, app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sentinel_merchant_settlement.adapters.auth import TokenMap
from sentinel_merchant_settlement.adapters.evidence_http import HttpEvidence
from sentinel_merchant_settlement.adapters.evidence_stub import StubEvidence
from sentinel_merchant_settlement.adapters.http import AppServices, create_app
from sentinel_merchant_settlement.adapters.provider_http import HttpPaymentProvider
from sentinel_merchant_settlement.adapters.provider_stub import StubPaymentProvider
from sentinel_merchant_settlement.adapters.store_memory import MemoryFindingStore
from sentinel_merchant_settlement.application.errors import ConfigurationError
from sentinel_merchant_settlement.application.findings import ManageFindings
from sentinel_merchant_settlement.application.import_batch import ImportSettlementBatch
from sentinel_merchant_settlement.domain.types import CONTRACT_VERSION

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"


@dataclass(frozen=True)
class Settings:
    mode: str
    principals_path: Path
    contract_version: str
    evidence_base_url: str
    evidence_token: str
    provider_base_url: str
    provider_token: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else dict(os.environ)
        mode = source.get("MERCHANT_SETTLEMENT_MODE", "fixture")
        if mode not in {"fixture", "real-peers"}:
            raise ConfigurationError("MERCHANT_SETTLEMENT_MODE must be fixture or real-peers")
        path = Path(source.get("MERCHANT_SETTLEMENT_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS)))
        if not path.is_absolute():
            path = (MODULE_ROOT / path).resolve()
        return cls(
            mode=mode,
            principals_path=path,
            contract_version=source.get("MERCHANT_SETTLEMENT_CONTRACT_VERSION", CONTRACT_VERSION),
            evidence_base_url=source.get("EVIDENCE_BASE_URL", ""),
            evidence_token=source.get("EVIDENCE_TOKEN", ""),
            provider_base_url=source.get("PAYMENT_PROVIDER_BASE_URL", ""),
            provider_token=source.get("PAYMENT_PROVIDER_TOKEN", ""),
        )


def build_app(
    settings: Settings | None = None,
    *,
    evidence=None,
    provider=None,
    store=None,
):
    settings = settings or Settings.from_environ()
    if settings.contract_version != CONTRACT_VERSION:
        raise ConfigurationError("Unsupported contract version")

    tokens = TokenMap.from_path(settings.principals_path)
    mode = settings.mode

    if mode == "fixture":
        evidence_port = evidence if evidence is not None else StubEvidence()
        provider_port = provider if provider is not None else StubPaymentProvider()
    else:
        if evidence is not None or provider is not None:
            # Tests may inject real-peer doubles that still fail closed.
            evidence_port = (
                evidence
                if evidence is not None
                else HttpEvidence(
                    base_url=settings.evidence_base_url,
                    token=settings.evidence_token,
                )
            )
            provider_port = (
                provider
                if provider is not None
                else HttpPaymentProvider(
                    base_url=settings.provider_base_url,
                    token=settings.provider_token,
                )
            )
        else:
            evidence_port = HttpEvidence(
                base_url=settings.evidence_base_url,
                token=settings.evidence_token,
            )
            provider_port = HttpPaymentProvider(
                base_url=settings.provider_base_url,
                token=settings.provider_token,
            )

    if store is not None:
        finding_store = store
    elif mode == "real-peers":
        raise ConfigurationError(
            "real-peers requires an injected durable finding store "
            "(MemoryFindingStore defaults are not allowed across workers)"
        )
    else:
        finding_store = MemoryFindingStore()
    import_uc = ImportSettlementBatch(
        evidence=evidence_port,
        provider=provider_port,
        store=finding_store,
    )
    findings_uc = ManageFindings(finding_store)
    return create_app(
        AppServices(
            tokens=tokens,
            import_batch=import_uc,
            findings=findings_uc,
            mode=mode,
        )
    )
