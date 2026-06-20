import type { StructurePayload } from "@/lib/types";
import { plddtColor } from "@/lib/plddt";

export default function ConfidenceTrack({ structure }: { structure: StructurePayload }) {
  const { plddt, mutation_positions, low_confidence_regions } = structure;
  const n = plddt.length;
  const width = 520;
  const height = 46;
  const cellW = width / Math.max(n, 1);
  const muts = new Set(mutation_positions);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h4 className="text-sm font-medium text-ink">Per-residue confidence</h4>
        <span className="text-xs text-subtle">
          mean pLDDT {structure.mean_plddt.toFixed(0)}
          {structure.misfold_flag && (
            <span className="ml-2 rounded-full bg-warn/10 px-2 py-0.5 text-warn">misfold risk</span>
          )}
        </span>
      </div>

      <svg viewBox={`0 0 ${width} ${height + 22}`} className="mt-2 w-full" role="img" aria-label="confidence track">
        {/* low-confidence region underlays */}
        {low_confidence_regions.map(([s, e], i) => (
          <rect
            key={`lc-${i}`}
            x={(s - 1) * cellW}
            y={0}
            width={(e - s + 1) * cellW}
            height={height}
            fill="#ff7d45"
            opacity={0.12}
          />
        ))}
        {/* per-residue confidence cells */}
        {plddt.map((v, i) => (
          <rect key={i} x={i * cellW} y={6} width={Math.max(cellW - 0.3, 0.6)} height={height - 12} fill={plddtColor(v)} />
        ))}
        {/* mutation markers */}
        {Array.from(muts).map((p) => (
          <g key={`m-${p}`}>
            <rect x={(p - 1) * cellW - 0.5} y={2} width={Math.max(cellW, 1.5)} height={height - 4} fill="none" stroke="#111827" strokeWidth={1.2} />
            <polygon
              points={`${(p - 0.5) * cellW - 3},${height + 2} ${(p - 0.5) * cellW + 3},${height + 2} ${(p - 0.5) * cellW},${height + 8}`}
              fill="#111827"
            />
          </g>
        ))}
        {/* residue axis ticks */}
        <text x={0} y={height + 19} fontSize={9} fill="#9ca3af">1</text>
        <text x={width} y={height + 19} fontSize={9} fill="#9ca3af" textAnchor="end">{n}</text>
      </svg>

      <p className="mt-1 text-xs text-subtle">
        Black markers show introduced mutations; shaded bands are low-confidence regions.
      </p>
    </div>
  );
}
