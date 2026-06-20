"use client";

import { useState } from "react";
import InputView from "@/components/InputView";
import ReportView from "@/components/ReportView";
import { analyze } from "@/lib/api";
import type { AnalyzeRequest, Report } from "@/lib/types";

export default function Home() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [live, setLive] = useState(true);

  async function run(req: AnalyzeRequest) {
    setLoading(true);
    const { report, live } = await analyze(req);
    setReport(report);
    setLive(live);
    setLoading(false);
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <button
            onClick={() => setReport(null)}
            className="flex items-center gap-2 text-left"
            aria-label="Back to start"
          >
            <span className="h-2.5 w-2.5 rounded-full bg-accent" />
            <span className="text-sm font-semibold tracking-tight text-ink">DryRun</span>
            <span className="hidden text-sm text-subtle sm:inline">
              pre-synthesis experiment design
            </span>
          </button>
          {report && (
            <button
              onClick={() => setReport(null)}
              className="rounded-md border border-line px-3 py-1.5 text-sm text-ink transition hover:bg-canvas"
            >
              New analysis
            </button>
          )}
        </div>
      </header>

      {report ? (
        <ReportView report={report} live={live} />
      ) : (
        <InputView onSubmit={run} loading={loading} />
      )}
    </main>
  );
}
