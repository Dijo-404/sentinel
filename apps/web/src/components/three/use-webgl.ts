"use client";

import { useEffect, useState, type RefObject } from "react";

/** null until checked on the client; false in jsdom, old browsers or blocked GPUs. */
export function useWebGL(): boolean | null {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    if (typeof window.WebGLRenderingContext === "undefined") {
      setOk(false);
      return;
    }
    try {
      const canvas = document.createElement("canvas");
      setOk(Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl")));
    } catch {
      setOk(false);
    }
  }, []);
  return ok;
}

/** Pause render loops for canvases scrolled out of view. */
export function useInView(ref: RefObject<HTMLElement | null>): boolean {
  const [inView, setInView] = useState(true);
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) =>
      setInView(Boolean(entry?.isIntersecting)),
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [ref]);
  return inView;
}
