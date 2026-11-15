/** Sentinel cube mark. `inverse` is the light-on-dark version for night surfaces. */
export function LogoMark({
  size = 24,
  inverse = false,
  className,
}: {
  size?: number;
  inverse?: boolean;
  className?: string;
}) {
  return (
    <img
      src={inverse ? "/brand/sentinel-mark-inverse.svg" : "/brand/sentinel-mark.svg"}
      alt=""
      aria-hidden="true"
      width={Math.round(size * (382 / 466))}
      height={size}
      className={className ? `logo-mark ${className}` : "logo-mark"}
    />
  );
}
