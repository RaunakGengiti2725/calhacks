import type { AnalyzeRequest, Report } from "./types";
import mockReport from "./mockReport.json";

const API_URL = process.env.NEXT_PUBLIC_DRYRUN_API_URL || "http://localhost:8000";

/** The bundled mock report — used as a fallback so the UI always renders, even
 *  with no API running. This is what makes the frontend fully demoable in mock
 *  mode without any backend or credentials. */
export const fallbackReport = mockReport as unknown as Report;

async function withTimeout(input: string, init: RequestInit, ms: number): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

/** `reachedApi` is whether the live backend actually answered. It is NOT a claim
 *  that the data is from real external APIs — that truth lives, per stage, in
 *  `report.meta.providers` (live | fallback | mock | local). When the backend is
 *  unreachable we render the bundled mock report so the UI never breaks, and
 *  `reachedApi=false` makes that explicit. */
export async function analyze(req: AnalyzeRequest): Promise<{ report: Report; reachedApi: boolean }> {
  try {
    const res = await withTimeout(
      `${API_URL}/api/analyze`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      },
      // Live AlphaFold2 MSA jobs can take minutes; give the backend room before
      // we give up and show the bundled report.
      120000,
    );
    if (!res.ok) throw new Error(`API ${res.status}`);
    return { report: (await res.json()) as Report, reachedApi: true };
  } catch {
    // Backend unavailable — fall back to the bundled mock report so the demo
    // never breaks. (For non-default inputs this returns the demo result.)
    return { report: fallbackReport, reachedApi: false };
  }
}
