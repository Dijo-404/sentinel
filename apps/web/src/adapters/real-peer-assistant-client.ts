import type {
  AssistantClient,
  AssistantMessage,
  AssistantRole,
  AssistantThread,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type AssistantPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateThreads(
  json: unknown,
  requestId: string,
): { threads: AssistantThread[]; source: string } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { threads?: unknown }).threads)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing threads array",
      requestId,
    );
  }
  const body = json as { threads: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim()
      ? body.source.trim()
      : "live";

  const threads = body.threads.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Thread[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.thread_id !== "string" ||
      typeof o.title !== "string" ||
      typeof o.updated_at !== "string"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Thread[${i}] missing required fields`,
        requestId,
      );
    }
    return {
      thread_id: o.thread_id,
      title: o.title,
      updated_at: o.updated_at,
    };
  });

  return { threads, source };
}

function validateMessages(
  json: unknown,
  requestId: string,
): { messages: AssistantMessage[]; source: string } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { messages?: unknown }).messages)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing messages array",
      requestId,
    );
  }
  const body = json as { messages: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim()
      ? body.source.trim()
      : "live";

  const messages = body.messages.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Message[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.message_id !== "string" ||
      typeof o.role !== "string" ||
      typeof o.text !== "string" ||
      typeof o.evidence_mode !== "string" ||
      typeof o.created_at !== "string"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Message[${i}] missing required fields`,
        requestId,
      );
    }
    let role: AssistantMessage["role"];
    if (o.role === "user" || o.role === "assistant" || o.role === "system") {
      role = o.role;
    } else {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Message[${i}] has invalid role`,
        requestId,
      );
    }
    const message: AssistantMessage = {
      message_id: o.message_id,
      role,
      text: o.text,
      evidence_mode: o.evidence_mode,
      created_at: o.created_at,
    };
    return message;
  });

  return { messages, source };
}

function validateMessage(
  json: unknown,
  requestId: string,
): AssistantMessage {
  const wrapped = validateMessages(
    { messages: [json], source: "live" },
    requestId,
  );
  return wrapped.messages[0]!;
}

export function createRealPeerAssistantClient(
  options: AssistantPeerOptions,
): AssistantClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "assistant",
  });

  return {
    listThreads(role: AssistantRole) {
      const params = new URLSearchParams({ role });
      return request("GET", `/v1/threads?${params}`, validateThreads);
    },
    listMessages(threadId) {
      return request(
        "GET",
        `/v1/threads/${encodeURIComponent(threadId)}/messages`,
        validateMessages,
      );
    },
    postMessage(threadId, text) {
      return request(
        "POST",
        `/v1/threads/${encodeURIComponent(threadId)}/messages`,
        validateMessage,
        { text },
      );
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffAssistantClient(options?: {
  fetchImpl?: typeof fetch;
}): AssistantClient {
  return createRealPeerAssistantClient({
    baseUrl: "/api/bff/assistant",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
