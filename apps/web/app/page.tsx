import { DemoSessionInitializer } from "../components/demo-session-initializer";
import { HealthStatus } from "../components/health-status";

export default function Home() {
  return (
    <main>
      <h1>SourcePilot</h1>
      <p>AI-assisted, evidence-backed supplier sourcing workspace.</p>
      <DemoSessionInitializer />
      <HealthStatus />
    </main>
  );
}
