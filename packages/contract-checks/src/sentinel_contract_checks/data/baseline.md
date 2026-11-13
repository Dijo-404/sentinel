# Sentinel independent-task contract baseline

Version: `sentinel.task-contracts.v1`. Status: proposed planning input, not an implemented API.

This baseline is supplied with every task. SN-002 implements conformance tooling against it; SN-002 is not a prerequisite. Each task records this document's SHA-256 and includes relevant schema snapshots, synthetic examples, and local peer stubs in its owned directory. A snapshot may translate wire data into local types; it must preserve the baseline semantics. No agent needs another task's source package to implement these interfaces.

## Common conventions

- Money is an integer number of minor units. INR `150000` means ₹1,500. Currency is explicit; monetary floats are invalid.
- IDs are opaque strings. Examples use readable synthetic IDs. Do not infer authorization from ID format or model output.
- Timestamps are UTC RFC 3339 with `Z`. Required evidence includes observation and expiry timestamps. Reject expired evidence at authorization time.
- Tenant, customer, reviewer, and service identity come from authenticated server/peer context. A body field or prompt cannot establish identity. A local stub uses a clearly synthetic test principal.
- Every case/action/evidence operation verifies tenant and subject scope. Authenticated peer calls still require resource authorization.
- Errors use `{ "code": "...", "message": "...", "request_id": "..." }` with no secrets or raw provider payloads. Use 409 for conflicting keys/digests/revisions, 403/404 for unauthorized scope, 422 for invalid input, and 503 for unavailable required peers. Do not leak existence through differing unauthorized responses.
- HTTP services expose `/healthz`, `/readyz`, and a versioned `/v1` API. Local fixture readiness is explicitly labeled; real-peer readiness reports unavailable required peers. A `/v1/capabilities` response declares `contract_version`, `component`, and `mode: fixture|real-peers`.
- Stateful components own their schema, migrations, seed identities, and local database/container setup. No peer writes another component's tables.
- Requests/events carry `request_id`, `traceparent` where applicable, `case_id`, and the relevant stable `action_id`. Do not put customer/payment identifiers in metric labels.
- Baseline readers accept compatible optional fields. Unknown actions, statuses, and required-version mismatches fail explicitly. Financial payloads permit only the exact declared fields; never ignore an extra authorization-relevant field while hashing a different payload.

## Core records and states

### Case and evidence

Minimum case response fields: `case_id`, `revision` (positive integer), `status`, `language`, `intent`, `evidence_ids`, and `contract_version`. A client-supplied case request has only `message`, `language`, `order_reference`, and `channel`; identity comes from the authenticated session. Case creation uses `Idempotency-Key`, returns 202, and rejects a different payload under the same key.

Case states: `RECEIVED`, `NEEDS_INPUT`, `INVESTIGATING`, `RECONCILING`, `PLANNING`, `POLICY_CHECK`, `WAITING_APPROVAL`, `EXECUTING`, `VERIFYING`, `WAITING_EXTERNAL`, `ESCALATED`, `VERIFIED_RESOLVED`, `CLOSED_NO_ACTION`. Escalation is a handoff, not financial resolution.

Evidence fields: `evidence_id`, `case_id`, `source`, `subject_ref`, `observed_at`, `expires_at`, `digest`, `verification_status`, and a typed `facts` object. Server-side scope accompanies the record. `verification_status` is `VERIFIED`, `UNVERIFIED`, or `CONFLICTING`; a model/customer assertion never upgrades it. The digest is SHA-256 of the exact UTF-8 serialized payload supplied with the evidence snapshot; retain those bytes with the digest instead of reconstructing them from parsed JSON. Boundary schemas distinguish captured payment facts, order/merchant confirmation, refund status, and customer-credit evidence.

Baseline synthetic evidence bundle:

```json
{
  "contract_version": "sentinel.task-contracts.v1",
  "case_id": "case-demo-42",
  "order_reference": "DEMO-ORDER-42",
  "payments": [
    {"transaction_ref": "TXN-A", "status": "CAPTURED", "amount_minor": 150000, "currency": "INR"},
    {"transaction_ref": "TXN-B", "status": "CAPTURED", "amount_minor": 150000, "currency": "INR"}
  ],
  "fulfilled_order_count": 1,
  "merchant_confirmed_duplicate": true,
  "refunded_minor": 0,
  "pending_minor": 0,
  "reserved_minor": 0
}
```

This fixture is not itself proof of authority, freshness, payment duplication, or credit. Each task supplies authenticated synthetic principals and verified evidence envelopes, timestamps, and error variants around it. Two equal amounts alone never establish duplicate payment.

### Proposal, policy, and approval

The exact action payload is:

```json
{
  "action": "REQUEST_REFUND",
  "case_id": "case-demo-42",
  "case_revision": 1,
  "transaction_ref": "TXN-B",
  "amount_minor": 150000,
  "currency": "INR",
  "destination": "ORIGINAL_PAYMENT_ROUTE",
  "evidence_ids": ["evidence-payment-b", "evidence-order"],
  "policy_version": "demo-policy-v1"
}
```

`action` values are `STATUS_UPDATE`, `OPEN_DISPUTE`, `SCHEDULE_RECHECK`, `REQUEST_REFUND`, `SYNC_ORDER`, and `ESCALATE`. Refund payloads require every field above; other actions have their own explicit schema. Case revision is a positive integer, refund amount is a positive integer, and evidence IDs are a nonempty ordered list. Array order is significant for digest matching. Rationale is separate untrusted display text, not part of authority.

For this baseline, the action digest is SHA-256 of UTF-8 JSON with keys sorted lexicographically, no whitespace, no ASCII escaping, and no floats/NaN. Object keys are the declared ASCII names above. Preserve strings and array order exactly, without Unicode normalization. Reference serialization is Python `json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)`, after rejecting non-schema values. Snapshots must contain exact canonical bytes and expected digest fixtures so other languages can match them.

Policy returns `outcome: ALLOW|REQUIRE_APPROVAL|DENY|NEED_EVIDENCE`, `reason_codes`, `policy_version`, `action_digest`, and `required_evidence`. `ALLOW` from a model or unauthenticated peer grants no capability. The ledger repeats authoritative eligibility, approval, scope, and balance checks atomically before reservation.

An approval record binds `approval_id`, `action_digest`, `case_revision`, `policy_version`, `decision: APPROVE|REJECT`, authenticated `reviewer_id`, and `expires_at`. The ledger owns the authoritative record. The case API and UI forward an authenticated decision request; they do not synthesize approval authority. Stale revision, wrong digest, wrong tenant/role, or expiry prevents dispatch.

### Financial ledger and dispatch

One action-ledger component owns payment eligibility/reservations, authoritative approvals, immutable actions, stable provider references, dispatch leases, outbox, and financial audit. Reservation, action/outbox creation, and required audit entries commit in one local PostgreSQL transaction. Completed, pending, and reserved refunds together cannot exceed the eligible captured amount. No network request occurs while holding that transaction open. Source evidence needed for eligibility is authenticated, scoped, and freshness-checked before being accepted into the local eligibility snapshot; the transaction rejects superseded/expired snapshots and known external refund conflicts.

Reservation inputs include `operation_key`, `payload`, `action_digest`, and `approval_id`, with identity supplied by server context. Same key and identical payload reuse the action; different payload returns 409. The ledger generates `action_id` and `provider_ref` once. All later attempts use those references.

The dispatcher claims an existing authorized outbox command using an authenticated ledger port. A command includes `action_id`, `provider_ref`, immutable `payload`, `action_digest`, `lease_id`, `lease_expires_at`, and the provider's permitted retry/status-lookup capabilities. A typed command body alone is not a bearer capability: real-peer mode requires an authenticated ledger connection and scope checks. Claim replay cannot mint a new logical operation.

After timeout/crash, lookup uses the original provider reference. A lease expiring does not prove a financial operation failed. Unknown outcomes preserve the reservation. Providers lacking safe duplicate-key retry/status lookup require escalation rather than resubmission. No consumer bypasses the ledger through direct table writes.

Action states: `PROPOSED`, `RESERVED`, `DISPATCHING`, `OUTCOME_UNKNOWN`, `PENDING`, `PROVIDER_CONFIRMED`, `CREDIT_CONFIRMED`, `FAILED_FINAL`, `ESCALATED`. Verified outcomes and transitions require provenance. An HTTP 200 or accepted provider request does not establish final refund or credit.

### Events and verification

Provider event handling verifies a provider-specific signature over original bytes, mapping to tenant/merchant, deduplication key, and replay policy. Persist the inbox before acknowledging receipt. Duplicate/out-of-order events trigger reconciliation of current provider status and cannot regress state or create another refund.

The verifier owns inbox/recheck state and sends authenticated evidence to ledger transition ports. Only the ledger changes authoritative action state and balances. Scheduled work has stable `job_id`, case/action scope, `available_at`, lease, and bounded attempts. Transient failure preserves durable work.

Case events have `event_id`, increasing per-case `sequence`, `case_id`, `case_revision`, `type`, `occurred_at`, and a redacted `payload`. SSE `id` is the sequence cursor; reconnect resumes after the supplied cursor without losing persisted events. Consumers handle duplicates idempotently. Financial events are authenticated facts, not client-provided instructions.

`VERIFIED_RESOLVED` requires the scenario's explicit postconditions. The duplicate-payment hero fixture requires provider outcome and separate synthetic credit evidence. Missing credit leaves the case waiting even after provider confirmation. Fraud/escalation never counts as verified financial resolution.

## Boundary catalogue

These are required baseline ports, not installed endpoints. Stateful/service implementations expose them through authenticated HTTP; libraries and test doubles may implement the same typed port in process. Each issue includes the subset it consumes/produces plus local request/response fixtures. Additive details may be task-local, while the semantics above remain fixed.

| Port | Owning task/root | Input and output |
| --- | --- | --- |
| `module-checks.v1` | SN-001 `tooling/workspace/` | Discover declared modules already present; run module-local checks; report absent modules separately. No global dependency install required. |
| `contract-checks.v1` | SN-002 `packages/contract-checks/` | Validate baseline fixtures, canonical digest bytes, and compatibility; emit structured violations. |
| `persistence-kit.v1` | SN-003 `packages/persistence/` | Tenant-aware migration/seed/check helpers against its own test database. Optional library; no shared authoritative financial tables. |
| `payment-provider.v1` | SN-004 `services/simulator/` | Scoped transaction/order/refund reads, refund request by stable reference, status lookup, synthetic credit evidence, deterministic fault control. |
| `policy.v1` | SN-005 `services/policy/` | Proposal plus scoped evidence/approval facts; deterministic outcome, reasons, obligations, policy version, digest. |
| `evidence.v1` | SN-006 `services/evidence/` | Scoped case/order/transaction lookup; verified normalized snapshots and deterministic reconciliation results. |
| `case-api.v1` | SN-007 `apps/api/` | Phase 1 `/v1/cases`, case messages/events, `/v1/ops/cases`, evidence, decisions, and escalation routes. Local ports cover storage, workflow, ledger, and evidence peers. |
| `workflow.v1` | SN-008 `services/workflow/` | Start/resume/recheck a scoped case revision; checkpoint, explicit case status, and requested next action. Owns its baseline fake/configurable structured-model adapter; Phase 2 context is not required. |
| `action-ledger.v1` | SN-009 `services/action-ledger/` | Authenticated decisions, reservation, authorized command claim, action/status lookup, and evidence-bound outcome transitions. Owns authoritative approval/financial state. |
| `dispatcher.v1` | SN-010 `services/dispatcher/` | Claim authorized command, submit through provider adapter, record accepted/unknown outcome; reconcile stable reference. |
| `verifier.v1` | SN-011 `services/verifier/` | Signed original webhook bytes or scheduled scoped recheck; durable inbox, fresh outcome evidence, ledger transition request, closure assessment. |
| `web-shell.v1` | SN-012 `apps/web/` | Authenticated case client plus component slots; customer/operator pages with fixture and real-peer adapters. |
| `approval-ui.v1` | SN-013 `packages/approval-ui/` | Validated action/evidence/decision view models and injected authorized API client; accessible component/standalone preview, refresh/conflict events. |
| `core-assembly.v1` | SN-014 `integration/core/` | Endpoint/version/mode configuration and four journey scenarios; explicit component compatibility/failure report. |
| `telemetry.v1` | SN-015 `packages/telemetry/` | Sanitized event/span/metric hooks and redaction; correlated export and local example dashboards. Financial audit remains separate. |
| `evaluation.v1` | SN-016 `evals/core/` | Versioned fixture set plus injected runner/HTTP adapter; deterministic safety/outcome report and holdout metadata. |
| `voice.v1` | SN-017 `services/voice/` | Consented synthetic audio/text with language; source-preserving transcript or bounded failure; optional speech output, no financial authority. |
| `replay.v1` | SN-018 `replay/core/` | Fixture events, virtual clock, candidate runner port; deterministic state/effect differences and promotion recommendation. |
| `release-evidence.v1` | SN-019 `release/mvp/` | Evidence manifest containing component commit, contract hash, check command/result, artifact digest, observed mode, and timestamp; missing/invalid/fixture-only release proof fails. |
| `finharness-sdk.v1` | SN-020 `packages/finharness-sdk/` | Injectable evidence/policy/ledger/verification/model ports and version-pinned configuration; no independent refund executor or case store. |
| `indic-context.v1` | SN-021 `packages/indic-context/` | Original text/language, scoped evidence, provider config; validated proposal or ambiguity/error with provenance preserved. |
| `finharness-runtime.v1` | SN-022 `services/finharness-runtime/` | Pinned case manifest, injected SDK-compatible ports, read-only shadow or explicitly enabled sandbox mode; outcome/proposal comparison without shadow writes/notifications. |
| `finbench.v1` | SN-023 `benchmarks/finbench_indic/` | Hashed grouped dataset split and injected candidate runner; separate model/system scores with denominators, variance, and hard safety result. |
| `harness-telemetry.v1` | SN-024 `packages/finharness-telemetry/` | Injected sanitized runtime/evaluation/audit correlation records; bounded metrics and versioned export/dashboard examples. |
| `harness-replay.v1` | SN-025 `replay/finharness/` | Pinned context/runtime runner and synthetic fault schedule; state/effect comparison and mandatory safety promotion gate. |
| `sandbox-validation.v1` | SN-026 `validation/sandbox-pilot/` | Configured component endpoints and evidence; load/restart/restore/rollback/second-workflow test plan and measured report. Actual external pilot execution requires separate authorization. |
| `merchant-settlement.v1` | SN-027 `services/merchant-settlement/` | Import synthetic settlement batches; match payments/orders; emit discrepancy findings (missing, duplicate, fee_diff, short_settle). Read-only vs payment/evidence peers; no provider writes. |
| `merchant-inbox.v1` | SN-028 `services/merchant-inbox/` | Merchant exception queue: paid-unfulfilled, unmatched payment, pending refund; filter, assign, note, escalate. Escalation is not resolution. |
| `merchant-refunds.v1` | SN-029 `services/merchant-refunds/` | Merchant-staff refund requests with evidence attachments; propose via policy/ledger ports only. No second executor; SN-009 remains sole financial authority. |
| `merchant-disputes.v1` | SN-030 `services/merchant-disputes/` | Dispute case lifecycle, evidence packet assembly, deadline tracking; no ledger table edits. |
| `merchant-sla.v1` | SN-031 `services/merchant-sla/` | Response/resolution targets, assignment, overdue highlighting, follow-up scheduling; escalation distinct from verified closure. |
| `merchant-analytics.v1` | SN-032 `services/merchant-analytics/` | Merchant-scoped aggregate metrics: exception rates, unresolved amounts, refund aging, handling time, recurring causes. Read-only. |
| `merchant-comms.v1` | SN-033 `packages/merchant-comms/` | English/Tamil/Hindi status draft generation with operator approval gate and simulated delivery history; no financial authority. |
| `merchant-teams.v1` | SN-034 `services/merchant-teams/` | Merchant-scoped staff accounts, roles, advisory approval limits, activity timeline. Limits never bypass ledger/policy authorization. |

## Required standalone proof

Every task includes fixtures implementing consumed ports; no fixture imports an unfinished peer package. Its `make -C <owned-root> check` installs/uses only declared local dependencies and exercises component acceptance with no other Sentinel task running. Database tests use the component's own PostgreSQL setup when transaction behavior matters; an in-memory fake cannot prove reservation concurrency.

External model/voice API credentials are optional for the local check. Fake inference is clearly labeled and live model tests remain opt-in. A real-peer adapter must reject absent, unauthorized, malformed, or incompatible peers. Integration/release/pilot tools test this failure behavior using negative fixtures so the tool itself can finish before real services exist.

Before accepting a product release, use the real independently built components with synthetic payment providers. Report `component-under-test: real` separately from `payment-provider: simulator` and `model: fake|live`. Stub peers cannot satisfy assembled release evidence. Record external pilot/provider observations separately; no fixture is evidence of real financial settlement.

## Exact baseline wire types

The notation below specifies JSON values: `?` marks an optional property; `T[]` is an array; `int` is an integer. All other properties are required. Enums and semantic constraints from the sections above apply. Object types reject undeclared properties except the explicitly extensible `attributes` map. Path parameters are not repeated in request bodies. Optional properties are omitted, not `null`. Library ports use the same request/response values in process. A module includes serialized fixtures for the subset it consumes and produces.

```text
Version = "sentinel.task-contracts.v1"
Scope = { case_id: string, case_revision: int }
Principal = { principal_id: string, tenant_id: string,
              roles: string[], subject_refs: string[], case_ids: string[] }
Error = { code: string, message: string, request_id: string }
Ack = { contract_version: Version, job_id: string, accepted: true }
Capabilities = { contract_version: Version, component: string,
                 mode: "fixture" | "real-peers" }

Case = { contract_version: Version, case_id: string, revision: int,
         status: CaseState, language: string, intent: string,
         evidence_ids: string[], action_id?: string }
CaseCreate = { message: string, language: string,
               order_reference: string, channel: "web" | "voice" }
CaseCreated = { case_id: string, status: "RECEIVED", status_url: string }
CaseMessage = { message_id: string, text: string, language: string,
                author: "CUSTOMER" | "OPERATOR", occurred_at: string }
CaseInput = { case_id: string, case_revision: int, original_text: string,
              language: string, order_reference: string, messages: CaseMessage[] }
CaseEvent = { event_id: string, sequence: int, case_id: string,
              case_revision: int, type: string, occurred_at: string,
              payload: { status: CaseState, evidence_ids: string[],
                         action_id?: string, reason_code: string } }
CaseResult = { event_key: string, expected_revision: int,
               status: CaseState, evidence_ids: string[],
               action_id?: string, assessment_id?: string, reason_code: string }

Payment = { transaction_ref: string, order_reference: string,
            subject_ref: string, status: "CAPTURED" | "PENDING" | "FAILED",
            amount_minor: int, currency: "INR" }
Order = { order_reference: string, subject_ref: string,
          fulfilled_order_count: int, merchant_confirmed_duplicate: bool,
          paid: bool }
RefundRequest = { action_id: string, provider_ref: string,
                  transaction_ref: string, amount_minor: int,
                  currency: "INR", destination: "ORIGINAL_PAYMENT_ROUTE" }
Refund = { action_id: string, provider_ref: string, transaction_ref: string,
           amount_minor: int, currency: "INR",
           status: "PENDING" | "PROVIDER_CONFIRMED" | "FAILED_FINAL" }
Credit = { provider_ref: string, confirmed: bool, observed_at: string }
PaymentFacts = { kind: "PAYMENT", payment: Payment }
OrderFacts = { kind: "ORDER", order: Order }
RefundFacts = { kind: "REFUND", refund: Refund }
CreditFacts = { kind: "CREDIT", credit: Credit }
Evidence = { evidence_id: string, case_id: string, source: string,
             subject_ref: string, observed_at: string, expires_at: string,
             digest: string, verification_status: "VERIFIED" | "UNVERIFIED" | "CONFLICTING",
             facts: PaymentFacts | OrderFacts | RefundFacts | CreditFacts }
EvidenceBundle = { contract_version: Version, case_id: string,
                   evidence: Evidence[], reconciliation_codes: string[] }

ActionBase = { case_id: string, case_revision: int,
               evidence_ids: string[], policy_version: string }
RefundAction = ActionBase & { action: "REQUEST_REFUND", transaction_ref: string,
                 amount_minor: int, currency: "INR", destination: "ORIGINAL_PAYMENT_ROUTE" }
StatusAction = ActionBase & { action: "STATUS_UPDATE",
                 message_code: "WAITING" | "NEEDS_INPUT" | "ESCALATED" | "VERIFIED" }
DisputeAction = ActionBase & { action: "OPEN_DISPUTE", transaction_ref: string,
                              reason_code: string }
RecheckAction = ActionBase & { action: "SCHEDULE_RECHECK", available_at: string,
                              reason_code: string }
SyncAction = ActionBase & { action: "SYNC_ORDER", transaction_ref: string,
                           order_reference: string }
EscalateAction = ActionBase & { action: "ESCALATE", reason_code: string,
                               owner_queue: "PAYMENTS" | "FRAUD" | "SUPERVISOR" }
Action = RefundAction | StatusAction | DisputeAction | RecheckAction | SyncAction | EscalateAction
Approval = { approval_id: string, action_digest: string, case_revision: int,
             policy_version: string, decision: "APPROVE" | "REJECT",
             reviewer_id: string, expires_at: string }
DecisionRequest = { decision: "APPROVE" | "REJECT", action_digest: string,
                    case_revision: int, policy_version: string, expires_at: string }
PolicyRequest = { payload: Action, evidence: Evidence[], approval?: Approval }
PolicyResult = { outcome: "ALLOW" | "REQUIRE_APPROVAL" | "DENY" | "NEED_EVIDENCE",
                 reason_codes: string[], policy_version: string,
                 action_digest: string, required_evidence: string[] }

ReservationRequest = { operation_key: string, payload: RefundAction,
                        action_digest: string, approval_id: string }
ActionRecord = { action_id: string, provider_ref: string, payload: RefundAction,
                 action_digest: string, status: ActionState,
                 approval?: Approval }
ProposalRequest = { operation_key: string, payload: RefundAction, action_digest: string }
Command = { action_id: string, provider_ref: string, payload: RefundAction,
            action_digest: string, lease_id: string, lease_expires_at: string,
            provider_capabilities: { same_key_retry: bool, status_lookup: bool } }
ClaimResult = { commands: Command[] }
OutcomeRequest = { event_key: string, lease_id?: string, status: ActionState,
                   evidence: Evidence[], reason_code: string }

WorkflowRequest = { case_id: string, case_revision: int, job_key: string,
                    event: "START" | "INPUT" | "DECISION" | "RECHECK" }
ModelRequest = { case: Case, input: CaseInput, evidence: Evidence[] }
ModelResult = { outcome: "PROPOSAL" | "NEEDS_INPUT" | "ESCALATE",
                proposal?: Action, reason_codes: string[],
                original_text: string, language: string }
VerificationRequest = { case_id: string, case_revision: int,
                         action_id: string, provider_ref: string }
VerificationResult = { assessment_id: string, case_id: string, case_revision: int,
                        action_id: string, assessed_at: string, expires_at: string,
                        status: "WAITING" | "VERIFIED" | "CONFLICT" | "ESCALATED",
                        evidence: Evidence[], reason_codes: string[] }
```

`CaseState` and `ActionState` mean the exact enumerations above. `ActionBase & {...}` is a merged object, not a nested `base` property. The ledger creates immutable unreserved proposals through its proposal endpoint so supervisors can approve a specific `action_id` before reservation. Proposal creation grants no dispatch rights. Reservation must match that proposal's operation key, digest, case revision, tenant, and approval. All refunds require approval. Non-refund actions route through case/workflow services, not the financial dispatcher; unsupported actions return 422 rather than becoming refund commands. `ModelResult.proposal` is required exactly when outcome is `PROPOSAL`.

## Exact service routes and authentication

Every protected endpoint requires an opaque bearer token in `Authorization`. For synthetic local/assembled demos, each service resolves configured test tokens to the exact `Principal` type above; this configuration is local to that task. The same reviewed token map is supplied to real components by assembly configuration. No separate identity-service task is needed. Incoming identity/role headers and model-supplied principals are never trusted. Future verified issuers may replace token lookup while preserving these principal semantics. These are synthetic demo credentials, never production credentials.

Roles are `customer`, `operator`, `supervisor`, `workflow`, `dispatcher`, `verifier`, and `sandbox-admin`. Customer principals may access only their configured subject/case scope; operator/supervisor principals remain tenant-scoped. Service principals require exact allowed tenant/case/subject scope. Role membership alone never authorizes a resource. Decision proxies forward the original authenticated supervisor token; they cannot convert an operator/customer into a supervisor. No service receives implicit cross-tenant access.

For each route, the response is JSON unless stated. Successful reads/decisions return 200; creation is explicitly listed. Empty-body operations accept no undeclared request body. Common error codes/statuses follow the baseline above. Resource-level idempotency applies in addition to HTTP request correlation.

| Port / method / route | Request | Response | Role requirement |
| --- | --- | --- | --- |
| provider `GET /v1/transactions?order_reference=...` | Scoped query | `{ payments: Payment[] }` | workflow, verifier, sandbox-admin |
| provider `GET /v1/orders/{order_reference}` | Empty | `Order` | workflow, verifier, sandbox-admin |
| provider `GET /v1/refunds?transaction_ref=...` | Scoped query | `{ refunds: Refund[] }` | workflow, verifier, sandbox-admin |
| provider `POST /v1/refunds` | `RefundRequest`; `Idempotency-Key` equals provider_ref | `Refund`, 202 | dispatcher |
| provider `GET /v1/refunds/{provider_ref}` | Empty | `Refund`; 404 is not proof an ambiguous write failed | dispatcher, verifier, workflow |
| provider `GET /v1/credits/{provider_ref}` | Empty | `Credit` | verifier, workflow |
| policy `POST /v1/evaluate` | `PolicyRequest` | `PolicyResult` | workflow; ledger uses a workflow-scoped service principal |
| evidence `POST /v1/evidence/collect` | `{ case_id, case_revision, order_reference }` | `EvidenceBundle` | workflow, verifier |
| evidence `GET /v1/cases/{case_id}/evidence` | Empty | `EvidenceBundle` | workflow, verifier, operator, supervisor |
| cases `POST /v1/cases` | `CaseCreate`; required `Idempotency-Key` | `CaseCreated`, 202 | customer, operator |
| cases `GET /v1/cases/{case_id}` | Empty | `Case` | scoped customer, operator, supervisor, workflow, verifier |
| cases `POST /v1/cases/{case_id}/messages` | `{ message: string, language: string, expected_revision: int }` | `Case`, 202 | scoped customer, operator |
| cases `GET /v1/cases/{case_id}/events` | `Last-Event-ID` sequence cursor or `after` query | SSE `CaseEvent`; `format=json` returns `{ events: CaseEvent[] }` | scoped customer, operator, supervisor |
| cases `GET /v1/ops/cases?status=...&after=...` | Optional status/cursor | `{ cases: Case[], next_cursor?: string }` | operator, supervisor |
| cases `GET /v1/ops/cases/{case_id}/evidence` | Empty | `EvidenceBundle` | operator, supervisor |
| cases `POST /v1/ops/actions/{action_id}/decisions` | `DecisionRequest` | `Approval` from the ledger | supervisor |
| cases `POST /v1/ops/cases/{case_id}/escalate` | `{ expected_revision: int, reason_code: string, owner_queue: string }` | `Case` | operator, supervisor |
| cases `GET /v1/internal/cases/{case_id}/input?revision=...` | Required positive revision query | `CaseInput` for that immutable revision | workflow |
| cases `POST /v1/internal/cases/{case_id}/results` | `CaseResult` | `Case` | workflow, verifier |
| workflow `POST /v1/runs` | `WorkflowRequest` | `Ack`, 202 | workflow-scoped case API service principal, verifier |
| ledger `POST /v1/actions/proposals` | `ProposalRequest` | `ActionRecord`, 201 | workflow |
| ledger `POST /v1/actions/{action_id}/decisions` | `DecisionRequest` | `Approval` | supervisor |
| ledger `POST /v1/actions/reservations` | `ReservationRequest` | `ActionRecord`, 201 or 200 on identical retry | workflow |
| ledger `POST /v1/actions/claims` | `{ limit: int }`, 1 to 100 | `ClaimResult`; empty commands means no work | dispatcher |
| ledger `GET /v1/actions/{action_id}` | Empty | `ActionRecord` | workflow, dispatcher, verifier, operator, supervisor |
| ledger `POST /v1/actions/{action_id}/outcomes` | `OutcomeRequest` | `ActionRecord` | dispatcher for accepted/unknown; verifier for evidence-confirmed transitions |
| verifier `POST /v1/rechecks` | `VerificationRequest`; required `Idempotency-Key` | `Ack`, 202 | workflow, verifier |
| verifier `POST /v1/webhooks/simulator` | Original provider event bytes | `{ accepted: true }`, 202 after inbox commit | Provider signature; tenant resolved from authenticated signed payload |
| verifier `POST /v1/assessments` | `VerificationRequest` | `VerificationResult` | workflow |
| verifier `GET /v1/assessments/{assessment_id}` | Empty | `VerificationResult` | workflow-scoped case API service principal, verifier |
| context `POST /v1/proposals` | `ModelRequest` | `ModelResult` | workflow |

SN-008 owns a baseline structured-model adapter implementing `ModelRequest`/`ModelResult` inside its own root, including fake inference and a configurable real provider adapter. SN-021's optional `indic-context.v1` adapter may implement the same values later. MVP assembly must not require SN-021. Similarly the web shell must run with voice disabled; optional voice does not become a release prerequisite through a component slot.

## Result propagation and idempotent transitions

Case API owns the original complaint, ordered message history, order reference, language, and immutable input snapshots for each case revision. The authenticated case-input route supplies `CaseInput` to the workflow without cross-database reads; `original_text` is the original complaint, and `messages` includes it plus subsequent customer/operator inputs through that revision. Unknown revisions fail explicitly. Model input uses this full snapshot; order-reference hints remain untrusted until scoped evidence verifies them.

Case API owns case status/events; workflow/verifier submit `CaseResult` through the internal results route. They do not edit case tables. `event_key` is unique per tenant/case; an identical retry returns the original accepted case snapshot, while the same key with different payload returns 409. A new result requires the current `expected_revision`, atomically advances revision, and appends the matching durable event. A stale new result returns 409; workers read current case state and reconcile their outcome before retrying. Never blindly overwrite a newer case state. External ledger actions retain their stable action ID when a case revision advances; the command's original approval revision/digest remains immutable.

Workers persist pending result delivery in their own durable state/outbox. A case API outage delays result notification; it does not repeat a financial operation or release a reservation. Customer-message/decision handling durably schedules a workflow event instead of relying on a successful synchronous worker call. Repeated `job_key` values with identical payload are idempotent; differing payload returns 409.

The verifier submits authenticated evidence to the ledger before announcing a corresponding financial case result. Verified case resolution requires the case API to confirm the evidence/closure assessment through its trusted verifier port; a `status: VERIFIED_RESOLVED` body alone cannot close the case. A resolved `CaseResult` requires `assessment_id`; the case API reads that assessment from the authenticated verifier, checks matching case/action/revision, fresh verified evidence, and the scenario predicate, then persists the accepted assessment reference with its event. No model can call these service-authorized ports directly.

Ledger proposals start in `PROPOSED` with no reservation or outbox command. Approval/rejection does not reserve funds. Reservation moves an approved matching proposal to `RESERVED`. Claim moves `RESERVED` to `DISPATCHING`. Dispatcher outcomes may move it to `PENDING` or `OUTCOME_UNKNOWN`; verified provider evidence may move it to `PROVIDER_CONFIRMED` or `FAILED_FINAL`. `CREDIT_CONFIRMED` requires separate credit evidence after provider confirmation. Unknown/pending states may escalate while retaining monetary allocations; authoritative reconciliation can complete an escalated action. Duplicate evidence is a no-op. Invalid/regressive transitions return 409. Only authoritative final-failure evidence permits release; no reservation is released merely because a lease expired or a lookup returned 404. Include these transitions and failure cases in each consumed ledger fixture.

The synthetic provider webhook body is `{ event_id: string, tenant_id: string, merchant_ref: string, provider_ref: string, type: "REFUND_STATUS" | "CREDIT_STATUS", occurred_at: string }`. `X-Sentinel-Signature` is lowercase hex HMAC-SHA256 of the original bytes under a local provider key; `event_id` deduplicates by provider/tenant. Verify signature, merchant mapping, age policy, and provider status by stable reference; the claimed event type alone cannot establish an outcome. Fixed virtual-clock fixtures may disable wall-clock age checking only in explicitly labeled test mode.

## Matching request/response examples

Each task must instantiate the exact types above with its own synthetic auth context. These minimal operation pairs fix identifiers and state meanings across independently built peers:

```json
{
  "case_result_request": {"event_key":"result-demo-1","expected_revision":1,"status":"WAITING_APPROVAL","evidence_ids":["evidence-payment-b","evidence-order"],"action_id":"action-demo-1","reason_code":"SUPERVISOR_REQUIRED"},
  "case_result_response": {"contract_version":"sentinel.task-contracts.v1","case_id":"case-demo-42","revision":2,"status":"WAITING_APPROVAL","language":"en-IN","intent":"DUPLICATE_PAYMENT","evidence_ids":["evidence-payment-b","evidence-order"],"action_id":"action-demo-1"},
  "claim_request": {"limit":1},
  "claim_empty_response": {"commands":[]},
  "workflow_request": {"case_id":"case-demo-42","case_revision":2,"job_key":"resume-demo-1","event":"DECISION"},
  "workflow_response": {"contract_version":"sentinel.task-contracts.v1","job_id":"job-demo-1","accepted":true},
  "conflicting_retry_response": {"code":"IDEMPOTENCY_CONFLICT","message":"Key already used with a different payload","request_id":"request-demo-1"},
  "missing_peer_response": {"code":"PEER_UNAVAILABLE","message":"Required peer unavailable","request_id":"request-demo-2"}
}
```

For telemetry, evaluation, replay, SDK, assembly, and release tools, the boundary is an injected library/CLI port, not a mandatory HTTP service. Each accepts `RunInput = { contract_version: Version, run_id: string, mode: "fixture" | "real-peers", input_artifacts: ArtifactRef[], parameters: { [key: string]: string|int|bool } }` and returns `RunReport = { contract_version: Version, run_id: string, mode: "fixture" | "real-peers", status: "PASS" | "FAIL" | "UNVERIFIED", checks: CheckResult[], output_artifacts: ArtifactRef[] }`. `ArtifactRef = { kind: string, uri: string, sha256: string, component_version: string, evidence_mode: "fixture" | "real-component" | "live-provider" }`; `CheckResult = { name: string, status: "PASS" | "FAIL" | "UNVERIFIED", reason_code: string }`. Module-specific parameters are additive namespaced options; unsupported required options fail. The `check` entry point uses only local inputs and returns exit 0 on successful self-tests; a separate real-peer run exits nonzero on FAIL or UNVERIFIED. Artifact schemas inside each package declare the port-specific records already listed above; consumers use injected adapters instead of importing those packages.

The approval UI accepts `{ case: Case, action: ActionRecord, evidence: Evidence[] }` plus an injected `decide(action_id, DecisionRequest) -> Approval` client and renders refresh/conflict events. It owns a preview without the web shell. Voice accepts `{ language: string, audio_uri?: string, text?: string, consent: bool }` with exactly one audio/text input and returns `{ original_text: string, language: string, ambiguous: bool, reason_codes: string[] }`; raw audio is not a metric label or financial capability. Its standalone provider fixture and typed client are sufficient for development with no web-shell task.

## Canonical digest and financial operation fixture

Use a virtual clock and separately configured synthetic scoped principals to exercise this example. The approval record must already exist and match the proposal before reservation; these request bodies alone do not confer authority. Provider status remains pending until independent outcome/credit evidence arrives.

```json
{
  "canonical_action_utf8": "{\"action\":\"REQUEST_REFUND\",\"amount_minor\":150000,\"case_id\":\"case-demo-42\",\"case_revision\":1,\"currency\":\"INR\",\"destination\":\"ORIGINAL_PAYMENT_ROUTE\",\"evidence_ids\":[\"evidence-payment-b\",\"evidence-order\"],\"policy_version\":\"demo-policy-v1\",\"transaction_ref\":\"TXN-B\"}",
  "expected_sha256": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
  "reservation_request": {
    "operation_key": "duplicate-demo-42-b",
    "payload": {
      "action": "REQUEST_REFUND",
      "case_id": "case-demo-42",
      "case_revision": 1,
      "transaction_ref": "TXN-B",
      "amount_minor": 150000,
      "currency": "INR",
      "destination": "ORIGINAL_PAYMENT_ROUTE",
      "evidence_ids": [
        "evidence-payment-b",
        "evidence-order"
      ],
      "policy_version": "demo-policy-v1"
    },
    "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
    "approval_id": "approval-demo-1"
  },
  "claim_one_response": {
    "commands": [
      {
        "action_id": "action-demo-1",
        "provider_ref": "refund-demo-1",
        "payload": {
          "action": "REQUEST_REFUND",
          "case_id": "case-demo-42",
          "case_revision": 1,
          "transaction_ref": "TXN-B",
          "amount_minor": 150000,
          "currency": "INR",
          "destination": "ORIGINAL_PAYMENT_ROUTE",
          "evidence_ids": [
            "evidence-payment-b",
            "evidence-order"
          ],
          "policy_version": "demo-policy-v1"
        },
        "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
        "lease_id": "lease-demo-1",
        "lease_expires_at": "2026-11-13T12:05:00Z",
        "provider_capabilities": {
          "same_key_retry": true,
          "status_lookup": true
        }
      }
    ]
  },
  "provider_refund_request": {
    "action_id": "action-demo-1",
    "provider_ref": "refund-demo-1",
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "destination": "ORIGINAL_PAYMENT_ROUTE"
  },
  "provider_refund_response": {
    "action_id": "action-demo-1",
    "provider_ref": "refund-demo-1",
    "transaction_ref": "TXN-B",
    "amount_minor": 150000,
    "currency": "INR",
    "status": "PENDING"
  },
  "ambiguous_lookup_response": {
    "code": "NOT_FOUND",
    "message": "Reference not currently visible; outcome remains unknown",
    "request_id": "request-demo-3"
  }
}
```

## Merchant operations ports (synthetic / simulator-backed)

These ports support merchant operations consoles against synthetic settlement and case data. They never move real money, store production credentials, or write SN-009 ledger tables. Refund proposals call `action-ledger.v1` / `policy.v1` through authenticated adapters; advisory merchant approval limits cannot authorize financial actions.

```text
SettlementBatch = { batch_id: string, tenant_id: string, merchant_ref: string,
                    period_start: string, period_end: string, currency: string,
                    rows: SettlementRow[], source_digest: string }
SettlementRow = { row_id: string, transaction_ref: string, order_ref?: string,
                  settled_minor: int, fee_minor: int, occurred_at: string }
SettlementFinding = { finding_id: string, batch_id: string, kind:
                      "MISSING_PAYMENT" | "MISSING_SETTLEMENT" | "DUPLICATE_ROW" |
                      "FEE_DIFF" | "SHORT_SETTLE" | "UNMATCHED_ORDER",
                      transaction_ref?: string, expected_minor?: int,
                      observed_minor?: int, evidence_ids: string[], status:
                      "OPEN" | "ASSIGNED" | "ESCALATED" | "CLOSED" }
ExceptionItem = { item_id: string, tenant_id: string, merchant_ref: string,
                  kind: "PAID_UNFULFILLED" | "UNMATCHED_PAYMENT" | "PENDING_REFUND",
                  case_id?: string, transaction_ref?: string, amount_minor: int,
                  currency: string, assignee?: string, notes: string[],
                  status: "OPEN" | "ASSIGNED" | "ESCALATED" | "CLOSED" }
MerchantRefundRequest = { request_id: string, tenant_id: string, merchant_ref: string,
                          case_id: string, transaction_ref: string, amount_minor: int,
                          currency: string, evidence_ids: string[], rationale: string,
                          status: "DRAFT" | "SUBMITTED" | "AWAITING_APPROVAL" |
                          "RESERVED" | "REJECTED" | "VERIFIED" | "FAILED",
                          action_id?: string, approval_id?: string }
DisputeCase = { dispute_id: string, tenant_id: string, merchant_ref: string,
                case_id: string, reason_code: string, deadline_at: string,
                evidence_packet_ids: string[], status:
                "OPEN" | "EVIDENCE_PENDING" | "SUBMITTED" | "WON" | "LOST" | "WITHDRAWN" }
SlaPolicy = { policy_id: string, tenant_id: string, merchant_ref: string,
              respond_within_seconds: int, resolve_within_seconds: int }
SlaTask = { task_id: string, case_id: string, assignee?: string,
            due_at: string, follow_up_at?: string, overdue: bool,
            status: "OPEN" | "IN_PROGRESS" | "ESCALATED" | "DONE" }
MerchantMetrics = { tenant_id: string, merchant_ref: string, window_start: string,
                    window_end: string, exception_rate: string, unresolved_minor: int,
                    currency: string, refund_aging_buckets: { [bucket: string]: int },
                    median_handling_seconds: int, top_causes: string[] }
CommsDraft = { draft_id: string, case_id: string, language: "en" | "ta" | "hi",
               body: string, status: "DRAFT" | "APPROVED" | "SIMULATED_SENT" | "REJECTED",
               delivery_history: { at: string, channel: string, status: string }[] }
MerchantStaff = { staff_id: string, tenant_id: string, merchant_ref: string,
                  display_name: string, roles: string[],
                  approval_limit_minor?: int, currency?: string, active: bool }
StaffActivity = { event_id: string, staff_id: string, at: string,
                  kind: string, subject_ref: string, summary: string }
```

HTTP/library ports accept authenticated merchant-scoped principals. Money fields remain integer minor units. Missing/unauthorized/malformed peers fail closed. Fixture mode is labeled; real-peer mode never falls back to fixtures.

