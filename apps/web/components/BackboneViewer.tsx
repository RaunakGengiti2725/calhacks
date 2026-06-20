"use client";

import { useEffect, useRef } from "react";
import { plddtColor } from "@/lib/plddt";

interface CA {
  x: number;
  y: number;
  z: number;
  b: number;
  mutated: boolean;
}

function parseCA(pdb: string, mutations: Set<number>): CA[] {
  const out: CA[] = [];
  let resi = 0;
  for (const line of pdb.split("\n")) {
    if ((line.startsWith("ATOM") || line.startsWith("HETATM")) && line.slice(12, 16).trim() === "CA") {
      resi += 1;
      out.push({
        x: +line.slice(30, 38),
        y: +line.slice(38, 46),
        z: +line.slice(46, 54),
        b: +line.slice(60, 66),
        mutated: mutations.has(resi),
      });
    }
  }
  return out;
}

/** A dependency-free, always-rendering 3D backbone trace: auto-rotating CA tube
 *  colored by per-residue pLDDT, with introduced mutations marked. This is the
 *  guaranteed visual (and the WebGL-failure fallback) for the structure panel. */
export default function BackboneViewer({
  pdb,
  mutationPositions,
}: {
  pdb: string;
  mutationPositions: number[];
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rotRef = useRef(0);
  const draggingRef = useRef<{ x: number; y: number } | null>(null);
  const angleRef = useRef({ ax: 0.3, ay: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const atoms = parseCA(pdb, new Set(mutationPositions));
    if (atoms.length === 0) return;

    // center + scale
    const cx = atoms.reduce((s, a) => s + a.x, 0) / atoms.length;
    const cy = atoms.reduce((s, a) => s + a.y, 0) / atoms.length;
    const cz = atoms.reduce((s, a) => s + a.z, 0) / atoms.length;
    let maxR = 1;
    for (const a of atoms) {
      const d = Math.hypot(a.x - cx, a.y - cy, a.z - cz);
      if (d > maxR) maxR = d;
    }

    const W = 600;
    const H = 360;
    const dpr = Math.min(typeof window !== "undefined" ? window.devicePixelRatio : 1, 2);
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);
    const scale = (Math.min(W, H) * 0.42) / maxR;

    let raf = 0;
    const render = () => {
      const { ax } = angleRef.current;
      const ay = angleRef.current.ay + (draggingRef.current ? 0 : (rotRef.current += 0.005));
      const cosY = Math.cos(ay);
      const sinY = Math.sin(ay);
      const cosX = Math.cos(ax);
      const sinX = Math.sin(ax);

      const pts = atoms.map((a) => {
        let x = a.x - cx;
        let y = a.y - cy;
        let z = a.z - cz;
        // rotate Y then X
        let x1 = x * cosY + z * sinY;
        let z1 = -x * sinY + z * cosY;
        let y1 = y * cosX - z1 * sinX;
        let z2 = y * sinX + z1 * cosX;
        return {
          sx: W / 2 + x1 * scale,
          sy: H / 2 - y1 * scale,
          depth: z2,
          b: a.b,
          mutated: a.mutated,
        };
      });

      ctx.clearRect(0, 0, W, H);
      // draw backbone segments back-to-front
      const order = pts.map((_, i) => i).slice(0, -1);
      order.sort((i, j) => (pts[i].depth + pts[i + 1].depth) - (pts[j].depth + pts[j + 1].depth));
      const minD = Math.min(...pts.map((p) => p.depth));
      const maxD = Math.max(...pts.map((p) => p.depth));
      const shade = (d: number) => 0.45 + 0.55 * ((d - minD) / Math.max(maxD - minD, 1));

      ctx.lineCap = "round";
      for (const i of order) {
        const p = pts[i];
        const q = pts[i + 1];
        ctx.strokeStyle = plddtColor((p.b + q.b) / 2);
        ctx.globalAlpha = shade((p.depth + q.depth) / 2);
        ctx.lineWidth = 4.5;
        ctx.beginPath();
        ctx.moveTo(p.sx, p.sy);
        ctx.lineTo(q.sx, q.sy);
        ctx.stroke();
      }
      // mutation markers (front-most)
      ctx.globalAlpha = 1;
      for (const p of pts) {
        if (!p.mutated) continue;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 6, 0, Math.PI * 2);
        ctx.fillStyle = "#111827";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 6, 0, Math.PI * 2);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(render);
    };
    raf = requestAnimationFrame(render);

    // drag to rotate
    const onDown = (e: PointerEvent) => {
      draggingRef.current = { x: e.clientX, y: e.clientY };
    };
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current) return;
      const dx = e.clientX - draggingRef.current.x;
      const dy = e.clientY - draggingRef.current.y;
      angleRef.current.ay += dx * 0.01;
      angleRef.current.ax = Math.max(-1.4, Math.min(1.4, angleRef.current.ax + dy * 0.01));
      draggingRef.current = { x: e.clientX, y: e.clientY };
    };
    const onUp = () => {
      draggingRef.current = null;
    };
    canvas.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);

    return () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [pdb, mutationPositions]);

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: "360px", touchAction: "none", cursor: "grab" }}
        aria-label="3D protein backbone colored by confidence"
      />
      <span className="pointer-events-none absolute bottom-2 right-3 text-[10px] text-subtle">
        drag to rotate
      </span>
    </div>
  );
}
