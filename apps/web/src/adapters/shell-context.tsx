"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { CaseClient, ShellConfig, VoiceClient } from "@/application/ports";
import { createShellRuntime, loadShellConfig } from "./composition";

type Ctx = {
  config: ShellConfig;
  caseClient: CaseClient;
  voiceClient: VoiceClient | null;
};

const ShellContext = createContext<Ctx | null>(null);

export function ShellProvider({
  children,
  caseClient,
  voiceClient,
  config,
}: {
  children: ReactNode;
  caseClient?: CaseClient;
  voiceClient?: VoiceClient | null;
  config?: ShellConfig;
}) {
  const value = useMemo(() => {
    const runtime = createShellRuntime(config ?? loadShellConfig(), {
      caseClient,
      voiceClient,
    });
    return {
      config: runtime.config,
      caseClient: runtime.caseClient,
      voiceClient: runtime.voiceClient,
    };
  }, [caseClient, voiceClient, config]);

  return (
    <ShellContext.Provider value={value}>{children}</ShellContext.Provider>
  );
}

export function useShell(): Ctx {
  const ctx = useContext(ShellContext);
  if (!ctx) {
    throw new Error("useShell requires ShellProvider");
  }
  return ctx;
}
