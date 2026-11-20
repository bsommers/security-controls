"""Command-line interface for resolving COSIS overlays and exporting OSCAL 1.1.2 profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    lib = load_library()

    if args.command == "summary":
        payload = {
            "standard": "NIST-SP-800-53-R5-UPD1",
            "families": len(lib.families),
            "controls": len(lib.controls),
            "cosis_use_cases": [
                {"id": uc.id, "official_name": uc.official_name} for uc in lib.use_cases.values()
            ],
        }
        print(json.dumps(payload, indent=2))
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
