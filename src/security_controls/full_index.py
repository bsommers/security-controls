"""Compact offline indexer and loader for NIST SP 800-53 Rev. 5.1.1 (1,189 controls)."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from security_controls.loader import ControlLibrary

INSERT_PARAM_RE = re.compile(r"\{\{\s*insert:\s*param,\s*([A-Za-z0-9_.-]+)\s*\}\}")

BASELINE_FILES: tuple[tuple[str, str], ...] = (
    ("low", "NIST_SP-800-53_rev5_LOW-baseline_profile.json"),
    ("moderate", "NIST_SP-800-53_rev5_MODERATE-baseline_profile.json"),
    ("high", "NIST_SP-800-53_rev5_HIGH-baseline_profile.json"),
    ("privacy", "NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json"),
)


@dataclass(frozen=True)
class FullControlIndexEntry:
    """Normalized entry from the 1,189-control NIST SP 800-53 Rev. 5.1.1 OSCAL catalog."""

    id: str
    oscal_id: str
    family: str
    title: str
    baselines: tuple[str, ...]
    param_ids: tuple[str, ...]
    summary: str
    base_control_id: str | None = None


@dataclass(frozen=True)
class FullControlIndex:
    """Loaded full NIST SP 800-53 Rev. 5.1.1 index with active and withdrawn accounting."""

    standard_id: str
    version: str
    upstream_oscal_version: str
    total_controls_and_enhancements: int
    base_control_count: int
    enhancement_count: int
    active_count: int
    withdrawn_count: int
    withdrawn_ids: tuple[str, ...]
    controls: dict[str, FullControlIndexEntry]
    by_oscal_id: dict[str, FullControlIndexEntry]
    load_ms: float


def oscal_id_to_nist_id(oscal_id: str) -> str:
    """Convert canonical OSCAL ID ('ac-6.10' or 'si-7') to NIST prose ID ('AC-6(10)' or 'SI-7')."""
    raw = oscal_id.strip()
    if "." in raw:
        base, enh = raw.split(".", 1)
        fam, num = base.split("-", 1)
        return f"{fam.upper()}-{int(num)}({int(enh)})"
    fam, num = raw.split("-", 1)
    return f"{fam.upper()}-{int(num)}"


def _extract_param_labels(params_list: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for p in params_list:
        pid = str(p.get("id", "")).strip()
        if not pid:
            continue
        label = p.get("label")
        if isinstance(label, str) and label.strip():
            labels[pid] = label.strip()
            continue
        sel = p.get("select")
        if isinstance(sel, dict) and isinstance(sel.get("choice"), list):
            choices = [str(c).strip() for c in sel["choice"] if str(c).strip()]
            labels[pid] = " | ".join(choices[:3])
        else:
            labels[pid] = pid
    return labels


def _extract_statement_summary(
    parts: list[dict[str, Any]],
    param_labels: dict[str, str],
) -> str:
    fragments: list[str] = []

    def _walk(items: list[dict[str, Any]]) -> None:
        for part in items:
            prose = part.get("prose")
            if isinstance(prose, str) and prose.strip():
                fragments.append(prose.strip())
            sub = part.get("parts")
            if isinstance(sub, list) and len(fragments) < 3:
                _walk(sub)

    stmt_parts = [p for p in parts if p.get("name") == "statement"]
    _walk(stmt_parts or parts[:1])
    joined = " ".join(fragments)

    def _sub_param(match: re.Match[str]) -> str:
        pid = match.group(1)
        lbl = param_labels.get(pid, pid)
        return f"[ODP: {lbl}]"

    resolved = INSERT_PARAM_RE.sub(_sub_param, joined)
    compact = " ".join(resolved.split())
    if len(compact) > 140:
        return compact[:137].rstrip() + "..."
    return compact or "NIST SP 800-53 Rev. 5.1.1 control requirement."


def _load_baseline_memberships(input_dir: Path) -> dict[str, list[str]]:
    memberships: dict[str, list[str]] = {}
    for baseline_name, filename in BASELINE_FILES:
        prof_path = input_dir / filename
        if not prof_path.is_file():
            raise FileNotFoundError(f"Missing NIST baseline profile in input/: {prof_path}")
        doc = json.loads(prof_path.read_text(encoding="utf-8"))
        imports = doc.get("profile", {}).get("imports", [])
        for imp in imports:
            for inc in imp.get("include-controls", []):
                for cid in inc.get("with-ids", []):
                    cid_str = str(cid).strip().lower()
                    memberships.setdefault(cid_str, []).append(baseline_name)
    return memberships


def compile_upstream_oscal_catalog(
    input_dir: Path,
    output_path: Path | None = None,
) -> tuple[dict[str, Any], float]:
    """
    Parse NIST_SP-800-53_rev5_catalog.json + 4 baseline profiles into a compact index (<600 KiB).
    Returns (compiled_index_dict, elapsed_milliseconds).
    """
    t0 = time.perf_counter()
    cat_path = input_dir / "NIST_SP-800-53_rev5_catalog.json"
    if not cat_path.is_file():
        raise FileNotFoundError(f"Missing upstream OSCAL catalog: {cat_path}")

    baseline_map = _load_baseline_memberships(input_dir)
    raw_cat = json.loads(cat_path.read_text(encoding="utf-8"))["catalog"]
    meta = raw_cat.get("metadata", {})
    groups: list[dict[str, Any]] = list(raw_cat.get("groups", []))

    active_entries: list[dict[str, Any]] = []
    withdrawn_ids: list[str] = []
    base_count = 0
    enh_count = 0

    for group in groups:
        fam_code = str(group.get("id", "")).upper()
        for base_ctrl in group.get("controls", []):
            base_count += 1
            base_oscal_id = str(base_ctrl["id"]).lower()
            base_nist_id = oscal_id_to_nist_id(base_oscal_id)
            base_props = {
                str(p.get("name")): str(p.get("value"))
                for p in base_ctrl.get("props", [])
            }
            base_params_map = _extract_param_labels(base_ctrl.get("params", []))

            if base_props.get("status") == "withdrawn":
                withdrawn_ids.append(base_nist_id)
            else:
                active_entries.append(
                    {
                        "id": base_nist_id,
                        "oscal_id": base_oscal_id,
                        "family": fam_code,
                        "title": str(base_ctrl.get("title", "")).strip(),
                        "baselines": baseline_map.get(base_oscal_id, []),
                        "params": list(base_params_map.keys()),
                        "summary": _extract_statement_summary(
                            base_ctrl.get("parts", []), base_params_map
                        ),
                    }
                )

            for enh in base_ctrl.get("controls", []):
                enh_count += 1
                enh_oscal_id = str(enh["id"]).lower()
                enh_nist_id = oscal_id_to_nist_id(enh_oscal_id)
                enh_props = {str(p.get("name")): str(p.get("value")) for p in enh.get("props", [])}
                if enh_props.get("status") == "withdrawn":
                    withdrawn_ids.append(enh_nist_id)
                    continue
                enh_params_map = {
                    **base_params_map,
                    **_extract_param_labels(enh.get("params", [])),
                }
                own_param_ids = [str(p["id"]) for p in enh.get("params", []) if p.get("id")]
                active_entries.append(
                    {
                        "id": enh_nist_id,
                        "oscal_id": enh_oscal_id,
                        "base": base_nist_id,
                        "family": fam_code,
                        "title": str(enh.get("title", "")).strip(),
                        "baselines": baseline_map.get(enh_oscal_id, []),
                        "params": own_param_ids,
                        "summary": _extract_statement_summary(
                            enh.get("parts", []), enh_params_map
                        ),
                    }
                )

    compiled: dict[str, Any] = {
        "standard_id": "NIST-SP-800-53-R5-UPD1-FULL-INDEX",
        "source_url": "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
        "upstream_repo_tag": "https://github.com/usnistgov/oscal-content/releases/tag/v1.1.0",
        "version": str(meta.get("version", "5.1.1")),
        "upstream_oscal_version": str(meta.get("oscal-version", "1.1.1")),
        "group_count": len(groups),
        "base_control_count": base_count,
        "enhancement_count": enh_count,
        "total_controls_and_enhancements": base_count + enh_count,
        "active_count": len(active_entries),
        "withdrawn_count": len(withdrawn_ids),
        "withdrawn_ids": withdrawn_ids,
        "controls": active_entries,
    }
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Compact line-per-control serialization keeps diffs clean and file size < 400 KiB
        header = {k: v for k, v in compiled.items() if k != "controls"}
        header_lines = json.dumps(header, indent=2).splitlines()
        ctrl_lines = [
            "    " + json.dumps(entry, separators=(",", ":"))
            for entry in active_entries
        ]
        rendered = (
            "\n".join(header_lines[:-1])
            + ',\n  "controls": [\n'
            + ",\n".join(ctrl_lines)
            + "\n  ]\n}\n"
        )
        output_path.write_text(rendered, encoding="utf-8")

    return compiled, elapsed_ms


def load_full_index(repo_root: Path | None = None) -> FullControlIndex:
    """Load the compiled 1,189-control NIST SP 800-53 Rev. 5.1.1 index in < 100ms."""
    from security_controls.loader import CatalogIntegrityError, default_repo_root

    t0 = time.perf_counter()
    root = (repo_root or default_repo_root()).resolve()
    idx_path = root / "catalog" / "sp800-53-r5-upd1" / "full-index.json"
    if not idx_path.is_file():
        raise CatalogIntegrityError(f"Missing compiled full NIST control index: {idx_path}")

    doc = json.loads(idx_path.read_text(encoding="utf-8"))
    controls: dict[str, FullControlIndexEntry] = {}
    by_oscal: dict[str, FullControlIndexEntry] = {}

    for raw in doc.get("controls", []):
        entry = FullControlIndexEntry(
            id=str(raw["id"]),
            oscal_id=str(raw["oscal_id"]),
            family=str(raw["family"]),
            title=str(raw["title"]),
            baselines=tuple(str(b) for b in raw.get("baselines", [])),
            param_ids=tuple(str(p) for p in raw.get("params", [])),
            summary=str(raw["summary"]),
            base_control_id=str(raw["base"]) if "base" in raw else None,
        )
        controls[entry.id] = entry
        by_oscal[entry.oscal_id] = entry

    load_ms = (time.perf_counter() - t0) * 1000.0
    return FullControlIndex(
        standard_id=str(doc["standard_id"]),
        version=str(doc["version"]),
        upstream_oscal_version=str(doc["upstream_oscal_version"]),
        total_controls_and_enhancements=int(doc["total_controls_and_enhancements"]),
        base_control_count=int(doc["base_control_count"]),
        enhancement_count=int(doc["enhancement_count"]),
        active_count=int(doc["active_count"]),
        withdrawn_count=int(doc["withdrawn_count"]),
        withdrawn_ids=tuple(str(w) for w in doc.get("withdrawn_ids", [])),
        controls=controls,
        by_oscal_id=by_oscal,
        load_ms=load_ms,
    )


def verify_core_controls_against_full_index(
    lib: ControlLibrary,
    full_index: FullControlIndex,
) -> list[str]:
    """Verify 100% ID, family, active-status, and title alignment against full NIST 5.1.1 index."""
    mismatches: list[str] = []
    withdrawn_set = set(full_index.withdrawn_ids)

    for cid, core in lib.controls.items():
        if cid in withdrawn_set:
            mismatches.append(f"{cid}: core-controls.json includes withdrawn NIST control")
            continue
        upstream = full_index.controls.get(cid)
        if upstream is None:
            mismatches.append(f"{cid}: not found in NIST SP 800-53 Rev. 5.1.1 active catalog")
            continue
        if core.family != upstream.family:
            mismatches.append(f"{cid}: family '{core.family}' != upstream '{upstream.family}'")
        if core.title.lower() != upstream.title.lower():
            mismatches.append(
                f"{cid}: title '{core.title}' != upstream '{upstream.title}'"
            )
        if core.base_control_id != upstream.base_control_id:
            mismatches.append(
                f"{cid}: base_control_id '{core.base_control_id}' != '{upstream.base_control_id}'"
            )

    return mismatches
