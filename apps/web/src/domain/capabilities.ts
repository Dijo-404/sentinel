import { CONTRACT_VERSION } from "./types";

export type ShellMode = "fixture" | "real-peers";

export type CapabilitiesResponse = {
  contract_version: string;
  component: "web-shell";
  port: "web-shell.v1";
  mode: ShellMode;
};

/** Assembly-probe payload for GET /v1/capabilities. */
export function buildCapabilities(
  mode: ShellMode,
  contractVersion: string = CONTRACT_VERSION,
): CapabilitiesResponse {
  return {
    contract_version: contractVersion,
    component: "web-shell",
    port: "web-shell.v1",
    mode,
  };
}
