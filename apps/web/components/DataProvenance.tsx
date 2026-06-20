import type { ProviderStatus, ReportMeta } from "@/lib/types";

// Human labels + the real backend behind each tracked stage.
const STAGE_LABELS: Record<string, string> = {
  generation: "Generation · Evo 2",
  viability: "Viability · Evo 2",
  structure: "Structure · AlphaFold2",
  llm: "Summary · ASI:One",
  cost: "Cost · model",
};

const STAGE_ORDER = ["generation", "viability", "structure", "cost", "llm"];

const STATUS_STYLE: Record<ProviderStatus, { dot: string; text: string; label: string; title: string }> = {
  live: {
    dot: "bg-emerald-500",
    text: "text-emerald-700",
    label: "live",
    title: "Real external API returned this stage's result.",
  },
  fallback: {
    dot: "bg-amber-500",
    text: "text-amber-700",
    label: "fallback",
    title: "Live was requested but the call failed — mock data was substituted (not a real API result).",
  },
  mock: {
    dot: "bg-zinc-400",
    text: "text-zinc-500",
    label: "mock",
    title: "Mock mode — deterministic synthetic data, by design (no live call attempted).",
  },
  local: {
    dot: "bg-sky-500",
    text: "text-sky-700",
    label: "local model",
    title: "A real in-process algorithm (not an external API, not a mock fallback).",
  },
};

/** Honest per-stage data provenance. Renders exactly what produced each stage's
 *  numbers — a fallback can never be displayed as a real API result. */
export default function DataProvenance({ meta }: { meta: ReportMeta }) {
  const providers = meta.providers ?? {};
  const stages = STAGE_ORDER.filter((s) => s in providers);
  if (stages.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {stages.map((stage) => {
        const status = providers[stage];
        const style = STATUS_STYLE[status] ?? STATUS_STYLE.mock;
        return (
          <span
            key={stage}
            title={`${STAGE_LABELS[stage] ?? stage}: ${style.title}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs"
          >
            <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
            <span className="text-subtle">{STAGE_LABELS[stage] ?? stage}</span>
            <span className={`font-medium ${style.text}`}>{style.label}</span>
          </span>
        );
      })}
      {meta.strict && (
        <span
          title="DRYRUN_STRICT is on: a live failure raises instead of silently using mock."
          className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
        >
          strict
        </span>
      )}
    </div>
  );
}
