"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createKnowledgeClientForMode } from "@/adapters/composition-peers";
import type { KnowledgeArticleSummary, KnowledgeClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to mode-wired BFF / fixture client. */
  knowledgeClient?: KnowledgeClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      articles: KnowledgeArticleSummary[];
      source: string;
      label: "live" | "fixture";
    };

/**
 * Operator Knowledge: articles via same-origin BFF `/api/bff/knowledge`
 * → knowledge `GET /v1/articles` (+ search). Real-peer failure stays visible —
 * never “Not available yet”.
 */
export function KnowledgePanel({ knowledgeClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (knowledgeClient === null) return null;
    if (knowledgeClient) return knowledgeClient;
    return createKnowledgeClientForMode(config.mode);
  }, [knowledgeClient, config.mode]);

  const [query, setQuery] = useState("");
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Knowledge client not configured",
          });
        }
        return;
      }
      try {
        const { articles, source } = await client.listArticles();
        if (cancelled) return;
        if (articles.length === 0) {
          setLoad({ status: "empty", source });
          return;
        }
        setLoad({
          status: "ready",
          articles,
          source,
          label: config.mode === "fixture" ? "fixture" : "live",
        });
      } catch (err) {
        if (cancelled) return;
        const detail =
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Load failed";
        setLoad({ status: "error", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [client, config.mode]);

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!client) {
      setLoad({
        status: "error",
        detail: "Knowledge client not configured",
      });
      return;
    }
    setLoad({ status: "loading" });
    try {
      const q = query.trim();
      if (!q) {
        const { articles, source } = await client.listArticles();
        if (articles.length === 0) {
          setLoad({ status: "empty", source });
          return;
        }
        setLoad({
          status: "ready",
          articles,
          source,
          label: config.mode === "fixture" ? "fixture" : "live",
        });
        return;
      }
      const { hits, source } = await client.search(q);
      if (hits.length === 0) {
        setLoad({ status: "empty", source });
        return;
      }
      setLoad({
        status: "ready",
        articles: hits,
        source,
        label: config.mode === "fixture" ? "fixture" : "live",
      });
    } catch (err) {
      const detail =
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Search failed";
      setLoad({ status: "error", detail });
    }
  }

  return (
    <div className="panel stack" data-testid="operator-knowledge">
      <h1>Knowledge</h1>
      <p className="muted">
        Articles from knowledge <code>GET /v1/articles</code> / <code>/v1/search</code>. Citation
        only — no money authority.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      <form className="stack" onSubmit={onSearch}>
        <label>
          Search
          <input
            type="search"
            name="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            data-testid="operator-knowledge-search"
          />
        </label>
        <button type="submit">Search</button>
      </form>

      {load.status === "loading" ? <UiState tone="loading" title="Loading knowledge…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Knowledge unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No articles" detail="No knowledge rows match this query." />
      ) : null}
      {load.status === "ready" ? (
        <ul className="stack" aria-label="Knowledge articles" data-testid="operator-knowledge-list">
          {load.articles.map((row) => (
            <li key={row.article_id} className="stack">
              <strong>{row.title}</strong>
              <p className="mono muted" style={{ margin: 0 }}>
                {row.article_id}
              </p>
              <p style={{ margin: 0 }}>{row.summary}</p>
              <p className="muted" style={{ margin: 0 }}>
                Updated {row.updated_at}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
