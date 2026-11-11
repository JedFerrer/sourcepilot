import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";

// jsdom has no layout engine. Browser reflow/zoom is verified separately.
if (typeof window !== "undefined") {
Object.defineProperty(window, "matchMedia", { writable: true, value: vi.fn((query: string) => ({
  matches: false, media: query, onchange: null,
  addEventListener: vi.fn(), removeEventListener: vi.fn(), addListener: vi.fn(), removeListener: vi.fn(), dispatchEvent: vi.fn(),
})) });
window.scrollTo = vi.fn();
afterEach(() => { window.history.replaceState(null, "", "/"); });
}
