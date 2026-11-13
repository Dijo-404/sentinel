type Props = {
  title: string;
  detail?: string;
  tone: "loading" | "error" | "empty" | "permission";
};

export function UiState({ title, detail, tone }: Props) {
  const role = tone === "error" || tone === "permission" ? "alert" : "status";
  return (
    <div
      className="state-banner"
      data-tone={tone}
      data-testid={`state-${tone}`}
      role={role}
      aria-live={tone === "loading" ? "polite" : "assertive"}
    >
      <strong>{title}</strong>
      {detail ? <p className="muted" style={{ margin: "0.35rem 0 0" }}>{detail}</p> : null}
    </div>
  );
}
