"""FastAPI boundary for knowledge.v1 routes (read-only articles)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..application.errors import KnowledgeError, ValidationError
from ..application.service import KnowledgeService
from ..domain.types import CONTRACT_VERSION, DEFAULT_SEARCH_LIMIT
from .auth import TokenAuthenticator


@dataclass
class AppServices:
    authenticator: TokenAuthenticator
    knowledge: KnowledgeService
    mode: str
    component: str = "knowledge"
    search: str = "substring"  # "semantic-hybrid" when backed by pgvector embeddings


def create_app(services: AppServices) -> FastAPI:
    app = FastAPI(title="sentinel-knowledge", version="0.1.0")
    app.state.services = services

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict:
        return {"status": "ready", "mode": services.mode}

    @app.get("/v1/capabilities")
    def capabilities() -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": services.component,
            "mode": services.mode,
            "search": services.search,
            "financial_authority": False,
        }

    @app.get("/v1/articles")
    def list_articles(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            articles = services.knowledge.list_articles(principal)
            return JSONResponse({"articles": [a.to_list_wire() for a in articles]})
        except KnowledgeError as exc:
            return _error(exc, request_id)

    @app.get("/v1/articles/{article_id}")
    def get_article(article_id: str, request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            article = services.knowledge.get_article(principal, article_id)
            return JSONResponse(article.to_detail_wire())
        except KnowledgeError as exc:
            return _error(exc, request_id)

    @app.get("/v1/search")
    def search(request: Request) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or f"request-{uuid.uuid4().hex[:12]}"
        try:
            principal = services.authenticator.authenticate(request.headers.get("authorization"))
            query = request.query_params.get("q")
            if query is None:
                raise ValidationError("q is required")
            raw_limit = request.query_params.get("limit")
            try:
                limit = int(raw_limit) if raw_limit is not None else DEFAULT_SEARCH_LIMIT
            except ValueError:
                raise ValidationError("limit must be an integer") from None
            hits = services.knowledge.search(principal, query, limit)
            return JSONResponse({"hits": [h.to_wire() for h in hits]})
        except KnowledgeError as exc:
            return _error(exc, request_id)

    return app


def _error(exc: KnowledgeError, request_id: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": exc.code,
            "message": exc.message,
            "request_id": getattr(exc, "request_id", None) or request_id,
        },
        status_code=exc.http_status,
    )
