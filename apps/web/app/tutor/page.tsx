import { TutorShell } from "@/components/tutor/TutorShell";

export default async function TutorPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const learnerRaw = query.learner_id;
  const userRaw = query.user_id;
  const learnerId = Array.isArray(learnerRaw) ? learnerRaw[0] : learnerRaw;
  const userId = Array.isArray(userRaw) ? userRaw[0] : userRaw;

  return (
    <div className="h-screen min-h-screen overflow-hidden bg-zinc-100">
      <TutorShell initialLearnerId={learnerId ?? "demo_learner"} initialUserId={userId ?? "demo_user"} />
    </div>
  );
}
