"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  label: string;
  /** How long the press must last, ms. */
  durationMs?: number;
  onCommit: () => void;
  disabled?: boolean;
  describedBy?: string;
};

/**
 * Press-and-hold commit for irreversible actions. Mouse, touch and keyboard
 * (hold Space or Enter). Releasing early cancels and resets to zero.
 */
export function HoldButton({ label, durationMs = 1200, onCommit, disabled, describedBy }: Props) {
  const [progress, setProgress] = useState(0);
  const start = useRef<number | null>(null);
  const raf = useRef<number | null>(null);
  const committed = useRef(false);

  function stop(reset = true) {
    if (raf.current !== null) cancelAnimationFrame(raf.current);
    raf.current = null;
    start.current = null;
    if (reset && !committed.current) setProgress(0);
  }

  function step(now: number) {
    if (start.current === null) start.current = now;
    const p = Math.min(1, (now - start.current) / durationMs);
    setProgress(p);
    if (p >= 1) {
      committed.current = true;
      stop(false);
      onCommit();
      return;
    }
    raf.current = requestAnimationFrame(step);
  }

  function begin() {
    if (disabled || committed.current || raf.current !== null) return;
    raf.current = requestAnimationFrame(step);
  }

  useEffect(() => () => stop(false), []);

  const pct = Math.round(progress * 100);
  return (
    <button
      type="button"
      className="hold-btn"
      disabled={disabled}
      aria-describedby={describedBy}
      data-past-half={progress > 0.45 || undefined}
      onPointerDown={begin}
      onPointerUp={() => stop()}
      onPointerLeave={() => stop()}
      onPointerCancel={() => stop()}
      onKeyDown={(e) => {
        if ((e.key === " " || e.key === "Enter") && !e.repeat) {
          e.preventDefault();
          begin();
        }
      }}
      onKeyUp={(e) => {
        if (e.key === " " || e.key === "Enter") stop();
      }}
      onClick={(e) => e.preventDefault()}
    >
      <span className="hold-btn__fill" style={{ width: `${pct}%` }} aria-hidden="true" />
      <span className="hold-btn__label">{pct > 0 && pct < 100 ? `Keep holding… ${pct}%` : label}</span>
    </button>
  );
}
