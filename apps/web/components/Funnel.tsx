import type { FunnelCounts } from "@/lib/types";

export default function Funnel({ funnel }: { funnel: FunnelCounts }) {
  const stages = [
    { label: "Generated", count: funnel.generated, note: "candidate variants", tone: "ink" },
    { label: "Viability passed", count: funnel.viability_passed, note: "cheap filter · whole pool", tone: "ink" },
    { label: "Fold passed", count: funnel.fold_passed, note: "expensive fold · survivors only", tone: "warn" },
    { label: "Selected", count: funnel.selected, note: "portfolio · budget-optimized", tone: "accent" },
  ];
  const max = Math.max(funnel.generated, 1);

  return (
    <div className="space-y-2.5">
      {stages.map((s, i) => {
        const pct = (s.count / max) * 100;
        const dropped = i > 0 ? stages[i - 1].count - s.count : 0;
        const color =
          s.tone === "accent" ? "#2563eb" : s.tone === "warn" ? "#d97706" : "#374151";
        return (
          <div key={s.label}>
            <div className="flex items-baseline justify-between text-sm">
              <span className="font-medium text-ink">{s.label}</span>
              <span className="tabular-nums font-semibold text-ink">{s.count}</span>
            </div>
            <div className="mt-1 h-7 w-full overflow-hidden rounded-md bg-canvas">
              <div
                className="flex h-full items-center rounded-md transition-all"
                style={{ width: `${Math.max(pct, 6)}%`, background: color }}
              />
            </div>
            <div className="mt-0.5 flex items-center justify-between text-xs text-subtle">
              <span>{s.note}</span>
              {dropped > 0 && <span>−{dropped} dropped</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
