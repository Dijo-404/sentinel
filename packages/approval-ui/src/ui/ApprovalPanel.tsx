import { useMemo, useState } from "react";
import type { DecideClient } from "../application/ports.js";
import { submitDecision } from "../application/submit-decision.js";
import { accessibleMessage } from "../domain/errors.js";
import { buildApprovalViewModel, ViewModelError } from "../domain/view-model.js";
import type {
  Approval,
  ApprovalUiInput,
  ConflictEvent,
  Decision,
  RefreshEvent,
} from "../domain/types.js";
import { formatAgeSeconds, formatMinorUnits } from "./format.js";

export type ApprovalPanelProps = ApprovalUiInput & {
  decide: DecideClient;
  reviewerId: string;
  decisionExpiresAt: string;
  now?: () => Date;
  onRefresh?: (event: RefreshEvent) => void;
  onConflict?: (event: ConflictEvent) => void;
  onDecided?: (approval: Approval) => void;
};

export function ApprovalPanel(props: ApprovalPanelProps) {
  const [busy, setBusy] = useState(false);
  const [alert, setAlert] = useState<string | null>(null);
  const [approval, setApproval] = useState<Approval | null>(null);

  const readNow = (): Date => (props.now ? props.now() : new Date());

  const modelResult = useMemo(() => {
    try {
      return {
        ok: true as const,
        view: buildApprovalViewModel(
          {
            case: props.case,
            action: props.action,
            evidence: props.evidence,
          },
          props.reviewerId,
          props.decisionExpiresAt,
          readNow(),
        ),
      };
    } catch (error) {
      return {
        ok: false as const,
        message: error instanceof ViewModelError ? error.message : "Invalid approval input",
      };
    }
  }, [
    props.case,
    props.action,
    props.evidence,
    props.reviewerId,
    props.decisionExpiresAt,
    props.now,
  ]);

  if (!modelResult.ok) {
    return (
      <section className="sentinel-approval" aria-labelledby="approval-title">
        <h2 id="approval-title">Approval required</h2>
        <p role="alert">{modelResult.message}</p>
      </section>
    );
  }

  const view = modelResult.view;

  async function onDecide(decision: Decision) {
    setBusy(true);
    setAlert(null);
    const deps: Parameters<typeof submitDecision>[0] = {
      decide: props.decide,
      view,
      now: readNow(),
    };
    if (props.onRefresh) {
      deps.onRefresh = props.onRefresh;
    }
    if (props.onConflict) {
      deps.onConflict = props.onConflict;
    }
    const outcome = await submitDecision(deps, decision);
    setBusy(false);
    if (!outcome.ok) {
      setAlert(accessibleMessage(outcome.ui_code, outcome.error.message));
      return;
    }
    setApproval(outcome.approval);
    props.onDecided?.(outcome.approval);
  }

  return (
    <section className="sentinel-approval" aria-labelledby="approval-title">
      <h2 id="approval-title">Approval required</h2>

      <dl className="sentinel-approval__facts">
        <div>
          <dt>Case</dt>
          <dd data-testid="case-id">{view.case_id}</dd>
        </div>
        <div>
          <dt>Case revision</dt>
          <dd data-testid="case-revision">{view.case_revision}</dd>
        </div>
        <div>
          <dt>Case status</dt>
          <dd data-testid="case-status">{view.case_status}</dd>
        </div>
        <div>
          <dt>Action</dt>
          <dd data-testid="action-id">{view.action_id}</dd>
        </div>
        <div>
          <dt>Transaction</dt>
          <dd data-testid="transaction-ref">{view.transaction_ref}</dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd data-testid="amount">{formatMinorUnits(view.amount_minor, view.currency)}</dd>
        </div>
        <div>
          <dt>Policy version</dt>
          <dd data-testid="policy-version">{view.policy_version}</dd>
        </div>
        <div>
          <dt>Action digest</dt>
          <dd data-testid="action-digest">
            <code>{view.action_digest}</code>
          </dd>
        </div>
        <div>
          <dt>Decision expiry</dt>
          <dd data-testid="decision-expires-at">{view.decision_expires_at}</dd>
        </div>
        <div>
          <dt>Reviewer</dt>
          <dd data-testid="reviewer-id">{view.reviewer_id}</dd>
        </div>
      </dl>

      <h3 id="evidence-heading">Evidence</h3>
      <ul aria-labelledby="evidence-heading" className="sentinel-approval__evidence">
        {view.evidence_ages.map((item) => (
          <li key={item.evidence_id} data-testid={`evidence-${item.evidence_id}`}>
            <span data-testid={`evidence-id-${item.evidence_id}`}>{item.evidence_id}</span>
            <span data-testid={`evidence-age-${item.evidence_id}`}>
              age {formatAgeSeconds(item.age_seconds)}
            </span>
            <span data-testid={`evidence-expires-${item.evidence_id}`}>
              expires {item.expires_at}
            </span>
            {item.expired ? (
              <span role="status" data-testid={`evidence-expired-${item.evidence_id}`}>
                expired
              </span>
            ) : null}
          </li>
        ))}
      </ul>

      {alert ? (
        <p role="alert" data-testid="decision-alert">
          {alert}
        </p>
      ) : null}

      {approval ? (
        <p role="status" data-testid="decision-result">
          Recorded {approval.decision} as {approval.approval_id} by {approval.reviewer_id}
        </p>
      ) : (
        <div className="sentinel-approval__actions">
          <button
            type="button"
            data-testid="approve"
            disabled={busy}
            onClick={() => void onDecide("APPROVE")}
          >
            Approve
          </button>
          <button
            type="button"
            data-testid="reject"
            disabled={busy}
            onClick={() => void onDecide("REJECT")}
          >
            Reject
          </button>
        </div>
      )}
    </section>
  );
}
