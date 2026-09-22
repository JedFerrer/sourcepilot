import { DemoSessionInitializer } from "../../../components/demo-session-initializer";
import { ProjectWorkspace } from "../../../components/project-workspace";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return (
    <main>
      <DemoSessionInitializer>
        <ProjectWorkspace projectId={projectId} />
      </DemoSessionInitializer>
    </main>
  );
}
