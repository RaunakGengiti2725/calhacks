"use client";

import { useEffect, useRef, useState } from "react";
import BackboneViewer from "./BackboneViewer";

/** Structure panel renderer.
 *
 *  The DEFAULT renderer is the dependency-free `BackboneViewer`: a rotating CA
 *  backbone trace colored by the standard AlphaFold pLDDT scale with introduced
 *  mutations marked. It always renders (no WebGL required), so the demo is never
 *  blank — this doubles as the "static fallback if WebGL fails" the spec calls for.
 *
 *  Mol* (full molecular graphics) is wired as an optional enhancement: set
 *  NEXT_PUBLIC_USE_MOLSTAR=1 to attempt it. If it initializes AND paints a
 *  structure, it takes over; otherwise the backbone trace stays. We only switch
 *  once Mol* has actually rendered (camera reset + resize), so a half-initialized
 *  Mol* can never leave an empty viewport. */
const USE_MOLSTAR = process.env.NEXT_PUBLIC_USE_MOLSTAR === "1";

export default function MolViewer({
  pdb,
  mutationPositions,
}: {
  pdb: string;
  mutationPositions: number[];
}) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [molReady, setMolReady] = useState(false);

  useEffect(() => {
    if (!USE_MOLSTAR) return;
    let disposed = false;
    let plugin: { dispose?: () => void; canvas3d?: { requestCameraReset: () => void; handleResize: () => void } } | null = null;

    (async () => {
      try {
        const host = hostRef.current;
        if (!host) return;
        const [{ PluginContext }, { DefaultPluginSpec }] = await Promise.all([
          import("molstar/lib/mol-plugin/context"),
          import("molstar/lib/mol-plugin/spec"),
        ]);
        const canvas = document.createElement("canvas");
        canvas.style.width = "100%";
        canvas.style.height = "100%";
        host.appendChild(canvas);

        const p = new PluginContext(DefaultPluginSpec());
        plugin = p as never;
        await p.init();
        if (!p.initViewer(canvas, host) || disposed) throw new Error("init failed");

        const data = await p.builders.data.rawData({ data: pdb }, { state: { isGhost: true } });
        const traj = await p.builders.structure.parseTrajectory(data, "pdb");
        const model = await p.builders.structure.createModel(traj);
        const structure = await p.builders.structure.createStructure(model);
        const polymer = await p.builders.structure.tryCreateComponentStatic(structure, "polymer");
        if (polymer) {
          await p.builders.structure.representation.addRepresentation(polymer, {
            type: "cartoon",
            color: "uncertainty",
          });
        }
        p.canvas3d?.handleResize();
        p.canvas3d?.requestCameraReset();
        if (!disposed) setMolReady(true);
      } catch {
        if (!disposed) setMolReady(false);
      }
    })();

    return () => {
      disposed = true;
      try {
        plugin?.dispose?.();
      } catch {
        /* ignore */
      }
      if (hostRef.current) hostRef.current.innerHTML = "";
    };
  }, [pdb]);

  return (
    <div className="relative" style={{ height: 360 }}>
      {USE_MOLSTAR && (
        <div ref={hostRef} style={{ position: "absolute", inset: 0, display: molReady ? "block" : "none" }} />
      )}
      {!molReady && <BackboneViewer pdb={pdb} mutationPositions={mutationPositions} />}
    </div>
  );
}
