"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { fragmentStage, resolveStage, stageUrl } from "../lib/workspace-navigation";
import { type WorkflowStage } from "../lib/workflow";

type Position = { focus?: HTMLElement; scroll: number };
export function useWorkspaceNavigation(projectId: string, fallback?: WorkflowStage) {
  const [stage, setStage] = useState<WorkflowStage>("BRIEF");
  const initialized = useRef<string | null>(null);
  const stageRef = useRef(stage);
  stageRef.current = stage;
  const positions = useRef<Partial<Record<WorkflowStage, Position>>>({});
  const focusStage = useCallback((next: WorkflowStage, target?: string, restore = false) => {
    requestAnimationFrame(() => {
      const position = restore ? positions.current[next] : undefined;
      const heading = document.getElementById(`${next.toLowerCase()}-title`);
      const element = (target ? document.getElementById(target) : position?.focus?.isConnected ? position.focus : null) ?? heading;
      if (element) {
        if (!element.matches("button, input, select, textarea, a, [tabindex]")) element.tabIndex = -1;
        element.focus({ preventScroll: true });
        if (position) window.scrollTo?.(0, position.scroll);
        else element.scrollIntoView?.({ block: "start" });
      }
    });
  }, []);
  const remember = useCallback(() => {
    const previous = positions.current[stageRef.current];
    const active = document.activeElement as HTMLElement | null;
    positions.current[stageRef.current] = { focus: active?.closest(".stage-panel") ? active : previous?.focus, scroll: window.scrollY };
  }, []);
  const navigate = useCallback((next: WorkflowStage, target?: string) => {
    remember();
    window.history.pushState(window.history.state, "", stageUrl(new URL(window.location.href), next, target));
    setStage(next);
    focusStage(next, target);
  }, [focusStage, remember]);
  useEffect(() => {
    if (initialized.current !== projectId) {
      initialized.current = projectId;
      positions.current = {};
      const url = new URL(window.location.href);
      const selected = resolveStage(url, fallback);
      setStage(selected);
      const compatible = fragmentStage(url.hash) === selected ? url.hash : "";
      window.history.replaceState(window.history.state, "", stageUrl(url, selected, compatible));
      if (compatible) focusStage(selected, compatible.slice(1));
    }
    const pop = () => { remember(); const next = resolveStage(new URL(window.location.href), fallback); setStage(next); focusStage(next, undefined, true); };
    const anchor = (event: MouseEvent) => {
      const link = (event.target as Element).closest?.('a[href^="#"]');
      const hash = link?.getAttribute("href");
      const next = hash ? fragmentStage(hash) : null;
      if (next && hash) { event.preventDefault(); navigate(next, hash.slice(1)); }
    };
    const focus = (event: FocusEvent) => { const element = event.target as HTMLElement; if (element.closest?.(".stage-panel")) positions.current[stageRef.current] = { focus: element, scroll: window.scrollY }; };
    document.addEventListener("focusin", focus);
    window.addEventListener("popstate", pop);
    document.addEventListener("click", anchor);
    return () => { document.removeEventListener("focusin", focus); window.removeEventListener("popstate", pop); document.removeEventListener("click", anchor); };
  }, [projectId, fallback, focusStage, remember, navigate]);
  return { stage, navigate };
}
