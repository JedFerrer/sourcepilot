"use client";

import { useEffect, useState } from "react";

type HealthState = "loading" | "connected" | "unavailable";

export function HealthStatus() {
  const [state, setState] = useState<HealthState>("loading");

  useEffect(() => {
    void fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Health request failed");
        }

        setState("connected");
      })
      .catch(() => setState("unavailable"));
  }, []);

  if (state === "loading") {
    return <p className="health-status">Checking API connection…</p>;
  }

  if (state === "connected") {
    return <p className="health-status health-status--connected">API connected</p>;
  }

  return <p className="health-status health-status--unavailable">API unavailable</p>;
}
