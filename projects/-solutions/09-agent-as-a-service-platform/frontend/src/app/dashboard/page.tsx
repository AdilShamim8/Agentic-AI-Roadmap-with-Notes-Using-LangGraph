"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Zap, DollarSign, TrendingUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatCents, formatNumber, timeAgo } from "@/lib/utils";
import type { Invocation, UsageStats } from "@/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [invocations, setInvocations] = useState<Invocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const [u, inv] = await Promise.all([api.getUsage(), api.listInvocations()]);
        setUsage(u);
        setInvocations(inv);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [user]);

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-zinc-900">Your dashboard</h1>
        <p className="mt-2 text-zinc-600">Sign in to see your usage.</p>
        <Link href="/login" className="btn-primary mt-4 inline-flex">Sign in</Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="card p-8 animate-pulse">
          <div className="h-6 w-1/3 bg-zinc-200 rounded" />
        </div>
      </div>
    );
  }

  const chartData = (usage?.by_agent || []).slice(0, 10).map((a) => ({
    name: a.name.length > 12 ? a.name.slice(0, 12) + "…" : a.name,
    invocations: a.count,
    cost: a.cost_cents / 100,
  }));

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-zinc-900 mb-6">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Total invocations"
          value={formatNumber(usage?.total_invocations || 0)}
          color="text-brand-600 bg-brand-50"
        />
        <StatCard
          icon={<DollarSign className="h-5 w-5" />}
          label="Total spent"
          value={formatCents(usage?.total_cost_cents || 0)}
          color="text-green-600 bg-green-50"
        />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="This month"
          value={`${usage?.invocations_this_month || 0} calls`}
          color="text-blue-600 bg-blue-50"
        />
        <StatCard
          icon={<Activity className="h-5 w-5" />}
          label="Plan"
          value={(usage?.plan || "free").toUpperCase()}
          color="text-purple-600 bg-purple-50"
          subtext={`${usage?.invocations_used || 0} / ${usage?.invocations_included || 0} used`}
        />
      </div>

      {/* Chart */}
      <div className="card p-6 mb-6">
        <h2 className="font-semibold text-zinc-900 mb-4">Invocations by agent</h2>
        {chartData.length === 0 ? (
          <p className="text-sm text-zinc-500 py-12 text-center">No data yet. Invoke some agents to see analytics.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#71717a" />
              <YAxis tick={{ fontSize: 12 }} stroke="#71717a" />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: "1px solid #e4e4e7",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="invocations" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Recent invocations */}
      <div className="card p-6">
        <h2 className="font-semibold text-zinc-900 mb-4">Recent invocations</h2>
        {invocations.length === 0 ? (
          <p className="text-sm text-zinc-500 py-8 text-center">
            No invocations yet. <Link href="/" className="text-brand-600 hover:underline">Browse agents</Link> to get started.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 uppercase tracking-wider">
                  <th className="py-2 pr-4">Agent</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Input</th>
                  <th className="py-2 pr-4">Duration</th>
                  <th className="py-2 pr-4">Cost</th>
                  <th className="py-2 pr-4">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {invocations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-zinc-50">
                    <td className="py-3 pr-4">
                      <Link href={`/agents/${inv.agent_id}`} className="text-brand-600 hover:underline">
                        {inv.agent_name || "deleted"}
                      </Link>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={
                        inv.status === "completed" ? "badge bg-green-100 text-green-700" :
                        inv.status === "failed" ? "badge bg-red-100 text-red-700" :
                        "badge bg-yellow-100 text-yellow-700"
                      }>
                        {inv.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 max-w-xs truncate text-zinc-600">{inv.input_message}</td>
                    <td className="py-3 pr-4 text-zinc-500">{inv.duration_ms ? `${inv.duration_ms}ms` : "-"}</td>
                    <td className="py-3 pr-4 text-zinc-700">{inv.cost_cents > 0 ? formatCents(inv.cost_cents) : "Free"}</td>
                    <td className="py-3 pr-4 text-zinc-500">{timeAgo(inv.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color, subtext }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  subtext?: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{label}</span>
        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold text-zinc-900">{value}</p>
      {subtext && <p className="text-xs text-zinc-500 mt-1">{subtext}</p>}
    </div>
  );
}
