"use client";

import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { SequenceSpacePoint } from "@/lib/types";

export default function SequenceSpaceScatter({ points }: { points: SequenceSpacePoint[] }) {
  const dryrun = points.filter((p) => p.selected_optimized);
  const naive = points.filter((p) => p.selected_naive && !p.selected_optimized);
  const other = points.filter((p) => !p.selected_optimized && !p.selected_naive);

  return (
    <div>
      <div className="h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#f1f1f1" />
            <XAxis type="number" dataKey="x" tick={false} axisLine={{ stroke: "#e5e7eb" }} label={{ value: "sequence-space dim 1", position: "insideBottom", offset: -2, fill: "#9ca3af", fontSize: 11 }} />
            <YAxis type="number" dataKey="y" tick={false} axisLine={{ stroke: "#e5e7eb" }} label={{ value: "dim 2", angle: -90, position: "insideLeft", fill: "#9ca3af", fontSize: 11 }} />
            <ZAxis type="number" dataKey="size" range={[60, 60]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as SequenceSpacePoint;
                return (
                  <div className="rounded-md border border-line bg-white px-2.5 py-1.5 text-xs shadow-sm">
                    <div className="font-mono text-ink">{p.design_id}</div>
                    <div className="text-subtle">p = {p.success_probability.toFixed(2)}</div>
                  </div>
                );
              }}
            />
            <Scatter name="Other candidates" data={other} fill="#d1d5db" />
            <Scatter name="Naive selection" data={naive} fill="#9ca3af" shape="circle" stroke="#6b7280" strokeWidth={2} />
            <Scatter name="DryRun selection" data={dryrun} fill="#2563eb" shape="circle" stroke="#1d4ed8" strokeWidth={2} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 flex flex-wrap gap-4 text-xs text-subtle">
        <Legend color="#d1d5db" label="other candidates" />
        <Legend color="#9ca3af" label="naive selection (clustered)" />
        <Legend color="#2563eb" label="DryRun selection (spread)" />
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
