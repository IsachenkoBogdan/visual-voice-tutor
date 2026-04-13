"use client";

import { useEffect, useState } from "react";

import { buildApiHeaders, getClientEnv } from "@/lib/env";

interface PlanSpec {
  plan_id: "free" | "pro" | "team";
  title: string;
  monthly_price_usd: number;
  monthly_turn_limit: number | null;
  features: string[];
}

interface SubscriptionState {
  learner_id: string;
  plan_id: "free" | "pro" | "team";
  status: string;
  monthly_turn_limit: number | null;
  renews_at: string | null;
}

interface EntitlementState {
  status: string;
  reason: string;
  turns_used_this_month: number;
  turns_limit_this_month: number | null;
  can_use_voice_loop: boolean;
}

export default function BillingPage() {
  const env = getClientEnv();
  const [learnerId, setLearnerId] = useState("demo_learner");
  const [plans, setPlans] = useState<PlanSpec[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionState | null>(null);
  const [entitlement, setEntitlement] = useState<EntitlementState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload(): Promise<void> {
    try {
      setError(null);
      const [plansResp, subResp, entResp] = await Promise.all([
        fetch(`${env.apiBaseUrl}/api/v1/billing/plans`, { headers: buildApiHeaders(env.apiKey) }),
        fetch(`${env.apiBaseUrl}/api/v1/billing/subscription/${learnerId}`, {
          headers: buildApiHeaders(env.apiKey),
        }),
        fetch(`${env.apiBaseUrl}/api/v1/billing/entitlement/${learnerId}`, {
          headers: buildApiHeaders(env.apiKey),
        }),
      ]);
      if (!plansResp.ok || !subResp.ok || !entResp.ok) {
        throw new Error(`HTTP ${plansResp.status}/${subResp.status}/${entResp.status}`);
      }
      setPlans((await plansResp.json()) as PlanSpec[]);
      setSubscription((await subResp.json()) as SubscriptionState);
      setEntitlement((await entResp.json()) as EntitlementState);
    } catch (loadError) {
      setError(String(loadError));
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learnerId, env.apiBaseUrl]);

  async function changePlan(planId: "free" | "pro" | "team", turnLimit: number | null): Promise<void> {
    if (!subscription) {
      return;
    }
    try {
      setBusy(true);
      setError(null);
      const payload: SubscriptionState = {
        ...subscription,
        learner_id: learnerId,
        plan_id: planId,
        status: "active",
        monthly_turn_limit: turnLimit,
      };
      const response = await fetch(`${env.apiBaseUrl}/api/v1/billing/subscription/${learnerId}`, {
        method: "PUT",
        headers: { "content-type": "application/json", ...buildApiHeaders(env.apiKey) },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      await reload();
    } catch (updateError) {
      setError(String(updateError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-100 p-4 md:p-6">
      <section className="mx-auto w-full max-w-5xl space-y-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm md:p-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">Billing & Entitlements</h1>
          <p className="text-sm text-zinc-600">v0.9 groundwork: plans, subscription state, usage gating.</p>
        </div>

        <label className="flex max-w-sm flex-col gap-1 text-xs text-zinc-600">
          Learner ID
          <input
            value={learnerId}
            onChange={(event) => setLearnerId(event.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-900"
          />
        </label>

        {error ? <p className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">{error}</p> : null}

        {subscription ? (
          <section className="rounded-xl border border-zinc-200 p-3 text-sm text-zinc-700">
            <h2 className="mb-2 text-sm font-semibold text-zinc-900">Current Subscription</h2>
            <div className="grid gap-2 md:grid-cols-2">
              <div>Plan: {subscription.plan_id}</div>
              <div>Status: {subscription.status}</div>
              <div>Turn limit: {subscription.monthly_turn_limit ?? "unlimited"}</div>
              <div>Renews at: {subscription.renews_at ?? "n/a"}</div>
            </div>
          </section>
        ) : null}

        {entitlement ? (
          <section className="rounded-xl border border-zinc-200 p-3 text-sm text-zinc-700">
            <h2 className="mb-2 text-sm font-semibold text-zinc-900">Entitlement</h2>
            <div className="grid gap-2 md:grid-cols-2">
              <div>Status: {entitlement.status}</div>
              <div>Reason: {entitlement.reason}</div>
              <div>
                Turns used: {entitlement.turns_used_this_month} / {entitlement.turns_limit_this_month ?? "unlimited"}
              </div>
              <div>Voice loop enabled: {String(entitlement.can_use_voice_loop)}</div>
            </div>
          </section>
        ) : null}

        <section className="grid gap-3 md:grid-cols-3">
          {plans.map((plan) => (
            <article key={plan.plan_id} className="rounded-xl border border-zinc-200 p-3">
              <h3 className="text-base font-semibold text-zinc-900">{plan.title}</h3>
              <p className="text-sm text-zinc-600">${plan.monthly_price_usd}/mo</p>
              <p className="text-sm text-zinc-600">Turn limit: {plan.monthly_turn_limit ?? "unlimited"}</p>
              <ul className="mt-2 space-y-1 text-xs text-zinc-600">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <button
                type="button"
                disabled={busy}
                className="mt-3 w-full rounded-md border border-zinc-300 px-2 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
                onClick={() => {
                  void changePlan(plan.plan_id, plan.monthly_turn_limit);
                }}
              >
                Switch to {plan.title}
              </button>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
