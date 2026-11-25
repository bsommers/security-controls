#!/usr/bin/env python3
"""Deterministic repository validator for NIST SP 800-53r5 Update 1 & COSIS controls."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from security_controls.full_index import (  # noqa: E402
    load_full_index,
    verify_core_controls_against_full_index,
)
from security_controls.loader import CatalogIntegrityError, load_library  # noqa: E402
from security_controls.oscal import (  # noqa: E402
    build_oscal_profile,
    validate_oscal_profile_schema,
)
from security_controls.resolver import resolve_effective_profile  # noqa: E402

MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(((?:[^()]|\([^()]*\))+)\)")
VALID_SOURCE_TIERS = frozenset({"nist_sp800_53b", "nist_cosis_draft", "org_pattern_tailoring"})


def _strip_fenced_code(md_text: str) -> str:
    return re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)


def validate_all(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        lib = load_library(root)
    except CatalogIntegrityError as exc:
        return [str(exc)]

    # RS-1: Verify 1,189-control Rev. 5.1.1 full index & 100% alignment with core-controls.json
    full_idx_path = root / "catalog" / "sp800-53-r5-upd1" / "full-index.json"
    if full_idx_path.is_file():
        full_idx = load_full_index(root)
        if full_idx.total_controls_and_enhancements != 1189:
            errors.append(
                f"Expected 1,189 total controls in full-index.json, got "
                f"{full_idx.total_controls_and_enhancements}"
            )
        errors.extend(verify_core_controls_against_full_index(lib, full_idx))

    # RS-2: Verify two-layer provenance separation on every COSIS overlay (0 unattributed rules)
    cosis_dir = root / "catalog" / "cosis"
    for uc_id, uc in lib.use_cases.items():
        ov_raw = json.loads((cosis_dir / uc.overlay_file).read_text(encoding="utf-8"))
        src_prov = ov_raw.get("source_provenance")
        if not isinstance(src_prov, dict):
            errors.append(f"{uc_id}: missing RS-2 source_provenance block")
        else:
            up = src_prov.get("upstream_cosis_source", {})
            if up.get("publication_status") != "[NIST-DRAFT]":
                errors.append(f"{uc_id}: upstream_cosis_source must carry [NIST-DRAFT] tag")
        for r_idx, raw_rule in enumerate(ov_raw.get("tailored_controls", [])):
            tier = raw_rule.get("source_tier")
            if tier not in VALID_SOURCE_TIERS:
                errors.append(f"{uc_id}[{r_idx}]: invalid or missing source_tier {tier!r}")

    # RS-3: Verify every COSIS overlay resolves cleanly & passes NIST OSCAL 1.1.2 JSON Schema
    oscal_schema_path = root / "schema" / "oscal_profile_schema.json"
    for uc_id in lib.use_cases:
        prof = resolve_effective_profile(lib, use_case_ids=[uc_id])
        oscal = build_oscal_profile(prof)
        if oscal["profile"]["metadata"]["oscal-version"] != "1.1.2":
            errors.append(f"{uc_id}: invalid oscal-version")
        if not oscal["profile"]["modify"]["set-parameters"]:
            errors.append(f"{uc_id}: expected non-empty OSCAL set-parameters")
        if oscal_schema_path.is_file():
            for schema_err in validate_oscal_profile_schema(oscal, oscal_schema_path):
                errors.append(f"{uc_id} OSCAL 1.1.2 schema error at {schema_err}")

    # Verify relative links across all Markdown documentation
    for md_path in sorted(root.rglob("*.md")):
        if ".venv" in md_path.parts or "target" in md_path.parts:
            continue
        cleaned = _strip_fenced_code(md_path.read_text(encoding="utf-8"))
        for match in MD_LINK_RE.finditer(cleaned):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            rel_part = urllib.parse.unquote(raw_target.split("#", 1)[0])
            if not rel_part:
                continue
            resolved = (md_path.parent / rel_part).resolve()
            if not resolved.exists():
                errors.append(
                    f"Broken relative link in {md_path.relative_to(root)}: '{raw_target}'"
                )

    return errors


def main() -> int:
    errors = validate_all(ROOT)
    if errors:
        for err in errors:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1
    lib = load_library(ROOT)
    full_idx = load_full_index(ROOT)
    print(
        f"[PASS] Validated {len(lib.families)} families, {len(lib.controls)} curated controls, "
        f"{full_idx.total_controls_and_enhancements} upstream NIST Rev. {full_idx.version} "
        f"controls ({full_idx.active_count} active in {full_idx.load_ms:.1f}ms), "
        f"and {len(lib.overlays)} OSCAL 1.1.2 schema-verified COSIS overlays."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
