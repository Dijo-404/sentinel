import type {
  KnowledgeArticle,
  KnowledgeArticleSummary,
  KnowledgeClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type KnowledgePeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateSummary(
  row: unknown,
  index: number,
  requestId: string,
): KnowledgeArticleSummary {
  if (!row || typeof row !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      `Article[${index}] is not an object`,
      requestId,
    );
  }
  const o = row as Record<string, unknown>;
  if (
    typeof o.article_id !== "string" ||
    typeof o.title !== "string" ||
    typeof o.summary !== "string" ||
    typeof o.updated_at !== "string"
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      `Article[${index}] missing required fields`,
      requestId,
    );
  }
  return {
    article_id: o.article_id,
    title: o.title,
    summary: o.summary,
    updated_at: o.updated_at,
  };
}

function validateArticles(
  json: unknown,
  requestId: string,
): { articles: KnowledgeArticleSummary[]; source: string } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { articles?: unknown }).articles)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing articles array",
      requestId,
    );
  }
  const body = json as { articles: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim()
      ? body.source.trim()
      : "live";
  return {
    articles: body.articles.map((row, i) =>
      validateSummary(row, i, requestId),
    ),
    source,
  };
}

function validateHits(
  json: unknown,
  requestId: string,
): { hits: KnowledgeArticleSummary[]; source: string } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { hits?: unknown }).hits)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing hits array",
      requestId,
    );
  }
  const body = json as { hits: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim()
      ? body.source.trim()
      : "live";
  return {
    hits: body.hits.map((row, i) => validateSummary(row, i, requestId)),
    source,
  };
}

function validateArticle(
  json: unknown,
  requestId: string,
): KnowledgeArticle {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Article response is not an object",
      requestId,
    );
  }
  const summary = validateSummary(json, 0, requestId);
  const o = json as Record<string, unknown>;
  if (typeof o.body !== "string") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Article missing body",
      requestId,
    );
  }
  return { ...summary, body: o.body };
}

export function createRealPeerKnowledgeClient(
  options: KnowledgePeerOptions,
): KnowledgeClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "knowledge",
  });

  return {
    listArticles() {
      return request("GET", "/v1/articles", validateArticles);
    },
    getArticle(articleId) {
      return request(
        "GET",
        `/v1/articles/${encodeURIComponent(articleId)}`,
        validateArticle,
      );
    },
    search(q) {
      const params = new URLSearchParams({ q });
      return request("GET", `/v1/search?${params}`, validateHits);
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffKnowledgeClient(options?: {
  fetchImpl?: typeof fetch;
}): KnowledgeClient {
  return createRealPeerKnowledgeClient({
    baseUrl: "/api/bff/knowledge",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
