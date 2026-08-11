"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;
const listeners: Array<(t: Toast) => void> = [];

export function toast(message: string, type: ToastType = "info") {
  const t: Toast = { id: ++toastId, type, message };
  listeners.forEach((l) => l(t));
}

export function Toaster() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (t: Toast) => {
      setToasts((prev) => [...prev, t]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== t.id));
      }, 5000);
    };
    listeners.push(listener);
    return () => {
      const i = listeners.indexOf(listener);
      if (i >= 0) listeners.splice(i, 1);
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-start gap-2 rounded-lg border px-4 py-3 shadow-lg max-w-sm",
            t.type === "success" && "border-green-200 bg-green-50 text-green-900",
            t.type === "error" && "border-red-200 bg-red-50 text-red-900",
            t.type === "info" && "border-zinc-200 bg-white text-zinc-900"
          )}
        >
          {t.type === "success" && <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />}
          {t.type === "error" && <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />}
          {t.type === "info" && <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />}
          <span className="text-sm">{t.message}</span>
          <button
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
            className="ml-auto -mr-1 text-zinc-400 hover:text-zinc-700"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
