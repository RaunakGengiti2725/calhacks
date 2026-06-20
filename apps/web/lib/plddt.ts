// The standard AlphaFold per-residue confidence (pLDDT) color scale.
//   > 90        very high   dark blue
//   70 – 90     confident   light blue
//   50 – 70     low         yellow
//   < 50        very low    orange

export function plddtColor(v: number): string {
  if (v >= 90) return "#0053d6";
  if (v >= 70) return "#65cbf3";
  if (v >= 50) return "#ffdb13";
  return "#ff7d45";
}

export const PLDDT_LEGEND: { label: string; color: string; range: string }[] = [
  { label: "Very high", color: "#0053d6", range: "> 90" },
  { label: "Confident", color: "#65cbf3", range: "70–90" },
  { label: "Low", color: "#ffdb13", range: "50–70" },
  { label: "Very low", color: "#ff7d45", range: "< 50" },
];

export function round(n: number, dp = 0): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export function usd(n: number): string {
  return "$" + round(n, 0);
}
