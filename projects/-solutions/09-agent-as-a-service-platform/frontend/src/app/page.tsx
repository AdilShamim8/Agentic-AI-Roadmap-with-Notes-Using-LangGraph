"use client";

import { useEffect, useState } from "react";
import { Search, Sparkles, Server, Shield } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { AgentCard } from "@/components/AgentCard";
import type { Agent } from "@/types";

export default function HomePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listAgents(query);
        setAgents(data);
      } catch (e) {
        const err = e as ApiError;
        setError(
          err.status === 0
            ? "Cannot reach the API server. Is docker compose up running?"
            : err.message
        );
      } finally {
        setLoading(false);
      }
    };
    const t = setTimeout(load, 250); // debounce
    return () => clearTimeout(t);
  }, [query]);

  return (
    <div>
      {/* Hero */}
      <section className="border-b border-zinc-200 bg-gradient-to-b from-brand-50 to-white">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
              <Sparkles className="h-3.5 w-3.5" />
              A2A Protocol v0.3 · Agent Marketplace
            </div>
            <h1 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tight text-zinc-900">
              The <span className="text-brand-600">app store</span> for AI agents
            </h1>
            <p className="mt-4 max-w-2xl mx-auto text-lg text-zinc-600">
              Deploy, discover, and invoke agents through a unified A2A gateway.
              Per-invocation billing, ratings, and observability built in.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
            <FeatureCard
              icon={<Server className="h-5 w-5" />}
              title="Deploy in minutes"
              desc="Containerized agents, hot-swappable versions."
            />
            <FeatureCard
              icon={<Shield className="h-5 w-5" />}
              title="A2A-compliant"
              desc="Every agent serves /.well-known/agent.json."
            />
            <FeatureCard
              icon={<Sparkles className="h-5 w-5" />}
              title="Pay per call"
              desc="Stripe metered billing, transparent costs."
            />
          </div>
        </div>
      </section>

      {/* Browse */}
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <h2 className="text-2xl font-bold text-zinc-900">Browse agents</h2>
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <input
              type="search"
              placeholder="Search agents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input pl-9"
            />
          </div>
        </div>

        {loading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card p-5 animate-pulse">
                <div className="h-4 w-2/3 bg-zinc-200 rounded" />
                <div className="h-3 w-1/4 bg-zinc-200 rounded mt-2" />
                <div className="h-3 w-full bg-zinc-100 rounded mt-4" />
                <div className="h-3 w-3/4 bg-zinc-100 rounded mt-1" />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="card p-8 text-center">
            <p className="text-red-600 font-medium">Failed to load agents</p>
            <p className="text-sm text-zinc-600 mt-1">{error}</p>
          </div>
        )}

        {!loading && !error && agents.length === 0 && (
          <div className="card p-12 text-center">
            <p className="text-zinc-500">No agents deployed yet.</p>
            <a href="/deploy" className="btn-primary mt-4 inline-flex">
              Deploy your first agent
            </a>
          </div>
        )}

        {!loading && !error && agents.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((a) => (
              <AgentCard key={a.id} agent={a} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-zinc-900">{title}</h3>
          <p className="text-xs text-zinc-500">{desc}</p>
        </div>
      </div>
    </div>
  );
}
