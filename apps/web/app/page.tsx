import { DemoSessionInitializer } from "../components/demo-session-initializer";
import { ProjectDashboard } from "../components/project-dashboard";
import Link from "next/link";

export default function Home() {
  return (
    <main id="main-content">
      <header className="app-header"><Link className="brand" href="/"><span className="brand-mark">SP</span>SourcePilot</Link><p>Evidence for better sourcing decisions</p></header>
      <DemoSessionInitializer>
        <ProjectDashboard />
      </DemoSessionInitializer>
    </main>
  );
}
