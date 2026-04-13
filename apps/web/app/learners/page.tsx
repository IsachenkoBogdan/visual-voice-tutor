"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { buildApiHeaders, getClientEnv } from "@/lib/env";

interface LearnerProfile {
  learner_id: string;
  display_name: string;
  grade_band: string;
  pace_preference: string;
}

export default function LearnersPage() {
  const env = getClientEnv();
  const [userId, setUserId] = useState("demo_user");
  const [learners, setLearners] = useState<LearnerProfile[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load(): Promise<void> {
      try {
        setError(null);
        const response = await fetch(`${env.apiBaseUrl}/api/v1/accounts/${userId}/learners`, {
          signal: controller.signal,
          headers: buildApiHeaders(env.apiKey),
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = (await response.json()) as LearnerProfile[];
        setLearners(data);
      } catch (loadError) {
        setError(String(loadError));
      }
    }
    void load();
    return () => controller.abort();
  }, [env.apiBaseUrl, env.apiKey, userId]);

  return (
    <main className="min-h-screen bg-zinc-100 p-4 md:p-6">
      <section className="mx-auto w-full max-w-4xl space-y-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900">Learners</h1>
            <p className="text-sm text-zinc-600">Private alpha shell: learner profiles and session access.</p>
          </div>
          <Link href="/tutor" className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white">
            Open Tutor
          </Link>
        </div>

        <label className="flex max-w-sm flex-col gap-1 text-xs text-zinc-600">
          User ID
          <input
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
          />
        </label>

        {error ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">{error}</p> : null}

        <div className="grid gap-3 md:grid-cols-2">
          {learners.map((learner) => (
            <article key={learner.learner_id} className="rounded-xl border border-zinc-200 p-3">
              <h2 className="text-base font-semibold text-zinc-900">{learner.display_name}</h2>
              <p className="text-sm text-zinc-600">ID: {learner.learner_id}</p>
              <p className="text-sm text-zinc-600">Grade band: {learner.grade_band}</p>
              <p className="text-sm text-zinc-600">Pace: {learner.pace_preference}</p>
              <div className="mt-3 flex gap-2">
                <Link
                  href={`/learners/${learner.learner_id}`}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-xs text-zinc-700"
                >
                  Open Profile
                </Link>
                <Link
                  href={`/tutor?learner_id=${learner.learner_id}&user_id=${userId}`}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-xs text-zinc-700"
                >
                  Start Session
                </Link>
              </div>
            </article>
          ))}
        </div>

        {learners.length === 0 && !error ? (
          <p className="text-sm text-zinc-500">No linked learners yet. Link from backend API or tutor runtime.</p>
        ) : null}
      </section>
    </main>
  );
}
