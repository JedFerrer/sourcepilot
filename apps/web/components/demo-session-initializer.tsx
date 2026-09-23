"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type DemoSessionState = "initializing" | "ready" | "unavailable";

export function DemoSessionInitializer({ children }: { children?: ReactNode }) {
  const [state, setState] = useState<DemoSessionState>("initializing");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setState("initializing");
    setErrorMessage(null);
    void apiRequest<void>("/api/demo-session", { method: "POST" })
      .then(() => {
        setState("ready");
      })
      .catch((error: unknown) => {
        setErrorMessage(
          error instanceof ApiClientError ? error.message : "Demo session unavailable. Please try again.",
        );
        setState("unavailable");
      });
  }, [attempt]);

  if (state === "initializing") {
    return <p className="session-status">Preparing your private demo session…</p>;
  }

  if (state === "ready") {
    return (
      <>
        <p className="session-status session-status--ready">Demo session ready</p>
        {children}
      </>
    );
  }

  return (
    <div className="session-status session-status--unavailable" role="alert">
      <p>{errorMessage}</p>
      <button type="button" onClick={() => setAttempt((currentAttempt) => currentAttempt + 1)}>
        Try again
      </button>
    </div>
  );
}
