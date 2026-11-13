import type { CaseClient, ShellConfig, VoiceClient } from "@/application/ports";
import { CONTRACT_SHA256, CONTRACT_VERSION, PeerError } from "@/domain/types";
import { createCaseApiStub } from "./fixture-case-client";
import { createVoiceStub } from "../../tests/stubs/voice";
import { createRealPeerCaseClient } from "./real-peer-case-client";

export type ShellRuntime = {
  config: ShellConfig;
  caseClient: CaseClient;
  voiceClient: VoiceClient | null;
};

function demoPrincipal(role: string) {
  const roles = [role];
  return {
    principal_id: `fixture-${role}`,
    tenant_id: "tenant-demo",
    roles,
    subject_refs: role === "customer" ? ["subject-demo-9"] : [],
    case_ids: role === "customer" ? ["case-demo-42"] : [],
  };
}

export function loadShellConfig(
  env: Record<string, string | undefined> = process.env as Record<
    string,
    string | undefined
  >,
): ShellConfig {
  const mode = (env.NEXT_PUBLIC_SHELL_MODE ?? "fixture") as ShellConfig["mode"];
  if (mode !== "fixture" && mode !== "real-peers") {
    throw new PeerError(
      "INVALID_CONFIG",
      `Unknown SHELL_MODE: ${mode}`,
      "cfg-mode",
    );
  }
  const role = env.NEXT_PUBLIC_DEMO_ROLE ?? "customer";
  return {
    mode,
    voiceEnabled: env.NEXT_PUBLIC_VOICE_ENABLED === "true",
    contractVersion: env.NEXT_PUBLIC_CONTRACT_VERSION ?? CONTRACT_VERSION,
    contractSha256: env.NEXT_PUBLIC_CONTRACT_SHA256 ?? CONTRACT_SHA256,
    caseApiBaseUrl: env.CASE_API_BASE_URL,
    bearerToken: env.CASE_API_BEARER_TOKEN ?? env.NEXT_PUBLIC_DEMO_TOKEN,
    principal: demoPrincipal(role),
  };
}

/**
 * Wire adapters once. Fixture mode uses local stubs.
 * Real-peer mode never silently falls back to fixtures.
 */
export function createShellRuntime(
  config: ShellConfig = loadShellConfig(),
  overrides?: {
    caseClient?: CaseClient;
    voiceClient?: VoiceClient | null;
    fetchImpl?: typeof fetch;
  },
): ShellRuntime {
  let caseClient: CaseClient;
  if (overrides?.caseClient) {
    caseClient = overrides.caseClient;
  } else if (config.mode === "fixture") {
    caseClient = createCaseApiStub("valid");
  } else {
    caseClient = createRealPeerCaseClient({
      baseUrl: config.caseApiBaseUrl ?? "",
      bearerToken: config.bearerToken ?? "",
      fetchImpl: overrides?.fetchImpl,
    });
  }

  let voiceClient: VoiceClient | null = null;
  if (overrides && "voiceClient" in overrides) {
    voiceClient = overrides.voiceClient ?? null;
  } else if (config.voiceEnabled) {
    voiceClient =
      config.mode === "fixture"
        ? createVoiceStub("valid")
        : createVoiceStub("unavailable");
  }

  return { config, caseClient, voiceClient };
}
