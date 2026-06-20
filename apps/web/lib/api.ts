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

export async function analyze(req: AnalyzeRequest): Promise<{ report: Report; live: boolean }> {
  try {
    const res = await withTimeout(
      `${API_URL}/api/analyze`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      },
      20000,
    );
    if (!res.ok) throw new Error(`API ${res.status}`);
    return { report: (await res.json()) as Report, live: true };
  } catch {
    // Backend unavailable — fall back to the bundled mock report so the demo
    // never breaks. (For non-default inputs this returns the demo result.)
    return { report: fallbackReport, live: false };
  }
}
