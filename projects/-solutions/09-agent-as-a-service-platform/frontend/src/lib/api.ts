/**
 * API client — wraps fetch with JWT auth and error normalization.
 */
import type {
  Agent,
  Invocation,
  Token,
  UsageStats,
  User,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// -----------------------------------------------------------------------------
// Token storage (localStorage — fine for client-side demo; use httpOnly
// cookies in production)
// -----------------------------------------------------------------------------
const TOKEN_KEY = "a2a_token";
const USER_KEY = "a2a_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string, user: User): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getCurrentUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

// -----------------------------------------------------------------------------
// Fetch wrapper
// -----------------------------------------------------------------------------
export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!resp.ok) {
    let detail: unknown;
    try {
      detail = await resp.json();
    } catch {
      detail = await resp.text();
    }
    throw new ApiError(
      `API ${resp.status} on ${path}`,
      resp.status,
      detail
    );
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

// -----------------------------------------------------------------------------
// Auth
// -----------------------------------------------------------------------------
export const api = {
  async register(email: string, username: string, password: string, full_name?: string): Promise<Token> {
    return request<Token>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password, full_name }),
    });
  },

  async login(email: string, password: string): Promise<Token> {
    return request<Token>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async me(): Promise<User> {
    return request<User>("/auth/me");
  },

  // -------------------------------------------------------------------------
  // Agents
  // -------------------------------------------------------------------------
  async listAgents(query?: string): Promise<Agent[]> {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    return request<Agent[]>(`/agents${q}`);
  },

  async getAgent(id: string): Promise<Agent> {
    return request<Agent>(`/agents/${id}`);
  },

  async deployAgent(payload: {
    name: string;
    description: string;
    version: string;
    docker_image: string;
    price_per_invocation_cents: number;
    skills: Array<{ id: string; name: string; description: string; tags: string[] }>;
  }): Promise<{ agent: Agent; message: string }> {
    return request(`/agents`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async invokeAgent(id: string, message: string, skill_id?: string): Promise<{
    invocation_id: string;
    a2a_task_id: string | null;
    status: string;
    output: string;
    duration_ms: number | null;
    cost_cents: number;
  }> {
    return request(`/agents/${id}/invoke`, {
      method: "POST",
      body: JSON.stringify({ message, skill_id }),
    });
  },

  async rateAgent(id: string, score: number, review?: string): Promise<void> {
    return request(`/agents/${id}/ratings`, {
      method: "POST",
      body: JSON.stringify({ score, review }),
    });
  },

  async deleteAgent(id: string): Promise<void> {
    return request(`/agents/${id}`, { method: "DELETE" });
  },

  // -------------------------------------------------------------------------
  // Invocations
  // -------------------------------------------------------------------------
  async listInvocations(agentId?: string): Promise<Invocation[]> {
    const q = agentId ? `?agent_id=${agentId}` : "";
    return request<Invocation[]>(`/invocations${q}`);
  },

  // -------------------------------------------------------------------------
  // Billing / usage
  // -------------------------------------------------------------------------
  async getUsage(): Promise<UsageStats> {
    return request<UsageStats>("/billing/usage");
  },

  async createCheckout(plan: string): Promise<{ checkout_url: string; session_id: string }> {
    return request(`/billing/checkout?plan=${plan}`, { method: "POST" });
  },

  async upgradePlan(plan: string): Promise<{ status: string; plan: string }> {
    return request(`/billing/upgrade?plan=${plan}`, { method: "POST" });
  },
};
