import type { ReportSummary } from "@/lib/types";
import { round, usd } from "@/lib/plddt";

export default function SummaryRow({ s }: { s: ReportSummary }) {
  const cards = [
    {
      label: "Designs selected",
      value: `${s.designs_selected} / ${s.designs_total}`,
      hint: "of the full candidate pool",
    },
    {
      label: "Spend",
      value: usd(s.spend),
      hint: `of ${usd(s.budget)} budget`,
    },
    {
      label: "Distinct successes",
      value: round(s.expected_distinct_successes, 1),
      hint: `vs ${round(s.naive_expected_distinct_successes, 1)} naive · ${round(s.uplift_ratio, 1)}× more`,
      accent: true,
    },
    {
      label: "Cost per success",
      value: usd(s.cost_per_success),
      hint: "expected, fully loaded",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-line bg-surface p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-subtle">{c.label}</div>
          <div className={`mt-1.5 text-2xl font-semibold tracking-tight ${c.accent ? "text-accent" : "text-ink"}`}>
            {c.value}
          </div>
          <div className="mt-1 text-xs text-subtle">{c.hint}</div>
        </div>
      ))}
    </div>
  );
}
