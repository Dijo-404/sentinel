import type { DecisionUiCode, WireError } from "./types.js";

export class DecisionClientError extends Error {
  readonly status: number;
  readonly error: WireError;
  readonly uiCode: DecisionUiCode;

  constructor(status: number, error: WireError, uiCode: DecisionUiCode) {
    super(error.message);
    this.name = "DecisionClientError";
    this.status = status;
    this.error = error;
    this.uiCode = uiCode;
  }
}

export function mapWireError(status: number, error: WireError): DecisionUiCode {
  const code = error.code.toUpperCase();

  if (
    status === 409 ||
    code.includes("CONFLICT") ||
    code.includes("IDEMPOTENCY") ||
    code.includes("DIGEST")
  ) {
    return "CONFLICT";
  }
  if (
    code.includes("STALE") ||
    code.includes("REVISION") ||
    code === "CASE_REVISION_MISMATCH"
  ) {
    return "STALE";
  }
  if (code.includes("EXPIRED") || code.includes("EXPIRY")) {
    return "EXPIRED";
  }
  if (
    code.includes("CROSS_TENANT") ||
    code.includes("TENANT") ||
    code.includes("OUT_OF_SCOPE") ||
    code.includes("SCOPE")
  ) {
    return "CROSS_TENANT";
  }
  if (
    status === 401 ||
    status === 403 ||
    status === 404 ||
    code.includes("UNAUTHORIZED") ||
    code.includes("FORBIDDEN")
  ) {
    return "UNAUTHORIZED";
  }
  if (status === 503 || code.includes("UNAVAILABLE") || code.includes("PEER")) {
    return "UNAVAILABLE";
  }
  if (status === 422 || code.includes("MALFORMED") || code.includes("INVALID")) {
    return "MALFORMED";
  }
  return "UNKNOWN";
}

export function accessibleMessage(uiCode: DecisionUiCode, message: string): string {
  switch (uiCode) {
    case "EXPIRED":
      return `Decision blocked: approval or evidence expired. ${message}`;
    case "STALE":
      return `Decision blocked: case or action revision is stale. Refresh and retry. ${message}`;
    case "UNAUTHORIZED":
      return `Decision blocked: reviewer is not authorized for this resource. ${message}`;
    case "CROSS_TENANT":
      return `Decision blocked: resource is outside the authenticated tenant or subject scope. ${message}`;
    case "CONFLICT":
      return `Decision blocked: conflicting digest, revision, or idempotency key (HTTP 409). ${message}`;
    case "UNAVAILABLE":
      return `Decision blocked: required peer unavailable. ${message}`;
    case "MALFORMED":
      return `Decision blocked: peer returned a malformed or invalid response. ${message}`;
    default:
      return `Decision blocked: ${message}`;
  }
}
