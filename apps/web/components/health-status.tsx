"use client";

import { useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type HealthState = "loading" | "connected" | "unavailable";

export function HealthStatus() {
  const [state, setState] = useState<HealthState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setState("loading");
    setErrorMessage(null);
    void apiRequest<{ status: string }>("/api/health")
      .then(() => {
        setState("connected");
      })
      .catch((error: unknown) => {
        setErrorMessage(error instanceof ApiClientError ? error.message : "API unavailable. Please try again.");
        setState("unavailable");
      });
  }, [attempt]);

  if (state === "loading") {
    return <p className="health-status">Checking API connection…</p>;
  }

  if (state === "connected") {
    return <p className="health-status health-status--connected">API connected</p>;
  }

  return (
    <div className="health-status health-status--unavailable" role="alert">
      <p>{errorMessage}</p>
      <button type="button" onClick={() => setAttempt((currentAttempt) => currentAttempt + 1)}>
        Try again
      </button>
    </div>
  );
}
