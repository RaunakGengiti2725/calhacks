import type { CandidateRow } from "@/lib/types";
import { usd } from "@/lib/plddt";

export default function CandidateTable({ rows }: { rows: CandidateRow[] }) {
  const sorted = [...rows].sort((a, b) => b.success_probability - a.success_probability);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-subtle">
            <Th>Design</Th>
            <Th>Mutations</Th>
            <Th right>Viability</Th>
            <Th right>Fold pLDDT</Th>
            <Th right>Cost</Th>
            <Th right>Success p</Th>
            <Th center>Selected</Th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.design_id} className={`border-b border-line/60 ${r.selected ? "bg-accent/[0.03]" : ""}`}>
              <td className="py-2 pr-3 font-mono text-xs text-ink">{r.design_id}</td>
              <td className="py-2 pr-3">
                <span className="font-mono text-xs text-subtle">
                  {r.mutations.length ? r.mutations.join(" · ") : "—"}
                </span>
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink">{r.viability.toFixed(2)}</td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink">
                {r.fold_confidence != null ? r.fold_confidence.toFixed(0) : "—"}
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink">{usd(r.cost)}</td>
              <td className="py-2 pr-3 text-right tabular-nums font-medium text-ink">
                {r.success_probability.toFixed(2)}
              </td>
              <td className="py-2 text-center">
                {r.selected ? (
                  <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                    DryRun
                  </span>
                ) : r.selected_naive ? (
                  <span className="rounded-full bg-canvas px-2 py-0.5 text-xs text-subtle">naive</span>
                ) : (
                  <span className="text-subtle/50">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, right, center }: { children: React.ReactNode; right?: boolean; center?: boolean }) {
  return (
    <th className={`py-2 pr-3 font-medium ${right ? "text-right" : center ? "text-center" : "text-left"}`}>
      {children}
    </th>
  );
}
