#!/usr/bin/env python3
"""RS-1 Spike CLI: Compile NIST SP 800-53 Rev. 5.1.1 (1,189 controls) & benchmark <150ms load."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from security_controls.full_index import (  # noqa: E402
    compile_upstream_oscal_catalog,
    load_full_index,
    verify_core_controls_against_full_index,
)
from security_controls.loader import load_library  # noqa: E402


def main() -> int:
    input_dir = ROOT / "input"
    out_path = ROOT / "catalog" / "sp800-53-r5-upd1" / "full-index.json"

    compile_runs_ms: list[float] = []
    compiled_doc: dict[str, object] = {}
    for idx in range(5):
        compiled_doc, ms = compile_upstream_oscal_catalog(
            input_dir, output_path=out_path if idx == 0 else None
        )
        compile_runs_ms.append(ms)

    load_runs_ms: list[float] = []
    full_idx = load_full_index(ROOT)
    load_runs_ms.append(full_idx.load_ms)
    for _ in range(4):
        load_runs_ms.append(load_full_index(ROOT).load_ms)

    lib = load_library(ROOT)
    mismatches = verify_core_controls_against_full_index(lib, full_idx)
    size_bytes = out_path.stat().st_size

    report = {
        "spike_id": "RS-1",
        "catalog_version": full_idx.version,
        "upstream_oscal_version": full_idx.upstream_oscal_version,
        "groups": compiled_doc["group_count"],
        "base_controls": full_idx.base_control_count,
        "enhancements": full_idx.enhancement_count,
        "total_controls_and_enhancements": full_idx.total_controls_and_enhancements,
        "active_controls": full_idx.active_count,
        "withdrawn_controls": full_idx.withdrawn_count,
        "compiled_index_bytes": size_bytes,
        "compiled_index_kib": round(size_bytes / 1024.0, 2),
        "compile_median_ms": round(statistics.median(compile_runs_ms), 2),
        "cold_load_median_ms": round(statistics.median(load_runs_ms), 2),
        "core_controls_mismatches": mismatches,
        "pass": (
            full_idx.total_controls_and_enhancements == 1189
            and full_idx.active_count >= 1000
            and size_bytes < 600 * 1024
            and statistics.median(compile_runs_ms) < 150.0
            and statistics.median(load_runs_ms) < 100.0
            and not mismatches
        ),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
