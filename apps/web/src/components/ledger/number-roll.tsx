"use client";

/** Per-digit rolling number. Non-digits (₹ , . %) render static. Screen readers get plain text. */
export function NumberRoll({ value, className }: { value: string; className?: string }) {
  return (
    <span className={`roll tnum ${className ?? ""}`}>
      <span className="sr-only">{value}</span>
      <span aria-hidden="true" style={{ display: "inline-flex" }}>
        {value.split("").map((ch, i) => {
          const d = Number.parseInt(ch, 10);
          if (Number.isNaN(d)) return <span key={`${i}-${ch}`}>{ch}</span>;
          return (
            <span key={i} className="roll__digit" style={{ transform: `translateY(-${d}em)` }}>
              {DIGITS.map((n) => (
                <span key={n}>{n}</span>
              ))}
            </span>
          );
        })}
      </span>
    </span>
  );
}

const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
