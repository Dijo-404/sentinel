/**
 * Sentinel cube mark. Omit `inverse` to follow the theme (light-on-dark in Night Ledger,
 * dark-on-light in Paper); pass it to force a variant on a fixed-colour surface.
 */
export function LogoMark({
  size = 24,
  inverse,
  className,
}: {
  size?: number;
  inverse?: boolean;
  className?: string;
}) {
  const width = Math.round(size * (382 / 466));
  const cls = (extra: string) => ["logo-mark", extra, className].filter(Boolean).join(" ");
  if (inverse !== undefined) {
    return (
      <img
        src={inverse ? "/brand/sentinel-mark-inverse.svg" : "/brand/sentinel-mark.svg"}
        alt=""
        aria-hidden="true"
        width={width}
        height={size}
        className={cls("")}
      />
    );
  }
  return (
    <>
      <img
        src="/brand/sentinel-mark-inverse.svg"
        alt=""
        aria-hidden="true"
        width={width}
        height={size}
        className={cls("logo-mark--on-dark")}
      />
      <img
        src="/brand/sentinel-mark.svg"
        alt=""
        aria-hidden="true"
        width={width}
        height={size}
        className={cls("logo-mark--on-light")}
      />
    </>
  );
}
