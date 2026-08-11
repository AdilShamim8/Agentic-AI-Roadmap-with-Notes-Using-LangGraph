"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getCurrentUser, clearToken, type ApiError } from "@/lib/api";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, full_name?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = getCurrentUser();
    if (stored) {
      setUser(stored);
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const token = await api.login(email, password);
    setUser(token.user);
    // Token is stored inside api.login via setToken
    const { setToken } = await import("@/lib/api");
    setToken(token.access_token, token.user);
  };

  const register = async (
    email: string,
    username: string,
    password: string,
    full_name?: string
  ) => {
    const token = await api.register(email, username, password, full_name);
    setUser(token.user);
    const { setToken } = await import("@/lib/api");
    setToken(token.access_token, token.user);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
