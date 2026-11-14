import "@testing-library/jest-dom/vitest";

// jsdom has no IntersectionObserver; framer-motion's whileInView needs one.
class NoopIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
}
globalThis.IntersectionObserver ??=
  NoopIntersectionObserver as unknown as typeof IntersectionObserver;
