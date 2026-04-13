"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { buildApiHeaders, getClientEnv } from "@/lib/env";

interface LearnerProfile {
  learner_id: string;
  display_name: string;
  grade_band: string;
  pace_preference: string;
  weak_spots: string[];
  recurring_mistakes: string[];
  recent_topics: string[];
}

interface SessionSummary {
  session_id: string;
  turn_id: string;
  result: string;
  summary: string;
  created_at: string;
}

interface EntitlementStatus {
  status: string;
  reason: string;
  plan_id: string;
  turns_used_this_month: number;
  turns_limit_this_month: number | null;
  can_use_voice_loop: boolean;
}

export default function LearnerDetailPage({
  params,
}: {
  params: Promise<{ learnerId: string }>;
}) {
  const env = getClientEnv();
  const { learnerId } = use(params);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [entitlement, setEntitlement] = useState<EntitlementStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load(): Promise<void> {
      try {
        setError(null);
        const [profileResp, sessionResp, entResp] = await Promise.all([
          fetch(`${env.apiBaseUrl}/api/v1/learners/${learnerId}`, {
            signal: controller.signal,
            headers: buildApiHeaders(env.apiKey),
          }),
          fetch(`${env.apiBaseUrl}/api/v1/learners/${learnerId}/sessions?limit=20`, {
            signal: controller.signal,
            headers: buildApiHeaders(env.apiKey),
          }),
          fetch(`${env.apiBaseUrl}/api/v1/billing/entitlement/${learnerId}`, {
            signal: controller.signal,
            headers: buildApiHeaders(env.apiKey),
          }),
        ]);
        if (!profileResp.ok || !sessionResp.ok || !entResp.ok) {
          throw new Error(`HTTP ${profileResp.status}/${sessionResp.status}/${entResp.status}`);
        }
        setProfile((await profileResp.json()) as LearnerProfile);
        setSessions((await sessionResp.json()) as SessionSummary[]);
        setEntitlement((await entResp.json()) as EntitlementStatus);
      } catch (loadError) {
        setError(String(loadError));
      }
    }
    void load();
    return () => controller.abort();
  }, [env.apiBaseUrl, env.apiKey, learnerId]);

  return (
    <main className="min-h-screen bg-zinc-100 p-4 md:p-6">
      <section className="mx-auto w-full max-w-5xl space-y-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900">Learner Profile</h1>
            <p className="text-sm text-zinc-600">{learnerId}</p>
          </div>
          <div className="flex gap-2">
            <Link href="/learners" className="rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-700">
              Back
            </Link>
            <Link
              href={`/tutor?learner_id=${learnerId}&user_id=demo_user`}
              className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white"
            >
              Open Tutor
            </Link>
          </div>
        </div>

        {error ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">{error}</p> : null}

        {profile ? (
          <section className="grid gap-2 rounded-xl border border-zinc-200 p-3 text-sm text-zinc-700 md:grid-cols-2">
            <div>Display name: {profile.display_name}</div>
            <div>Grade band: {profile.grade_band}</div>
            <div>Pace preference: {profile.pace_preference}</div>
            <div>Recent topics: {profile.recent_topics.join(", ") || "none"}</div>
            <div className="md:col-span-2">Recurring mistakes: {profile.recurring_mistakes.join(", ") || "none"}</div>
            <div className="md:col-span-2">Weak spots: {profile.weak_spots.join(", ") || "none"}</div>
          </section>
        ) : null}

        {entitlement ? (
          <section className="rounded-xl border border-zinc-200 p-3 text-sm text-zinc-700">
            <h2 className="mb-2 text-sm font-semibold text-zinc-900">Entitlement</h2>
            <div className="grid gap-2 md:grid-cols-2">
              <div>Plan: {entitlement.plan_id}</div>
              <div>Status: {entitlement.status}</div>
              <div>Reason: {entitlement.reason}</div>
              <div>
                Usage: {entitlement.turns_used_this_month} / {entitlement.turns_limit_this_month ?? "unlimited"}
              </div>
              <div>Voice loop: {String(entitlement.can_use_voice_loop)}</div>
            </div>
          </section>
        ) : null}

        <section className="rounded-xl border border-zinc-200 p-3">
          <h2 className="mb-2 text-sm font-semibold text-zinc-900">Session History</h2>
          <div className="space-y-2">
            {sessions.map((session) => (
              <article key={`${session.session_id}-${session.turn_id}`} className="rounded border border-zinc-100 bg-zinc-50 p-2">
                <div className="text-xs text-zinc-500">
                  {session.session_id} • {session.turn_id} • {new Date(session.created_at).toLocaleString()}
                </div>
                <div className="text-sm text-zinc-700">{session.result}</div>
                <div className="text-sm text-zinc-800">{session.summary}</div>
              </article>
            ))}
            {sessions.length === 0 ? <p className="text-sm text-zinc-500">No sessions yet.</p> : null}
          </div>
        </section>
      </section>
    </main>
  );
}
