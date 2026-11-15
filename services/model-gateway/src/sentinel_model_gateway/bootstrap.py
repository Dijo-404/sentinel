"""Composition root: environment -> Sarvam + knowledge adapters -> HTTP app. No fixture mode."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .adapters.http_api import AppServices, create_app
from .adapters.knowledge import HttpKnowledgeSearch
from .adapters.sarvam import SarvamChat
from .application.errors import ConfigurationError
from .application.service import ProposalService, ReplyService


def _token_set(raw: str) -> frozenset[str]:
    return frozenset(t.strip() for t in raw.split(",") if t.strip())


@dataclass(frozen=True)
class Settings:
    sarvam_api_key: str
    model: str
    sarvam_base_url: str
    max_tokens: int
    sarvam_timeout_s: float
    reasoning_effort: str | None
    proposal_tokens: frozenset[str]
    reply_tokens: frozenset[str]
    knowledge_url: str
    knowledge_token: str

    @classmethod
    def from_environ(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else os.environ
        tokens = _token_set(source.get("MODEL_GATEWAY_TOKENS", ""))
        if not tokens:
            raise ConfigurationError("MODEL_GATEWAY_TOKENS must list at least one bearer token")
        try:
            max_tokens = int(source.get("MODEL_GATEWAY_MAX_TOKENS", "4096"))
            timeout_s = float(source.get("MODEL_GATEWAY_SARVAM_TIMEOUT_S", "9"))
        except ValueError as exc:
            raise ConfigurationError("MODEL_GATEWAY_MAX_TOKENS/TIMEOUT_S must be numeric") from exc
        effort = source.get("MODEL_GATEWAY_REASONING_EFFORT", "off").strip() or "off"
        if effort not in {"off", "low", "medium", "high"}:
            raise ConfigurationError("MODEL_GATEWAY_REASONING_EFFORT must be off|low|medium|high")
        return cls(
            sarvam_api_key=source.get("SARVAM_API_KEY", "").strip(),
            model=source.get("MODEL_GATEWAY_MODEL", "sarvam-105b").strip() or "sarvam-105b",
            sarvam_base_url=source.get("MODEL_GATEWAY_SARVAM_BASE_URL", "https://api.sarvam.ai"),
            max_tokens=max_tokens,
            sarvam_timeout_s=timeout_s,
            reasoning_effort=None if effort == "off" else effort,
            proposal_tokens=tokens,
            reply_tokens=_token_set(source.get("MODEL_GATEWAY_REPLY_TOKENS", "")),
            knowledge_url=source.get("MODEL_GATEWAY_KNOWLEDGE_URL", "").strip(),
            knowledge_token=source.get("MODEL_GATEWAY_KNOWLEDGE_TOKEN", "").strip(),
        )


def build_app(settings: Settings | None = None, *, sarvam_client=None, knowledge_client=None):
    """`*_client` lets tests inject an httpx transport; runtime always uses real HTTP."""
    settings = settings or Settings.from_environ()
    chat = SarvamChat(
        settings.sarvam_api_key,
        settings.model,
        base_url=settings.sarvam_base_url,
        max_tokens=settings.max_tokens,
        timeout_s=settings.sarvam_timeout_s,
        reasoning_effort=settings.reasoning_effort,
        client=sarvam_client,
    )
    knowledge = HttpKnowledgeSearch(
        settings.knowledge_url, settings.knowledge_token, client=knowledge_client
    )
    return create_app(
        AppServices(
            proposals=ProposalService(chat),
            replies=ReplyService(chat, knowledge),
            proposal_tokens=settings.proposal_tokens,
            model=settings.model,
            reply_tokens=settings.reply_tokens,
        )
    )
