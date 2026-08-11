"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CreditCard, Check, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { toast } from "@/components/Toaster";
import { formatCents, cn } from "@/lib/utils";
import type { UsageStats } from "@/types";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price_cents: 0,
    invocations: 100,
    features: ["100 invocations / month", "All public agents", "Community support"],
  },
  {
    id: "starter",
    name: "Starter",
    price_cents: 1900,
    invocations: 1000,
    features: ["1,000 invocations / month", "Priority routing", "Email support"],
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price_cents: 9900,
    invocations: 10000,
    features: ["10,000 invocations / month", "Private agents", "Analytics export", "Slack support"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price_cents: 49900,
    invocations: 100000,
    features: ["100,000 invocations / month", "SSO + SAML", "Dedicated infra", "SLA"],
  },
];

export default function BillingPage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        setUsage(await api.getUsage());
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [user]);

  const upgrade = async (planId: string) => {
    try {
      const result = await api.upgradePlan(planId);
      toast(`Upgraded to ${result.plan.toUpperCase()}`, "success");
      setUsage(await api.getUsage());
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  const checkout = async (planId: string) => {
    try {
      const result = await api.createCheckout(planId);
      if (result.checkout_url.startsWith("http")) {
        window.location.href = result.checkout_url;
      } else {
        // Mock mode
        await upgrade(planId);
      }
    } catch (e) {
      toast((e as Error).message, "error");
    }
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-zinc-900">Billing</h1>
        <p className="mt-2 text-zinc-600">Sign in to manage your subscription.</p>
        <Link href="/login" className="btn-primary mt-4 inline-flex">Sign in</Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-zinc-900 mb-6">Billing & Subscription</h1>

      {/* Current plan */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-zinc-900">Current plan</h2>
            <p className="text-sm text-zinc-500 mt-1">
              {usage ? `${usage.invocations_used} of ${usage.invocations_included} invocations used this period` : "Loading..."}
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-zinc-900 uppercase">{usage?.plan || "free"}</p>
            {usage && (
              <p className="text-sm text-zinc-500">
                {formatCents(usage.cost_this_month_cents)} this month
              </p>
            )}
          </div>
        </div>
        {usage && (
          <div className="mt-4 h-2 w-full rounded-full bg-zinc-200 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full",
                usage.invocations_used / usage.invocations_included > 0.9
                  ? "bg-red-500"
                  : "bg-brand-500"
              )}
              style={{
                width: `${Math.min(100, (usage.invocations_used / usage.invocations_included) * 100)}%`,
              }}
            />
          </div>
        )}
      </div>

      {/* Plans */}
      <h2 className="font-semibold text-zinc-900 mb-4">Available plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = (usage?.plan || "free") === plan.id;
          return (
            <div
              key={plan.id}
              className={cn(
                "card p-6 relative flex flex-col",
                plan.popular && "border-brand-500 ring-1 ring-brand-500"
              )}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-600 px-3 py-0.5 text-xs font-medium text-white">
                  Popular
                </span>
              )}
              <h3 className="font-semibold text-zinc-900">{plan.name}</h3>
              <p className="mt-2 text-2xl font-bold text-zinc-900">
                {formatCents(plan.price_cents)}
                <span className="text-sm font-normal text-zinc-500">/mo</span>
              </p>
              <p className="text-xs text-zinc-500 mt-1">
                <Zap className="inline h-3 w-3" /> {plan.invocations.toLocaleString()} invocations
              </p>
              <ul className="mt-4 space-y-2 text-sm flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-zinc-700">
                    <Check className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => checkout(plan.id)}
                disabled={isCurrent}
                className={cn(
                  "mt-6 w-full",
                  isCurrent ? "btn-secondary" : plan.popular ? "btn-primary" : "btn-secondary"
                )}
              >
                {isCurrent ? "Current plan" : <><CreditCard className="h-4 w-4" /> Upgrade</>}
              </button>
            </div>
          );
        })}
      </div>

      <p className="mt-6 text-center text-xs text-zinc-500">
        In demo mode, upgrades are instant (no real charge). Configure STRIPE_SECRET_KEY in .env to enable real Stripe checkout.
      </p>
    </div>
  );
}
