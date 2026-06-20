"""DryRun CLI — runs the entire cascade in process and prints the JSON report.

`dryrun --demo` runs the bundled demo end to end with zero configuration. stdout
is always the pure JSON report (machine-usable); a human-readable summary is
printed to stderr.

This module imports only the uagents-free cascade, so it works with just the mock
demo install (no agent framework needed).
"""

from __future__ import annotations

import argparse
import sys

from dryrun_agents.shared.cascade import run_cascade
from dryrun_agents.shared.inputs import resolve_inputs
from dryrun_providers import get_mode


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dryrun",
        description="Run the DryRun pre-synthesis experiment-design cascade.",
    )
    p.add_argument("--demo", action="store_true", help="Run the bundled demo (no config needed)")
    p.add_argument("--natural", "-n", type=str, default=None, help="Plain-English request")
    p.add_argument("--seed", type=str, default=None, help="Seed protein sequence")
    p.add_argument("--goal", type=str, default=None, help="Design goal")
    p.add_argument("--budget", type=float, default=None, help="Total synthesis budget (USD)")
    p.add_argument("--candidates", type=int, default=None, help="Number of candidate variants")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress the stderr summary")
    return p


def _print_summary(report) -> None:
    s, f = report.summary, report.funnel
    c = report.comparison
    out = sys.stderr
    print("", file=out)
    print("  DryRun — pre-synthesis experiment design", file=out)
    print(f"  mode={report.meta.mode}  goal={report.meta.goal}", file=out)
    print("  " + "-" * 56, file=out)
    print(
        f"  cascade:  generated {f.generated}  ->  viability {f.viability_passed}"
        f"  ->  fold {f.fold_passed}  ->  selected {f.selected}",
        file=out,
    )
    print(
        f"  spend:    ${s.spend:,.0f} of ${s.budget:,.0f} budget", file=out
    )
    print(
        f"  DryRun:   {s.expected_distinct_successes:.2f} distinct approaches covered"
        f"  ({s.expected_constructs:.1f} expected good constructs)",
        file=out,
    )
    print(
        f"  naive:    {s.naive_expected_distinct_successes:.2f} distinct approaches covered"
        f"  ({s.naive_expected_constructs:.1f} expected good constructs)",
        file=out,
    )
    print(f"  uplift:   {s.uplift_ratio:.1f}x more distinct approaches at the same budget", file=out)
    if c.dollars_naive_needs_to_match is not None:
        print(
            f"  to match: naive would need ${c.dollars_naive_needs_to_match:,.0f}"
            f" (vs ${s.spend:,.0f})",
            file=out,
        )
    print("  " + "-" * 56, file=out)
    print(f"  {report.plain_summary}", file=out)
    print("", file=out)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    seed, goal, budget, count = resolve_inputs(
        natural=args.natural,
        seed=args.seed,
        goal=args.goal,
        budget=args.budget,
        candidates=args.candidates,
    )

    if not args.quiet:
        print(f"Running DryRun cascade (mode={get_mode()})...", file=sys.stderr)

    report = run_cascade(seed, goal, budget, count)

    # stdout = pure JSON report
    print(report.model_dump_json(indent=2))

    if not args.quiet:
        _print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
