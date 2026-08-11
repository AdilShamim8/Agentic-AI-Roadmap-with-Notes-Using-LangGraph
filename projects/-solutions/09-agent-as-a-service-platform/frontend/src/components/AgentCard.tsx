import Link from "next/link";
import { Star, Zap, Activity } from "lucide-react";
import type { Agent } from "@/types";
import { formatNumber, formatCents, cn } from "@/lib/utils";

const STATUS_STYLES: Record<Agent["status"], string> = {
  running: "bg-green-100 text-green-700",
  pending: "bg-yellow-100 text-yellow-700",
  deploying: "bg-blue-100 text-blue-700",
  stopped: "bg-zinc-100 text-zinc-700",
  failed: "bg-red-100 text-red-700",
  undeployed: "bg-zinc-100 text-zinc-500",
};

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Link href={`/agents/${agent.id}`} className="group">
      <div className="card p-5 h-full transition-all hover:shadow-md hover:border-brand-300">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-zinc-900 truncate group-hover:text-brand-700">
              {agent.name}
            </h3>
            <p className="text-xs text-zinc-500 mt-0.5">v{agent.version}</p>
          </div>
          <span className={cn("badge", STATUS_STYLES[agent.status])}>
            {agent.status}
          </span>
        </div>

        <p className="mt-3 text-sm text-zinc-600 line-clamp-2 min-h-[2.5rem]">
          {agent.description || "No description provided."}
        </p>

        <div className="mt-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-3 text-zinc-500">
            <span className="flex items-center gap-1">
              <Zap className="h-3.5 w-3.5" />
              {formatNumber(agent.invocations_count)}
            </span>
            <span className="flex items-center gap-1">
              <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
              {agent.avg_rating.toFixed(1)}
            </span>
          </div>
          <span className="font-medium text-zinc-700">
            {agent.price_per_invocation_cents === 0
              ? "Free"
              : formatCents(agent.price_per_invocation_cents) + "/call"}
          </span>
        </div>
      </div>
    </Link>
  );
}
