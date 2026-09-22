import { DemoSessionInitializer } from "../components/demo-session-initializer";
import { ProjectDashboard } from "../components/project-dashboard";

export default function Home() {
  return (
    <main>
      <h1>SourcePilot</h1>
      <p>AI-assisted, evidence-backed supplier sourcing workspace.</p>
      <DemoSessionInitializer>
        <ProjectDashboard />
      </DemoSessionInitializer>
    </main>
  );
}
