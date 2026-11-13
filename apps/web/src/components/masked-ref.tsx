type Props = {
  label: string;
  masked: string;
  full?: string;
};

/** Display masked payment/PII refs; full value never shown in UI text. */
export function MaskedRef({ label, masked, full }: Props) {
  return (
    <span className="mono" data-testid="masked-ref" title={label}>
      <span className="sr-only">{label}: </span>
      {masked}
      {full ? (
        <span className="sr-only" data-full-hidden="true">
          (full value redacted)
        </span>
      ) : null}
    </span>
  );
}
