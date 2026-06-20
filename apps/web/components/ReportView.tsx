"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { Report } from "@/lib/types";
import SummaryRow from "@/components/SummaryRow";
import CostComparisonChart from "@/components/CostComparisonChart";
import Funnel from "@/components/Funnel";
import SequenceSpaceScatter from "@/components/SequenceSpaceScatter";
import ConfidenceTrack from "@/components/ConfidenceTrack";
import CandidateTable from "@/components/CandidateTable";
import { PLDDT_LEGEND } from "@/lib/plddt";

// Mol* is WebGL/DOM-only — load client-side, never during SSR.
const MolViewer = dynamic(() => import("@/components/MolViewer"), {
  ssr: false,
  loading: () => <div className="grid h-[360px] place-items-center text-sm text-subtle">Loading 3D viewer…</div>,
});

export default function ReportView({ report, live }: { report: Report; live: boolean }) {
  const { structures, wild_type_structure } = report;
  const [activeIdx, setActiveIdx] = useState(0);
  const [showWildType, setShowWildType] = useState(false);

  const variant = structures[activeIdx] ?? wild_type_structure ?? null;
  const active = showWildType ? wild_type_structure ?? variant : variant;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {/* heading + plain-English summary */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-ink">
            {report.meta.goal ?? "Design analysis"}
          </h2>
          <p className="mt-1 text-sm text-subtle">
            {report.meta.candidate_count} candidates · seed {report.meta.seed_length} aa ·{" "}
            <span className="font-mono text-xs">{report.meta.mode} mode</span>
          </p>
        </div>
        {!live && (
          <span className="rounded-full border border-line bg-canvas px-3 py-1 text-xs text-subtle">
            offline · bundled mock report
          </span>
        )}
      </div>

      <p className="mt-4 max-w-3xl text-[15px] leading-relaxed text-ink">{report.plain_summary}</p>

      <div className="mt-6">
        <SummaryRow s={report.summary} />
      </div>

      {/* cost comparison + funnel */}
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-5">
        <Panel className="lg:col-span-3" title="Expected successes per dollar"
          subtitle="Distinct functional approaches covered at the same budget (diversity-adjusted).">
          <CostComparisonChart report={report} />
        </Panel>
        <Panel className="lg:col-span-2" title="Screening cascade"
          subtitle="Cheap viability filter runs on the whole pool; expensive folding only on survivors.">
          <Funnel funnel={report.funnel} />
        </Panel>
      </div>

      {/* 3D structure + confidence track */}
      <Panel
        className="mt-6"
        title="Predicted structure & confidence"
        subtitle="Colored by per-residue pLDDT. Predicts structure/confidence, not stability directly — low confidence flags structural risk."
      >
        {structures.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap gap-1.5">
              {structures.map((s, i) => (
                <button
                  key={s.design_id}
                  onClick={() => setActiveIdx(i)}
                  className={`rounded-md border px-2.5 py-1 font-mono text-xs transition ${
                    i === activeIdx && !showWildType
                      ? "border-accent bg-accent/5 text-accent"
                      : "border-line text-subtle hover:bg-canvas"
                  }`}
                >
                  {s.design_id}
                </button>
              ))}
            </div>
            <div className="ml-auto inline-flex overflow-hidden rounded-md border border-line text-xs">
              <Toggle on={!showWildType} onClick={() => setShowWildType(false)}>
                Variant
              </Toggle>
              <Toggle on={showWildType} onClick={() => setShowWildType(true)}>
                Wild type
              </Toggle>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="overflow-hidden rounded-lg border border-line bg-canvas">
            {active && (
              <MolViewer
                key={`${active.design_id}-${showWildType}`}
                pdb={active.pdb}
                mutationPositions={showWildType ? [] : active.mutation_positions}
              />
            )}
          </div>
          <div className="flex flex-col justify-between">
            {active && <ConfidenceTrack structure={active} />}
            <div className="mt-4 flex flex-wrap gap-3">
              {PLDDT_LEGEND.map((l) => (
                <div key={l.label} className="flex items-center gap-1.5 text-xs text-subtle">
                  <span className="h-3 w-3 rounded-sm" style={{ background: l.color }} />
                  {l.label} <span className="text-subtle/70">({l.range})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Panel>

      {/* sequence-space scatter */}
      <Panel
        className="mt-6"
        title="Sequence-space map"
        subtitle="Every candidate projected to 2D. Naive piles into one region; DryRun spreads across distinct ones."
      >
        <SequenceSpaceScatter points={report.sequence_space} />
      </Panel>

      {/* candidate table */}
      <Panel className="mt-6" title="All candidates" subtitle={`${report.candidates.length} designs scored.`}>
        <CandidateTable rows={report.candidates} />
      </Panel>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  className = "",
  children,
}: {
  title: string;
  subtitle?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-5 ${className}`}>
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-subtle">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Toggle({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 transition ${on ? "bg-accent text-white" : "text-subtle hover:bg-canvas"}`}
    >
      {children}
    </button>
  );
}
