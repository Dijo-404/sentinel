import { StrictMode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import previewBundle from "../../fixtures/preview-bundle.json";
import { ApprovalPanel } from "../ui/ApprovalPanel.js";
import type {
  ActionRecord,
  Approval,
  Case,
  DecisionRequest,
  Evidence,
} from "../domain/types.js";
import { createCaseApiStub } from "../../tests/stubs/case-api.js";

const caseRecord = previewBundle.case as Case;
const action = previewBundle.action as ActionRecord;
const evidence = previewBundle.evidence as Evidence[];
const virtualNow = new Date(previewBundle.virtual_now);

function PreviewApp() {
  const [events, setEvents] = useState<string[]>([]);
  const stub = useMemo(
    () =>
      createCaseApiStub("valid", {
        principal: previewBundle.reviewer,
        approval: previewBundle.approval_response as Approval,
      }),
    [],
  );

  const decide = async (actionId: string, request: DecisionRequest) => {
    setEvents((prev) => [
      ...prev,
      `decide ${actionId} ${request.decision} digest=${request.action_digest}`,
    ]);
    return stub.decide(actionId, request);
  };

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "2rem", maxWidth: 720 }}>
      <p data-testid="preview-mode">mode: fixture (local stubs; no live API)</p>
      <ApprovalPanel
        case={caseRecord}
        action={action}
        evidence={evidence}
        decide={decide}
        reviewerId={previewBundle.reviewer.principal_id}
        decisionExpiresAt={previewBundle.decision_expires_at}
        now={() => virtualNow}
        onRefresh={(event) =>
          setEvents((prev) => [...prev, `refresh:${event.reason_code}`])
        }
        onConflict={(event) =>
          setEvents((prev) => [...prev, `conflict:${event.reason_code}`])
        }
      />
      <h2>Preview events</h2>
      <ul data-testid="preview-events">
        {events.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </main>
  );
}

const root = document.getElementById("root");
if (!root) {
  throw new Error("preview root missing");
}
createRoot(root).render(
  <StrictMode>
    <PreviewApp />
  </StrictMode>,
);
