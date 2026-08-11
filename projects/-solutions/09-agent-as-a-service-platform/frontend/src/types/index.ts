/**
 * Shared TypeScript types — mirror the backend Pydantic schemas.
 */

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AgentSkill {
  id: string;
  name: string;
  description: string;
  tags: string[];
  input_modes: string[];
  output_modes: string[];
}

export interface AgentCard {
  schema_version: string;
  name: string;
  description: string;
  version: string;
  url: string;
  protocol_version: string;
  capabilities: Record<string, unknown>;
  default_input_modes: string[];
  default_output_modes: string[];
  skills: AgentSkill[];
  authentication: Record<string, unknown>;
  provider: Record<string, unknown>;
}

export interface Agent {
  id: string;
  name: string;
  slug: string;
  description: string;
  version: string;
  docker_image: string;
  status: "pending" | "deploying" | "running" | "stopped" | "failed" | "undeployed";
  base_url: string | null;
  price_per_invocation_cents: number;
  invocations_count: number;
  avg_rating: number;
  agent_card: Record<string, unknown>;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Invocation {
  id: string;
  agent_id: string;
  agent_name: string | null;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  a2a_task_id: string | null;
  input_message: string;
  output_message: string;
  duration_ms: number | null;
  cost_cents: number;
  created_at: string;
}

export interface UsageStats {
  total_invocations: number;
  total_cost_cents: number;
  invocations_this_month: number;
  cost_this_month_cents: number;
  plan: string;
  invocations_used: number;
  invocations_included: number;
  by_agent: Array<{
    agent_id: string;
    name: string;
    count: number;
    cost_cents: number;
  }>;
}

export interface Rating {
  id: string;
  agent_id: string;
  user_id: string;
  score: number;
  review: string | null;
  created_at: string;
}
