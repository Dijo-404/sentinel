import { NextResponse } from "next/server";
import { loadShellConfig } from "@/adapters/composition";
import { buildCapabilities } from "@/domain/capabilities";

/** Assembly probe: contract_version, component, port, mode. */
export function GET() {
  const config = loadShellConfig();
  return NextResponse.json(
    buildCapabilities(config.mode, config.contractVersion),
  );
}
