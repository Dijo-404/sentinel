"use client";

import { useMemo, type ReactNode } from "react";
import { ShellProvider, useShell } from "@/adapters/shell-context";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import type { PortalRole } from "../../../tests/stubs/identity";

/**
 * Fixture portals bind case-stub decide() to the active assignment role.
 * Root ShellProvider only knows NEXT_PUBLIC_DEMO_ROLE, which breaks supervisor decide.
 * Real-peers keep the parent BFF client (server enforces roles).
 */
export function PortalCaseShell({
  role,
  children,
}: {
  role: PortalRole;
  children: ReactNode;
}) {
  const { config } = useShell();
  const caseClient = useMemo(() => {
    if (config.mode !== "fixture") return undefined;
    return createCaseApiStub("valid", { reviewerRole: role });
  }, [config.mode, role]);

  if (!caseClient) {
    return children;
  }

  return (
    <ShellProvider config={config} caseClient={caseClient}>
      {children}
    </ShellProvider>
  );
}
