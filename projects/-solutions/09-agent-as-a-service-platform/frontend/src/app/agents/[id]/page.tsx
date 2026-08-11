"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Zap,
  Star,
  Send,
  Clock,
  DollarSign,
  Code,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { toast } from "@/components/Toaster";
import { formatNumber, formatCents, formatDate, cn } from "@/lib/utils";
import type { Agent, Rating } from "@/types";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);

  // Invocation form state
  const [message, setMessage] = useState("");
  const [skillId, setSkillId] = useState<string>("");
  const [invoking, setInvoking] = useState(false);
  const [result, setResult] = useState<{
    output: string;
    duration_ms: number | null;
    cost_cents: number;
  } | null>(null);

  // Rating form
  const [myScore, setMyScore] = useState(5);
  const [myReview, setMyReview] = useState("");

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const [a, r] = await Promise.all([
          api.getAgent(id),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/agents/${id}/ratings`).then((x) => x.json()),
        ]);
        setAgent(a);
        setRatings(r);
        const skills = (a.agent_card as { skills?: Array<{ id: string }> }).skills || [];
        if (skills.length > 0) setSkillId(skills[0].id);
      } catch (e) {
        toast((e as ApiError).message, "error");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const invoke = async () => {
    if (!agent) return;
    if (!user) {
      toast("Please sign in to invoke agents", "error");
      return;
    }
    if (!message.trim()) {
      toast("Enter a message to send", "error");
      return;
    }
    setInvoking(true);
    setResult(null);
    try {
      const r = await api.invokeAgent(agent.id, message, skillId || undefined);
      setResult({
        output: r.output,
        duration_ms: r.duration_ms,
        cost_cents: r.cost_cents,
      });
      toast("Invocation completed", "success");
    } catch (e) {
      const err = e as ApiError;
      toast(err.message, "error");
    } finally {
      setInvoking(false);
    }
  };

  const submitRating = async () => {
    if (!agent) return;
    try {
      await api.rateAgent(agent.id, myScore, myReview || undefined);
      toast("Rating submitted", "success");
      setMyReview("");
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/agents/${agent.id}/ratings`
      ).then((x) => x.json());
      setRatings(r);
    } catch (e) {
      toast((e as ApiError).message, "error");
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="card p-8 animate-pulse">
          <div className="h-6 w-1/3 bg-zinc-200 rounded" />
          <div className="h-4 w-1/4 bg-zinc-100 rounded mt-3" />
          <div className="h-3 w-full bg-zinc-100 rounded mt-6" />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 text-center">
        <p className="text-zinc-500">Agent not found.</p>
        <Link href="/" className="btn-secondary mt-4 inline-flex">Back to browse</Link>
      </div>
    );
  }

  const skills = (agent.agent_card as { skills?: Array<{ id: string; name: string; description: string }> }).skills || [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 mb-4">
        <ArrowLeft className="h-4 w-4" /> Back to browse
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">{agent.name}</h1>
            <p className="text-sm text-zinc-500 mt-1">v{agent.version} · {agent.slug}</p>
          </div>
          <span className={cn(
            "badge",
            agent.status === "running" ? "bg-green-100 text-green-700" : "bg-zinc-100 text-zinc-600"
          )}>
            {agent.status}
          </span>
        </div>

        <p className="mt-4 text-zinc-700">{agent.description || "No description provided."}</p>

        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat icon={<Zap className="h-4 w-4" />} label="Invocations" value={formatNumber(agent.invocations_count)} />
          <Stat icon={<Star className="h-4 w-4" />} label="Rating" value={agent.avg_rating.toFixed(1)} />
          <Stat icon={<DollarSign className="h-4 w-4" />} label="Per call" value={agent.price_per_invocation_cents === 0 ? "Free" : formatCents(agent.price_per_invocation_cents)} />
          <Stat icon={<Clock className="h-4 w-4" />} label="Deployed" value={formatDate(agent.created_at)} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoke panel */}
        <div className="card p-6">
          <h2 className="font-semibold text-zinc-900 mb-4">Try this agent</h2>

          {skills.length > 0 && (
            <div className="mb-4">
              <label className="block text-xs font-medium text-zinc-700 mb-1">Skill</label>
              <select value={skillId} onChange={(e) => setSkillId(e.target.value)} className="input">
                {skills.map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
              </select>
              <p className="text-xs text-zinc-500 mt-1">{skills.find((s) => s.id === skillId)?.description}</p>
            </div>
          )}

          <label className="block text-xs font-medium text-zinc-700 mb-1">Message</label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask the agent something..."
            rows={4}
            className="input resize-none font-mono text-sm"
          />

          <button
            onClick={invoke}
            disabled={invoking || !user || agent.status !== "running"}
            className="btn-primary w-full mt-3"
          >
            <Send className="h-4 w-4" />
            {invoking ? "Invoking..." : "Invoke agent"}
          </button>

          {!user && (
            <p className="text-xs text-zinc-500 mt-2">
              <Link href="/login" className="text-brand-600 hover:underline">Sign in</Link> to invoke agents.
            </p>
          )}
          {agent.status !== "running" && (
            <p className="text-xs text-yellow-600 mt-2">Agent is currently {agent.status}. Try again later.</p>
          )}

          {result && (
            <div className="mt-4 border-t border-zinc-200 pt-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-zinc-900">Response</h3>
                <div className="flex items-center gap-3 text-xs text-zinc-500">
                  {result.duration_ms !== null && <span>{result.duration_ms}ms</span>}
                  {result.cost_cents > 0 && <span>{formatCents(result.cost_cents)}</span>}
                </div>
              </div>
              <pre className="bg-zinc-900 text-zinc-100 rounded-lg p-4 text-xs font-mono whitespace-pre-wrap break-words max-h-80 overflow-auto">
                {result.output}
              </pre>
            </div>
          )}
        </div>

        {/* Agent card preview */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-zinc-900">Agent Card</h2>
            {agent.base_url && (
              <a
                href={`${agent.base_url}/.well-known/agent.json`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-brand-600 hover:underline inline-flex items-center gap-1"
              >
                <ExternalLink className="h-3 w-3" /> View raw
              </a>
            )}
          </div>
          <pre className="bg-zinc-50 rounded-lg p-4 text-xs font-mono overflow-auto max-h-96 border border-zinc-200">
{JSON.stringify(agent.agent_card, null, 2)}
          </pre>
        </div>
      </div>

      {/* Skills */}
      {skills.length > 0 && (
        <div className="card p-6 mt-6">
          <h2 className="font-semibold text-zinc-900 mb-4">Skills</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {skills.map((s) => (
              <div key={s.id} className="border border-zinc-200 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <Code className="h-4 w-4 text-brand-600" />
                  <span className="font-mono text-sm font-medium">{s.id}</span>
                </div>
                <p className="text-xs text-zinc-600 mt-1">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ratings */}
      <div className="card p-6 mt-6">
        <h2 className="font-semibold text-zinc-900 mb-4">Ratings ({ratings.length})</h2>

        {user && (
          <div className="border border-zinc-200 rounded-lg p-4 mb-4">
            <h3 className="text-sm font-medium text-zinc-900 mb-2">Rate this agent</h3>
            <div className="flex items-center gap-1 mb-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} onClick={() => setMyScore(n)} className="p-0.5" aria-label={`${n} stars`}>
                  <Star className={cn("h-5 w-5", n <= myScore ? "fill-yellow-400 text-yellow-400" : "text-zinc-300")} />
                </button>
              ))}
            </div>
            <textarea
              value={myReview}
              onChange={(e) => setMyReview(e.target.value)}
              placeholder="Optional review..."
              rows={2}
              className="input resize-none text-sm"
            />
            <button onClick={submitRating} className="btn-secondary mt-2 text-sm">Submit rating</button>
          </div>
        )}

        {ratings.length === 0 ? (
          <p className="text-sm text-zinc-500">No ratings yet. Be the first!</p>
        ) : (
          <ul className="space-y-3">
            {ratings.map((r) => (
              <li key={r.id} className="border-b border-zinc-100 pb-3 last:border-0">
                <div className="flex items-center gap-2">
                  <div className="flex">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star key={i} className={cn("h-3.5 w-3.5", i < r.score ? "fill-yellow-400 text-yellow-400" : "text-zinc-300")} />
                    ))}
                  </div>
                  <span className="text-xs text-zinc-500">{formatDate(r.created_at)}</span>
                </div>
                {r.review && <p className="text-sm text-zinc-700 mt-1">{r.review}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="border border-zinc-200 rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-xs text-zinc-500">
        {icon}
        {label}
      </div>
      <p className="mt-1 font-semibold text-zinc-900">{value}</p>
    </div>
  );
}
