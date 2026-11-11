/** Readable display only: does not change API values or business rules. */
export function humanLabel(value: string): string {
  const lower = value.replaceAll("_", " ").toLowerCase();
  return lower ? lower[0].toUpperCase() + lower.slice(1) : "";
}
export function displayDate(value: unknown): string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return String(value ?? "Not provided");
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(date);
}
export function displayRequirement(value: Record<string, unknown>): string {
  if (value.kind === "DATE") return displayDate(value.date);
  if (value.kind === "PERIOD") return [value.label, value.start_date ? `From ${displayDate(value.start_date)}` : null, value.end_date ? `Until ${displayDate(value.end_date)}` : null].filter(Boolean).join(" · ") || "Not provided";
  if ("text" in value) return String(value.text || "Not provided");
  if ("amount" in value) return `${value.amount ?? "Not provided"}${value.currency ? ` ${value.currency}` : " · Currency not provided"}`;
  if ("max_days" in value) return `${value.max_days} days maximum`;
  if ("quantity" in value) return `${value.quantity} units`;
  if ("value" in value) return value.value === true ? "Yes" : value.value === false ? "No" : String(value.value ?? "Not provided");
  return Object.entries(value).filter(([, item]) => item != null && item !== "").map(([key, item]) => `${humanLabel(key)}: ${String(item)}`).join(" · ") || "Not provided";
}
export function requirementLabel(kind: string, value: Record<string, unknown>): string {
  return humanLabel(String(kind === "CAPABILITY" ? value.capability_key ?? kind : kind === "INFORMATIONAL" ? value.subject ?? "Additional context" : kind));
}
