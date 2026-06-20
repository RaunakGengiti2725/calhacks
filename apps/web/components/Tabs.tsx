"use client";

import { useRef } from "react";

export interface TabDef {
  id: string;
  label: string;
  /** Optional short hint shown under the active tab to orient the viewer. */
  hint?: string;
  /** Optional count badge (e.g. number of candidates). */
  count?: number;
}

/** Accessible, keyboard-navigable tab bar (roving tabindex, arrow keys, aria).
 *  Visual language matches the app: ink/subtle text, an accent underline for the
 *  active tab, generous touch targets. Controlled via `value` / `onChange`. */
export default function Tabs({
  tabs,
  value,
  onChange,
}: {
  tabs: TabDef[];
  value: string;
  onChange: (id: string) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const active = tabs.find((t) => t.id === value) ?? tabs[0];

  function onKeyDown(e: React.KeyboardEvent, idx: number) {
    const last = tabs.length - 1;
    let next = -1;
    if (e.key === "ArrowRight") next = idx === last ? 0 : idx + 1;
    else if (e.key === "ArrowLeft") next = idx === 0 ? last : idx - 1;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = last;
    if (next >= 0) {
      e.preventDefault();
      onChange(tabs[next].id);
      refs.current[next]?.focus();
    }
  }

  return (
    <div className="border-b border-line">
      <div role="tablist" aria-label="Report sections" className="-mb-px flex flex-wrap gap-1">
        {tabs.map((t, i) => {
          const on = t.id === value;
          return (
            <button
              key={t.id}
              ref={(el) => {
                refs.current[i] = el;
              }}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={on}
              aria-controls={`panel-${t.id}`}
              tabIndex={on ? 0 : -1}
              onClick={() => onChange(t.id)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={`group relative flex items-center gap-1.5 border-b-2 px-3.5 py-2.5 text-sm font-medium outline-none transition focus-visible:bg-canvas ${
                on
                  ? "border-accent text-ink"
                  : "border-transparent text-subtle hover:border-line hover:text-ink"
              }`}
            >
              {t.label}
              {typeof t.count === "number" && (
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums transition ${
                    on ? "bg-accent/10 text-accent" : "bg-canvas text-subtle group-hover:text-ink"
                  }`}
                >
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {active?.hint && (
        <p className="py-2.5 text-xs leading-relaxed text-subtle">{active.hint}</p>
      )}
    </div>
  );
}
