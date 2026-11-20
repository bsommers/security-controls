"""Deterministic loader and referential-integrity verifier for SP 800-53r5 & COSIS catalogs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from security_controls.models import (
    ControlFamily,
    ControlParameter,
    ControlRecord,
    CosisOverlay,
    CosisUseCase,
    TailoredControlRule,
)

EXPECTED_FAMILY_COUNT = 20
EXPECTED_COSIS_USE_CASES = (
    "UC-GEN",
    "UC-PRED",
    "UC-AGENT-SINGLE",
    "UC-AGENT-MULTI",
    "UC-DEV",
)
CONTROL_ID_RE = re.compile(r"^[A-Z]{2}-\d+(?:\(\d+\))?$")
PATTERN_REF_RE = re.compile(r"^MCP-\d{3}$")
VALID_BASELINES = frozenset({"low", "moderate", "high", "privacy"})


class CatalogIntegrityError(RuntimeError):
    """Raised when catalog JSON files violate NIST SP 800-53r5 or COSIS referential invariants."""


@dataclass(frozen=True)
class ControlLibrary:
    """In-memory verified catalog of SP 800-53r5 families, controls, and COSIS overlays."""

    root_dir: Path
    families: dict[str, ControlFamily]
    controls: dict[str, ControlRecord]
    use_cases: dict[str, CosisUseCase]
    overlays: dict[str, CosisOverlay]


def default_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CatalogIntegrityError(f"Missing required catalog file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CatalogIntegrityError(f"Expected top-level JSON object in {path}")
    return data


def load_library(repo_root: Path | None = None) -> ControlLibrary:
    """Load and cross-validate all SP 800-53r5 Update 1 families, controls, and COSIS overlays."""
    root = (repo_root or default_repo_root()).resolve()
    sp_dir = root / "catalog" / "sp800-53-r5-upd1"
    cosis_dir = root / "catalog" / "cosis"

    fam_doc = _read_json(sp_dir / "families.json")
    families: dict[str, ControlFamily] = {}
    for entry in fam_doc.get("families", []):
        code = str(entry["code"])
        if code in families:
            raise CatalogIntegrityError(f"Duplicate control family code '{code}'")
        families[code] = ControlFamily(code=code, title=str(entry["title"]))

    if len(families) != EXPECTED_FAMILY_COUNT:
        raise CatalogIntegrityError(
            f"Expected {EXPECTED_FAMILY_COUNT} NIST SP 800-53r5 families, found {len(families)}."
        )

    ctrl_doc = _read_json(sp_dir / "core-controls.json")
    if ctrl_doc.get("source_url") != "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final":
        raise CatalogIntegrityError("core-controls.json must cite NIST SP 800-53r5 upd1 final URL.")

    controls: dict[str, ControlRecord] = {}
    covered_families: set[str] = set()
    for raw in ctrl_doc.get("controls", []):
        cid = str(raw["id"])
        if not CONTROL_ID_RE.match(cid):
            raise CatalogIntegrityError(f"Invalid SP 800-53 control identifier '{cid}'")
        if cid in controls:
            raise CatalogIntegrityError(f"Duplicate control identifier '{cid}'")

        fam = str(raw["family"])
        if fam not in families:
            raise CatalogIntegrityError(f"Control '{cid}' references unknown family '{fam}'")
        if not cid.startswith(f"{fam}-"):
            raise CatalogIntegrityError(f"Control '{cid}' prefix does not match family '{fam}'")
        covered_families.add(fam)

        baselines = tuple(str(b) for b in raw.get("baselines", []))
        for b in baselines:
            if b not in VALID_BASELINES:
                raise CatalogIntegrityError(f"Control '{cid}' has invalid baseline '{b}'")

        params = tuple(
            ControlParameter(param_id=str(p["param_id"]), label=str(p["label"]))
            for p in raw.get("parameters", [])
        )
        base_cid = str(raw["base_control_id"]) if "base_control_id" in raw else None
        controls[cid] = ControlRecord(
            id=cid,
            family=fam,
            title=str(raw["title"]),
            baselines=baselines,
            outcome_summary=str(raw["outcome_summary"]),
            parameters=params,
            base_control_id=base_cid,
        )

    # Verify enhancement base controls exist if referenced
    for ctrl in controls.values():
        if ctrl.base_control_id and ctrl.base_control_id not in controls:
            raise CatalogIntegrityError(
                f"Enhancement '{ctrl.id}' references missing base control '{ctrl.base_control_id}'"
            )

    missing_fams = set(families) - covered_families
    if missing_fams:
        raise CatalogIntegrityError(
            f"Catalog missing representative controls for families: {sorted(missing_fams)}"
        )

    uc_doc = _read_json(cosis_dir / "use-cases.json")
    if uc_doc.get("source_url") != "https://csrc.nist.gov/projects/cosis/use-cases":
        raise CatalogIntegrityError("use-cases.json must cite NIST COSIS use-cases URL.")

    use_cases: dict[str, CosisUseCase] = {}
    overlays: dict[str, CosisOverlay] = {}

    for raw_uc in uc_doc.get("use_cases", []):
        uc_id = str(raw_uc["id"])
        uc = CosisUseCase(
            id=uc_id,
            slug=str(raw_uc["slug"]),
            official_name=str(raw_uc["official_name"]),
            overlay_file=str(raw_uc["overlay_file"]),
            summary=str(raw_uc["summary"]),
        )
        use_cases[uc_id] = uc

        ov_doc = _read_json(cosis_dir / uc.overlay_file)
        if ov_doc.get("use_case_id") != uc_id:
            raise CatalogIntegrityError(
                f"Overlay {uc.overlay_file} use_case_id '{ov_doc.get('use_case_id')}' != '{uc_id}'"
            )

        rules: list[TailoredControlRule] = []
        seen_in_overlay: set[str] = set()
        for raw_rule in ov_doc.get("tailored_controls", []):
            rcid = str(raw_rule["control_id"])
            if rcid not in controls:
                raise CatalogIntegrityError(
                    f"Overlay '{uc_id}' references unregistered control '{rcid}'"
                )
            if rcid in seen_in_overlay:
                raise CatalogIntegrityError(
                    f"Overlay '{uc_id}' contains duplicate tailoring entry for '{rcid}'"
                )
            seen_in_overlay.add(rcid)

            declared_params = {p.param_id for p in controls[rcid].parameters}
            assignments = {
                str(pk): str(pv) for pk, pv in raw_rule.get("parameter_assignments", {}).items()
            }
            unknown_params = set(assignments) - declared_params
            if unknown_params:
                raise CatalogIntegrityError(
                    f"Overlay '{uc_id}' control '{rcid}' assigns undeclared parameter(s): "
                    f"{sorted(unknown_params)}"
                )

            pat_refs = tuple(str(pr) for pr in raw_rule.get("pattern_refs", []))
            for pr in pat_refs:
                if not PATTERN_REF_RE.match(pr):
                    raise CatalogIntegrityError(
                        f"Overlay '{uc_id}' control '{rcid}' has invalid pattern_ref '{pr}'"
                    )

            rules.append(
                TailoredControlRule(
                    control_id=rcid,
                    overlay_priority=str(raw_rule["overlay_priority"]),
                    ai_tailoring_guidance=str(raw_rule["ai_tailoring_guidance"]),
                    parameter_assignments=assignments,
                    assessment_check=str(raw_rule["assessment_check"]),
                    pattern_refs=pat_refs,
                )
            )

        overlays[uc_id] = CosisOverlay(
            overlay_id=str(ov_doc["overlay_id"]),
            use_case_id=uc_id,
            title=str(ov_doc["title"]),
            source_url=str(ov_doc["source_url"]),
            provenance_tier=str(ov_doc["provenance_tier"]),
            default_baseline=str(ov_doc["default_baseline"]),
            cia_focus=tuple(str(c) for c in ov_doc.get("cia_focus", [])),
            primary_risks=tuple(str(r) for r in ov_doc.get("primary_risks", [])),
            tailored_controls=tuple(rules),
        )

    if tuple(use_cases.keys()) != EXPECTED_COSIS_USE_CASES:
        raise CatalogIntegrityError(
            f"Expected COSIS use cases {EXPECTED_COSIS_USE_CASES}, found {tuple(use_cases.keys())}"
        )

    return ControlLibrary(
        root_dir=root,
        families=families,
        controls=controls,
        use_cases=use_cases,
        overlays=overlays,
    )
