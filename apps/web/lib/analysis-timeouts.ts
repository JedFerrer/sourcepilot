// Public operational configuration only; never include provider credentials here.
const configured = Number(process.env.NEXT_PUBLIC_SOURCEPILOT_ANALYSIS_TIMEOUT_SECONDS ?? "180");
if (!Number.isFinite(configured) || configured <= 0) {
  throw new Error("Analysis timeout must be a positive finite number of seconds.");
}

export const analysisBackendMs = configured * 1000;
export const analysisProxyMs = analysisBackendMs + 10_000;
export const analysisBrowserMs = analysisBackendMs + 15_000;
