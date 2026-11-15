import type {
  KnowledgeArticle,
  KnowledgeArticleSummary,
  KnowledgeClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Seed-aligned fixture article (synthetic; fixture mode only). */
export const FIXTURE_ARTICLE: KnowledgeArticle = {
  article_id: "article-demo-refund-policy",
  title: "Sandbox refund policy",
  summary: "Synthetic guidance for duplicate-charge refunds.",
  body: "Synthetic sandbox article. No money authority.",
  updated_at: "2026-11-14T10:00:00Z",
};

export const FIXTURE_ARTICLE_SUMMARY: KnowledgeArticleSummary = {
  article_id: FIXTURE_ARTICLE.article_id,
  title: FIXTURE_ARTICLE.title,
  summary: FIXTURE_ARTICLE.summary,
  updated_at: FIXTURE_ARTICLE.updated_at,
};

export type KnowledgeStub = "valid" | "unavailable" | "empty";

export function createKnowledgeStub(scenario: KnowledgeStub = "valid"): KnowledgeClient {
  if (scenario === "unavailable") {
    return {
      async listArticles() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "knowledge peer unavailable",
          "req-kn-unavailable",
          503,
        );
      },
      async getArticle() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "knowledge peer unavailable",
          "req-kn-unavailable",
          503,
        );
      },
      async search() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "knowledge peer unavailable",
          "req-kn-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listArticles() {
        return { articles: [], source: "fixture" };
      },
      async getArticle() {
        throw new PeerError("NOT_FOUND", "Article not found", "req-kn-missing", 404);
      },
      async search() {
        return { hits: [], source: "fixture" };
      },
    };
  }
  return {
    async listArticles() {
      return {
        articles: [{ ...FIXTURE_ARTICLE_SUMMARY }],
        source: "fixture",
      };
    },
    async getArticle(articleId) {
      if (articleId !== FIXTURE_ARTICLE.article_id) {
        throw new PeerError("NOT_FOUND", "Article not found", "req-kn-missing", 404);
      }
      return { ...FIXTURE_ARTICLE };
    },
    async search(q) {
      const needle = q.trim().toLowerCase();
      const hits =
        !needle ||
        FIXTURE_ARTICLE.title.toLowerCase().includes(needle) ||
        FIXTURE_ARTICLE.summary.toLowerCase().includes(needle)
          ? [{ ...FIXTURE_ARTICLE_SUMMARY }]
          : [];
      return { hits, source: "fixture" };
    },
  };
}
