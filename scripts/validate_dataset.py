"""Acceptance audit before publishing a simulation dataset; never runs SUMO."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from traffic_study.dataset import BASE, build_dataset, sources
from traffic_study.paper_methods import PAPERS, RESEARCH_METHODS


def audit(source, target_methods=10, target_scales=None, target_seeds=None):
    data = build_dataset(source)
    rows, runs, plan = data["rows"], data["runs"], data["plan"]
    if target_scales is None:
        target_scales = len(plan.get("scales", []))
    if target_seeds is None:
        target_seeds = len(plan.get("seeds", []))
    warnings, policies = [], []
    for run in runs:
        result_file = BASE / source / "runs" / run["run_id"] / "result.json"
        result = json.loads(result_file.read_text(encoding="utf-8"))
        policies.append(result.get("transition_policy"))
        path = BASE / source / "runs" / run["run_id"] / "sumo.log"
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if any(
                    term in line
                    for term in (
                        "Unsafe green phase",
                        "Missing yellow phase",
                        "no connection to the next edge",
                        "Request backPos",
                        "for invalid lane",
                    )
                ):
                    warnings.append(dict(run_id=run["run_id"], message=line))
    methods = sorted({r["method"] for r in runs})
    scales = sorted({r["demand_scale"] for r in runs})
    seeds = sorted({r["seed"] for r in runs})
    expected_research = target_methods * target_scales * target_seeds
    expected = expected_research + target_scales * target_seeds
    research_count = sum(run["method"] in RESEARCH_METHODS for run in runs)
    keys = [(r["scenario"], r["method"], r["probe_id"]) for r in rows]
    incomplete = sum(not r["completed"] for r in rows)
    invalid = sum(not r["valid_for_comparison"] for r in rows)
    collision_runs = sum(
        (r.get("collisions") or 0) > 0 or (r.get("teleports") or 0) > 0 for r in runs
    )
    checks = [
        dict(
            name="paper_eligibility",
            passed=all(
                m in PAPERS and PAPERS[m]["year"] >= 2023 for m in methods if m != "fixed_time"
            ),
            detail="Each research method maps to a 2023+ nonlearning paper; four named ECC2024 variants share one paper; fixed-time is separate.",
        ),
        dict(
            name="no_rl_or_training",
            passed=bool(methods)
            and all(
                not PAPERS[m]["uses_rl"] and not PAPERS[m]["requires_training"]
                for m in methods
                if m in PAPERS
            ),
            detail="No RL branch is extracted from a hybrid paper in the current registry.",
        ),
        dict(
            name="method_coverage",
            passed=len(set(methods) & set(RESEARCH_METHODS)) >= target_methods,
            detail=f"{len(set(methods)&set(RESEARCH_METHODS))}/{target_methods} research methods + baseline",
        ),
        dict(
            name="demand_coverage",
            passed=len(scales) >= target_scales,
            detail=f"{len(scales)}/{target_scales} demand levels",
        ),
        dict(
            name="seed_coverage",
            passed=len(seeds) >= target_seeds,
            detail=f"{len(seeds)}/{target_seeds} seeds",
        ),
        dict(
            name="run_coverage",
            passed=len(runs) >= expected,
            detail=f"{len(runs)}/{expected} complete runs",
        ),
        dict(
            name="unique_probe_rows",
            passed=len(keys) == len(set(keys)),
            detail=f"{len(keys)-len(set(keys))} duplicates",
        ),
        dict(
            name="four_probes_per_run",
            passed=bool(runs) and len(rows) == 4 * len(runs),
            detail=f"{len(rows)} probe rows / {len(runs)} runs",
        ),
        dict(
            name="all_probes_arrived",
            passed=bool(rows) and incomplete == 0,
            detail=f"{incomplete} unfinished probes",
        ),
        dict(
            name="no_collision_or_teleport",
            passed=bool(runs) and collision_runs == 0,
            detail=f"{collision_runs} affected runs, {invalid} invalid probes",
        ),
        dict(
            name="signal_and_connection_warnings",
            passed=bool(runs) and not warnings,
            detail=f"{len(warnings)} warnings",
        ),
        dict(
            name="paired_baselines",
            passed=bool(rows) and all(r["paired_valid"] for r in rows),
            detail=f"{sum(r['paired_valid'] for r in rows)}/{len(rows)} valid paired rows",
        ),
        dict(
            name="transition_policy_documented",
            passed=bool(policies) and all(p is not None for p in policies),
            detail="Each method must record its transition policy. Stored all-red phases and optional added clearance are distinct; documentation is not a real-world calibration certificate.",
        ),
    ]
    # Count every expected combination, not only marginal coverage.
    combinations = {(r["demand_scale"], r["seed"], r["method"]) for r in runs}
    required = {
        (d, s, m)
        for d in plan.get("scales", [])
        for s in plan.get("seeds", [])
        for m in plan.get("methods", [])
    }
    checks.append(
        dict(
            name="planned_grid_complete",
            passed=bool(required) and combinations == required,
            detail=f"{len(combinations & required)}/{len(required)} planned combinations",
        )
    )
    return dict(
        source=source,
        accepted=all(c["passed"] for c in checks),
        target_runs=expected,
        target_research_runs=expected_research,
        actual_research_runs=research_count,
        actual_runs=len(runs),
        actual_probe_rows=len(rows),
        methods=methods,
        scales=scales,
        seeds=seeds,
        checks=checks,
        warnings=warnings,
        dataset_schema=data["schema"],
        note="Rejected runs stay in raw dataset. A technical pilot is not an accepted final dataset.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sources(), default="batch_pilot")
    args = parser.parse_args()
    result = audit(args.source)
    folder = BASE / args.source
    (folder / "acceptance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Dataset acceptance audit",
        "",
        f"Source: {args.source}",
        f"Status: {'ACCEPTED' if result['accepted'] else 'NOT READY'}",
        "",
        "| Check | Pass | Evidence |",
        "|---|---|---|",
    ]
    lines += [
        f"| {c['name']} | {'yes' if c['passed'] else 'no'} | {c['detail']} |"
        for c in result["checks"]
    ]
    lines += [
        "",
        "No dashboard or final comparison should be treated as validated until acceptance checks pass.",
        "Signal warnings require inspection; their presence alone does not establish the cause of each collision.",
    ]
    (folder / "ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("source", "accepted", "target_runs", "actual_runs", "actual_probe_rows")
            },
            indent=2,
        )
    )
    raise SystemExit(0 if result["accepted"] else 2)
