"use client";

import { useRef, type PointerEvent } from "react";

/** Oversized wordmark that rests dim; the pointer lights it like a torch. */
export function FooterWordmark() {
  const wrap = useRef<HTMLDivElement>(null);

  function move(event: PointerEvent<HTMLDivElement>) {
    const node = wrap.current;
    if (!node || event.pointerType !== "mouse") return;
    const rect = node.getBoundingClientRect();
    node.style.setProperty("--spot-x", `${event.clientX - rect.left}px`);
    node.style.setProperty("--spot-y", `${event.clientY - rect.top}px`);
    node.dataset.lit = "true";
  }

  return (
    <div
      ref={wrap}
      className="wordmark"
      aria-hidden="true"
      onPointerMove={move}
      onPointerLeave={() => {
        if (wrap.current) delete wrap.current.dataset.lit;
      }}
    >
      <span className="wordmark__base">Sentinel</span>
      <span className="wordmark__lit">Sentinel</span>
    </div>
  );
}
