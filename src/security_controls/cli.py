"""Command-line interface for resolving COSIS overlays and exporting OSCAL 1.1.2 profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from security_controls.assessor import assess_forge_bundle
from security_controls.full_index import load_full_index
from security_controls.loader import load_library
from security_controls.oscal import build_oscal_profile
from security_controls.resolver import build_pattern_crosswalk, resolve_effective_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="security-controls",
        description="NIST SP 800-53 Rev. 5 (Update 1) & COSIS Use-Case Security Controls CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("summary", help="Print catalog counts and registered COSIS use cases.")
    sub.add_parser(
        "index-stats",
        help="Print full 1,189-control NIST SP 800-53 Rev. 5.1.1 index statistics and load time.",
    )

    res_p = sub.add_parser("resolve", help="Resolve baseline + COSIS overlay controls.")
    res_p.add_argument(
        "--use-case",
        action="append",
        required=True,
        help="COSIS use case ID (UC-GEN, UC-PRED, UC-AGENT-SINGLE, UC-AGENT-MULTI, UC-DEV).",
    )
    res_p.add_argument("--baseline", default=None, help="SP 800-53B baseline override.")
    res_p.add_argument(
        "--overlay-only",
        action="store_true",
        help="Include only controls explicitly tailored by the selected COSIS overlay(s).",
    )

    osc_p = sub.add_parser("export-oscal", help="Export a deterministic OSCAL 1.1.2 Profile JSON.")
    osc_p.add_argument("--use-case", action="append", required=True)
    osc_p.add_argument("--baseline", default=None)
    osc_p.add_argument("--overlay-only", action="store_true")
    osc_p.add_argument("--output", type=Path, default=None)

    sub.add_parser("crosswalk", help="Print MCP-001..008 -> NIST SP 800-53r5 crosswalk JSON.")

    ass_p = sub.add_parser(
        "assess-forge",
        help="Run deterministic SP 800-53A control evaluation on a forged MCP bundle.",
    )
    ass_p.add_argument("--manifest", type=Path, required=True)
    ass_p.add_argument("--release-artifacts", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lib = load_library()

    if args.command == "summary":
        full_idx = load_full_index(lib.root_dir)
        payload = {
            "standard": "NIST-SP-800-53-R5-UPD1",
            "version": full_idx.version,
            "families": len(lib.families),
            "controls": len(lib.controls),
            "upstream_total_controls": full_idx.total_controls_and_enhancements,
            "upstream_active_controls": full_idx.active_count,
            "cosis_use_cases": [
                {"id": uc.id, "official_name": uc.official_name} for uc in lib.use_cases.values()
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "index-stats":
        full_idx = load_full_index(lib.root_dir)
        print(
            json.dumps(
                {
                    "version": full_idx.version,
                    "upstream_oscal_version": full_idx.upstream_oscal_version,
                    "total_controls_and_enhancements": full_idx.total_controls_and_enhancements,
                    "base_controls": full_idx.base_control_count,
                    "enhancements": full_idx.enhancement_count,
                    "active_controls": full_idx.active_count,
                    "withdrawn_controls": full_idx.withdrawn_count,
                    "load_ms": round(full_idx.load_ms, 2),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "resolve":
        prof = resolve_effective_profile(
            lib,
            use_case_ids=args.use_case,
            baseline=args.baseline,
            overlay_only=bool(args.overlay_only),
        )
        out = {
            "baseline": prof.baseline,
            "use_case_ids": list(prof.use_case_ids),
            "effective_control_count": len(prof.controls),
            "controls": [
                {
                    "id": ec.control.id,
                    "title": ec.control.title,
                    "priority": ec.priority,
                    "selected_by_baseline": ec.selected_by_baseline,
                    "selected_by_overlays": list(ec.selected_by_overlays),
                    "parameter_assignments": ec.parameter_assignments,
                    "pattern_refs": list(ec.pattern_refs),
                }
                for ec in prof.controls
            ],
        }
        print(json.dumps(out, indent=2))
        return 0

    if args.command == "export-oscal":
        prof = resolve_effective_profile(
            lib,
            use_case_ids=args.use_case,
            baseline=args.baseline,
            overlay_only=bool(args.overlay_only),
        )
        oscal_doc = build_oscal_profile(prof)
        rendered = json.dumps(oscal_doc, indent=2) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Wrote OSCAL 1.1.2 profile ({len(prof.controls)} controls) to {args.output}")
        else:
            print(rendered, end="")
        return 0

    if args.command == "crosswalk":
        print(json.dumps(build_pattern_crosswalk(lib), indent=2))
        return 0

    if args.command == "assess-forge":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        rel = json.loads(args.release_artifacts.read_text(encoding="utf-8"))
        findings = assess_forge_bundle(lib, manifest, rel)
        print(
            json.dumps(
                [
                    {
                        "control_id": f.control_id,
                        "oscal_id": f.oscal_id,
                        "priority": f.priority,
                        "state": f.state,
                        "assessor_type": f.assessor_type,
                        "evidence_summary": f.evidence_summary,
                    }
                    for f in findings
                ],
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
