#!/usr/bin/env python3
"""RS-4 Spike CLI: Deterministic SP 800-53A assessment of MCP Server Forge artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from security_controls.assessor import assess_forge_bundle  # noqa: E402
from security_controls.loader import load_library  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic SP 800-53A evidence evaluator for Forged MCP bundles"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--release-artifacts", type=Path, required=True)
    args = parser.parse_args(argv)

    lib = load_library(ROOT)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rel = json.loads(args.release_artifacts.read_text(encoding="utf-8"))
    findings = assess_forge_bundle(lib, manifest, rel)

    p1_tech = [
        f
        for f in findings
        if f.priority == "P1" and f.assessor_type == "automated-deterministic-gate"
    ]
    p1_satisfied = [f for f in p1_tech if f.state == "satisfied"]
    human_req = [f for f in findings if f.assessor_type == "human-attestation-required"]

    summary = {
        "spike_id": "RS-4",
        "server_name": manifest.get("server_name"),
        "total_evaluated": len(findings),
        "p1_technical_total": len(p1_tech),
        "p1_technical_satisfied": len(p1_satisfied),
        "p1_automated_ratio": round(len(p1_satisfied) / max(len(p1_tech), 1), 4),
        "human_attestation_required": [f.control_id for f in human_req],
        "pass": len(p1_satisfied) / max(len(p1_tech), 1) >= 0.70 and len(human_req) == 4,
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
