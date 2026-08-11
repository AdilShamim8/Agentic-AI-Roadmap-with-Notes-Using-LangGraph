"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Rocket, Plus, Trash } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { toast } from "@/components/Toaster";
import { cn } from "@/lib/utils";

interface SkillForm {
  id: string;
  name: string;
  description: string;
  tags: string;
}

export default function DeployPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("0.1.0");
  const [dockerImage, setDockerImage] = useState("");
  const [priceCents, setPriceCents] = useState(0);
  const [skills, setSkills] = useState<SkillForm[]>([
    { id: "default", name: "Default", description: "Default skill", tags: "" },
  ]);
  const [submitting, setSubmitting] = useState(false);

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <h1 className="text-2xl font-bold text-zinc-900">Deploy an agent</h1>
        <p className="mt-2 text-zinc-600">You need to be signed in to deploy agents.</p>
        <a href="/login" className="btn-primary mt-4 inline-flex">Sign in</a>
      </div>
    );
  }

  const addSkill = () => {
    setSkills((prev) => [
      ...prev,
      { id: `skill-${prev.length + 1}`, name: "", description: "", tags: "" },
    ]);
  };

  const removeSkill = (idx: number) => {
    setSkills((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateSkill = (idx: number, field: keyof SkillForm, value: string) => {
    setSkills((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s))
    );
  };

  const submit = async () => {
    if (!name || !dockerImage) {
      toast("Name and Docker image are required", "error");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.deployAgent({
        name,
        description,
        version,
        docker_image: dockerImage,
        price_per_invocation_cents: priceCents,
        skills: skills
          .filter((s) => s.id && s.name)
          .map((s) => ({
            id: s.id,
            name: s.name,
            description: s.description,
            tags: s.tags.split(",").map((t) => t.trim()).filter(Boolean),
          })),
      });
      toast("Agent deployment started", "success");
      router.push(`/agents/${result.agent.id}`);
    } catch (e) {
      const err = e as ApiError;
      toast(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
          <Rocket className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Deploy an agent</h1>
          <p className="text-sm text-zinc-500">Register a new A2A-compliant agent on the platform.</p>
        </div>
      </div>

      <div className="card p-6 space-y-4">
        <Field label="Agent name" required>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Weather Forecaster"
            className="input"
          />
        </Field>

        <Field label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this agent do?"
            rows={3}
            className="input resize-none"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Version">
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="0.1.0"
              className="input"
            />
          </Field>
          <Field label="Price per invocation (cents)">
            <input
              type="number"
              min={0}
              value={priceCents}
              onChange={(e) => setPriceCents(Number(e.target.value))}
              className="input"
            />
          </Field>
        </div>

        <Field label="Docker image" required>
          <input
            value={dockerImage}
            onChange={(e) => setDockerImage(e.target.value)}
            placeholder="e.g. ghcr.io/myorg/weather-agent:latest"
            className="input font-mono text-sm"
          />
          <p className="text-xs text-zinc-500 mt-1">
            The image must expose an A2A-compatible server on port 8080 and serve
            <code className="mx-1 px-1 py-0.5 bg-zinc-100 rounded">/.well-known/agent.json</code>
          </p>
        </Field>

        {/* Skills */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-zinc-900">Skills</label>
            <button onClick={addSkill} className="btn-ghost text-xs">
              <Plus className="h-3 w-3" /> Add skill
            </button>
          </div>
          <div className="space-y-3">
            {skills.map((s, idx) => (
              <div key={idx} className="border border-zinc-200 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    value={s.id}
                    onChange={(e) => updateSkill(idx, "id", e.target.value)}
                    placeholder="skill_id"
                    className="input flex-1 font-mono text-xs"
                  />
                  <input
                    value={s.name}
                    onChange={(e) => updateSkill(idx, "name", e.target.value)}
                    placeholder="Display name"
                    className="input flex-1"
                  />
                  <button onClick={() => removeSkill(idx)} className="btn-ghost text-red-600">
                    <Trash className="h-4 w-4" />
                  </button>
                </div>
                <input
                  value={s.description}
                  onChange={(e) => updateSkill(idx, "description", e.target.value)}
                  placeholder="Description"
                  className="input text-sm"
                />
                <input
                  value={s.tags}
                  onChange={(e) => updateSkill(idx, "tags", e.target.value)}
                  placeholder="tags, comma-separated"
                  className="input text-sm"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-200">
          <button onClick={() => router.back()} className="btn-ghost">Cancel</button>
          <button onClick={submit} disabled={submitting} className="btn-primary">
            <Rocket className="h-4 w-4" />
            {submitting ? "Deploying..." : "Deploy agent"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-zinc-900 mb-1">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
    </div>
  );
}
