"use client";

import { useState } from "react";
import type { AnalyzeRequest } from "@/lib/types";

const DEMO_SEED = "TTCCPSIVARSNFNVCRLPGTPEAICATYTGCIIIPGATCPGDYAN";

export default function InputView({
  onSubmit,
  loading,
}: {
  onSubmit: (req: AnalyzeRequest) => void;
  loading: boolean;
}) {
  const [natural, setNatural] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [seed, setSeed] = useState("");
  const [goal, setGoal] = useState("");
  const [budget, setBudget] = useState("");
  const [candidates, setCandidates] = useState("");

  function submit() {
    if (loading) return;
    onSubmit({
      natural: natural.trim() || undefined,
      seed: seed.trim() || undefined,
      goal: goal.trim() || undefined,
      budget: budget ? Number(budget) : undefined,
      candidates: candidates ? Number(candidates) : undefined,
    });
  }

  function runDemo() {
    if (loading) return;
    onSubmit({
      seed: DEMO_SEED,
      goal: "improve thermal stability",
      budget: 500,
      candidates: 20,
    });
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">
        Which designs should you actually pay to synthesize?
      </h1>
      <p className="mt-3 text-[15px] leading-relaxed text-subtle">
        Most engineered proteins fail, and ordering near-identical variants concentrates risk
        rather than reducing it. Describe what you want to test and your budget — DryRun scores
        every candidate, folds only the survivors, and picks the portfolio that maximizes
        uncorrelated successes per dollar.
      </p>

      <div className="mt-8 rounded-xl border border-line bg-surface p-5">
        <label className="text-sm font-medium text-ink">Describe what you want to test</label>
        <textarea
          value={natural}
          onChange={(e) => setNatural(e.target.value)}
          rows={3}
          placeholder="Improve the thermal stability of my protein. I have about $500 to spend and want to consider 20 variants."
          className="mt-2 w-full resize-none rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] text-ink outline-none placeholder:text-subtle/70 focus:border-accent"
        />

        <button
          onClick={() => setShowAdvanced((s) => !s)}
          className="mt-3 text-sm text-accent hover:underline"
        >
          {showAdvanced ? "Hide" : "Add"} explicit fields
        </button>

        {showAdvanced && (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Seed sequence" full>
              <input
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder={DEMO_SEED}
                className="w-full rounded-lg border border-line bg-white px-3 py-2 font-mono text-xs text-ink outline-none focus:border-accent"
              />
            </Field>
            <Field label="Goal">
              <input
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="improve thermal stability"
                className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              />
            </Field>
            <Field label="Budget (USD)">
              <input
                value={budget}
                onChange={(e) => setBudget(e.target.value.replace(/[^0-9.]/g, ""))}
                inputMode="numeric"
                placeholder="500"
                className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              />
            </Field>
            <Field label="Candidate count">
              <input
                value={candidates}
                onChange={(e) => setCandidates(e.target.value.replace(/[^0-9]/g, ""))}
                inputMode="numeric"
                placeholder="20"
                className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              />
            </Field>
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={submit}
            disabled={loading}
            className="rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Analyzing…" : "Analyze designs"}
          </button>
          <button
            onClick={runDemo}
            disabled={loading}
            className="text-sm text-subtle transition hover:text-ink disabled:opacity-60"
          >
            or run the crambin demo
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  full,
  children,
}: {
  label: string;
  full?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={full ? "sm:col-span-2" : ""}>
      <label className="text-xs font-medium uppercase tracking-wide text-subtle">{label}</label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
