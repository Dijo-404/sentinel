import type {
  AssistantClient,
  AssistantMessage,
  AssistantThread,
} from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Seed-aligned fixture threads (synthetic; fixture mode only). */
export const FIXTURE_CUSTOMER_THREAD: AssistantThread = {
  thread_id: "thr-seed-tenant-demo",
  title: "Sandbox assistant thread",
  updated_at: "2026-11-15T10:00:00Z",
};

export const FIXTURE_OPERATOR_THREAD: AssistantThread = {
  thread_id: "thr-op-fixture-1",
  title: "Operator sandbox thread",
  updated_at: "2026-11-15T11:00:00Z",
};

export const FIXTURE_MESSAGES: AssistantMessage[] = [
  {
    message_id: "msg-seed-tenant-demo-user",
    role: "user",
    text: "Hello from tenant-demo sandbox seed.",
    evidence_mode: "sandbox",
    created_at: "2026-11-15T10:00:00Z",
  },
  {
    message_id: "msg-seed-tenant-demo-assistant",
    role: "assistant",
    text: "Sandbox assistant reply. Models propose only; no payment or ledger authority.",
    evidence_mode: "sandbox",
    created_at: "2026-11-15T10:00:01Z",
  },
];

export type AssistantStub = "valid" | "unavailable" | "empty";

export function createAssistantStub(
  scenario: AssistantStub = "valid",
): AssistantClient {
  if (scenario === "unavailable") {
    return {
      async listThreads() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "assistant peer unavailable",
          "req-as-unavailable",
          503,
        );
      },
      async listMessages() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "assistant peer unavailable",
          "req-as-unavailable",
          503,
        );
      },
      async postMessage() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "assistant peer unavailable",
          "req-as-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listThreads() {
        return { threads: [], source: "fixture" };
      },
      async listMessages() {
        return { messages: [], source: "fixture" };
      },
      async postMessage(_threadId, text) {
        return {
          message_id: "msg-empty-post",
          role: "user",
          text,
          evidence_mode: "sandbox",
          created_at: "2026-11-15T12:00:00Z",
        };
      },
    };
  }
  return {
    async listThreads(role) {
      const threads =
        role === "operator"
          ? [{ ...FIXTURE_OPERATOR_THREAD }]
          : [{ ...FIXTURE_CUSTOMER_THREAD }];
      return { threads, source: "fixture" };
    },
    async listMessages(threadId) {
      if (
        threadId !== FIXTURE_CUSTOMER_THREAD.thread_id &&
        threadId !== FIXTURE_OPERATOR_THREAD.thread_id
      ) {
        return { messages: [], source: "fixture" };
      }
      return {
        messages: FIXTURE_MESSAGES.map((m) => ({ ...m })),
        source: "fixture",
      };
    },
    async postMessage(threadId, text) {
      return {
        message_id: `msg-post-${threadId}`,
        role: "user",
        text,
        evidence_mode: "sandbox",
        created_at: "2026-11-15T12:00:00Z",
      };
    },
  };
}
