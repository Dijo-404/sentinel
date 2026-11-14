"use client";

import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
} from "framer-motion";
import { useEffect, useRef, useState } from "react";

type Mode = "default" | "hover" | "text" | "hidden";

const INTERACTIVE =
  'a[href], button:not(:disabled), [role="button"], [role="tab"], label, select, summary, [data-cursor]';
const TEXTUAL =
  'input:not([type="checkbox"], [type="radio"], [type="range"], [type="submit"], [type="button"]), textarea, [contenteditable="true"]';

function modeFor(target: Element | null): { mode: Mode; label: string | null } {
  if (!target) return { mode: "default", label: null };
  if (target.closest(TEXTUAL)) return { mode: "text", label: null };
  const labelled = target.closest("[data-cursor]");
  if (labelled) {
    return {
      mode: "hover",
      label: labelled.getAttribute("data-cursor") || null,
    };
  }
  if (target.closest(INTERACTIVE)) return { mode: "hover", label: null };
  return { mode: "default", label: null };
}

/**
 * Site-wide arrow cursor for fine pointers. Touch devices and text fields keep the
 * native cursor; `data-cursor="Label"` on an element shows a hint pill beside it.
 */
export function Cursor() {
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<Mode>("hidden");
  const [label, setLabel] = useState<string | null>(null);
  const [pressed, setPressed] = useState(false);
  const current = useRef<{ mode: Mode; label: string | null }>({
    mode: "hidden",
    label: null,
  });
  const reduce = useReducedMotion();
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  // A light spring keeps the arrow glued to the pointer while smoothing jitter.
  const sx = useSpring(x, { stiffness: 2200, damping: 90, mass: 0.2 });
  const sy = useSpring(y, { stiffness: 2200, damping: 90, mass: 0.2 });

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(hover: hover) and (pointer: fine)");
    const update = () => setEnabled(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const root = document.documentElement;
    root.dataset.pointer = "custom";

    const commit = (next: { mode: Mode; label: string | null }) => {
      if (
        next.mode === current.current.mode &&
        next.label === current.current.label
      ) {
        return;
      }
      current.current = next;
      setMode(next.mode);
      setLabel(next.label);
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType !== "mouse") return;
      x.set(event.clientX);
      y.set(event.clientY);
      if (current.current.mode === "hidden") {
        sx.jump(event.clientX);
        sy.jump(event.clientY);
      }
      commit(modeFor(event.target as Element));
    };
    const leave = (event: MouseEvent) => {
      if (!event.relatedTarget) commit({ mode: "hidden", label: null });
    };
    const down = () => setPressed(true);
    const up = () => setPressed(false);
    const hide = () => commit({ mode: "hidden", label: null });

    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", down);
    window.addEventListener("pointerup", up);
    window.addEventListener("blur", hide);
    document.addEventListener("mouseout", leave);
    return () => {
      delete root.dataset.pointer;
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", down);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("blur", hide);
      document.removeEventListener("mouseout", leave);
    };
  }, [enabled, x, y, sx, sy]);

  if (!enabled) return null;

  const hover = mode === "hover";
  const visible = mode === "default" || hover;

  return (
    <motion.div
      className="cursor"
      style={{ x: reduce ? x : sx, y: reduce ? y : sy }}
      aria-hidden="true"
    >
      <motion.svg
        viewBox="0 0 26 26"
        initial={false}
        animate={{
          opacity: visible ? 1 : 0,
          scale: !visible ? 0.6 : pressed ? 0.86 : hover ? 1.12 : 1,
          rotate: hover ? -12 : 0,
        }}
        transition={
          reduce
            ? { duration: 0 }
            : { type: "spring", stiffness: 520, damping: 28, mass: 0.5 }
        }
        style={{ originX: "3px", originY: "2px" }}
      >
        <path
          d="M3 2.2 21.6 12.4 12.3 15.2 6.4 22.2Z"
          className="cursor__arrow"
          data-hover={hover || undefined}
          strokeWidth="2.2"
          strokeLinejoin="round"
        />
      </motion.svg>
      <AnimatePresence>
        {label && visible ? (
          <motion.span
            key={label}
            className="cursor__label"
            initial={{ opacity: 0, scale: 0.7, x: -6 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={
              reduce
                ? { duration: 0 }
                : { type: "spring", stiffness: 420, damping: 26 }
            }
          >
            {label}
          </motion.span>
        ) : null}
      </AnimatePresence>
    </motion.div>
  );
}
