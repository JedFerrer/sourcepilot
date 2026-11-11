/** Focus only the current visible editor; never pull users out of a hidden stage. */
export function focusEditorTarget(target: HTMLElement | null): boolean {
  if (!target?.isConnected || target.closest("[hidden], [inert]")) return false;
  for (let element: HTMLElement | null = target; element; element = element.parentElement) {
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
  }
  target.focus({ preventScroll: true });
  if (document.activeElement !== target) return false;
  target.scrollIntoView?.({ block: "center", inline: "nearest", behavior: "instant" });
  return true;
}
