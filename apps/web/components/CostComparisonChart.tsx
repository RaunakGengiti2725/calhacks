"use client";

import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import type { Report } from "@/lib/types";
import { usd } from "@/lib/plddt";

export default function CostComparisonChart({ report }: { report: Report }) {
  const { summary, comparison } = report;
  const data = [
    { name: "Naive top-N", value: summary.naive_expected_distinct_successes, fill: "#9ca3af" },
    { name: "DryRun", value: summary.expected_distinct_successes, fill: "#2563eb" },
  ];
  const dollars = comparison.dollars_naive_needs_to_match;

  return (
    <div>
      <div className="h-[220px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 48, top: 8, bottom: 8 }}>
            <XAxis type="number" hide domain={[0, "dataMax + 0.6"]} />
            <YAxis
              type="category"
              dataKey="name"
              width={92}
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#111827", fontSize: 13 }}
            />
            <Bar dataKey="value" radius={[4, 4, 4, 4]} barSize={42}>
              {data.map((d) => (
                <Cell key={d.name} fill={d.fill} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v: number) => v.toFixed(1)}
                style={{ fill: "#111827", fontSize: 13, fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 rounded-lg bg-canvas px-4 py-3 text-sm text-ink">
        Both portfolios cost the same{" "}
        <span className="font-semibold">{usd(summary.spend)}</span>. To reach DryRun&apos;s{" "}
        <span className="font-semibold">{summary.expected_distinct_successes.toFixed(1)}</span> distinct
        successes, the naive ordering would need{" "}
        <span className="font-semibold text-accent">
          {dollars != null ? usd(dollars) : "far more budget"}
        </span>
        {dollars != null && (
          <>
            {" "}— about{" "}
            <span className="font-semibold">{(dollars / Math.max(summary.spend, 1)).toFixed(1)}×</span>{" "}
            the spend.
          </>
        )}
      </div>
    </div>
  );
}
