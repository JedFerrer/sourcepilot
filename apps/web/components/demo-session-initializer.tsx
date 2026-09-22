"use client";

import { useEffect, useState } from "react";

type DemoSessionState = "initializing" | "ready" | "unavailable";

export function DemoSessionInitializer() {
  const [state, setState] = useState<DemoSessionState>("initializing");

  useEffect(() => {
    void fetch("/api/demo-session", { method: "POST", credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Demo session request failed");
        }
        setState("ready");
      })
      .catch(() => setState("unavailable"));
  }, []);

  if (state === "initializing") {
    return <p className="session-status">Preparing your private demo session…</p>;
  }

  if (state === "ready") {
    return <p className="session-status session-status--ready">Demo session ready</p>;
  }

  return (
    <p className="session-status session-status--unavailable">
      Demo session unavailable. Refresh to try again.
    </p>
  );
}
