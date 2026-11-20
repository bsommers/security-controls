"""Smoke, unit, integration, and torture tests for NIST SP 800-53r5 Upd1 & COSIS controls."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.validate_controls import ROOT, validate_all
from security_controls.cli import main as cli_main
from security_controls.loader import (
    EXPECTED_COSIS_USE_CASES,
    EXPECTED_FAMILY_COUNT,
    CatalogIntegrityError,
    load_library,
)
from security_controls.oscal import build_oscal_profile, to_oscal_control_id
from security_controls.resolver import build_pattern_crosswalk, resolve_effective_profile


@pytest.mark.smoke
def test_repository_catalog_and_markdown_links_pass_validation() -> None:
    assert validate_all(ROOT) == []


@pytest.mark.unit
def test_sp800_53r5_upd1_twenty_families_and_five_cosis_use_cases() -> None:
    lib = load_library(ROOT)
    assert len(lib.families) == EXPECTED_FAMILY_COUNT
    assert set(lib.families) == {
        "AC",
        "AT",
        "AU",
        "CA",
        "CM",
        "CP",
        "IA",
        "IR",
        "MA",
        "MP",
        "PE",
        "PL",
        "PM",
        "PS",
        "PT",
        "RA",
        "SA",
        "SC",
        "SI",
        "SR",
    }
    assert tuple(lib.use_cases) == EXPECTED_COSIS_USE_CASES
    assert len(lib.controls) >= 40


@pytest.mark.unit
def test_oscal_control_id_canonicalization() -> None:
    assert to_oscal_control_id("AC-6") == "ac-6"
    assert to_oscal_control_id("AC-6(10)") == "ac-6.10"
    assert to_oscal_control_id("SI-7(1)") == "si-7.1"


@pytest.mark.integration
def test_multi_overlay_resolution_and_byte_deterministic_oscal_export() -> None:
    lib = load_library(ROOT)
    prof_a = resolve_effective_profile(
        lib,
        use_case_ids=["UC-AGENT-SINGLE", "UC-DEV"],
        baseline="high",
    )
    prof_b = resolve_effective_profile(
        lib,
        use_case_ids=["UC-AGENT-SINGLE", "UC-DEV"],
        baseline="high",
    )

    oscal_a = json.dumps(build_oscal_profile(prof_a), sort_keys=True)
    oscal_b = json.dumps(build_oscal_profile(prof_b), sort_keys=True)
    assert oscal_a == oscal_b

    ctrl_map = {ec.control.id: ec for ec in prof_a.controls}
    assert "AC-6(10)" in ctrl_map
    assert "SA-11" in ctrl_map
    assert "MCP-001" in ctrl_map["AC-6"].pattern_refs
    assert "MCP-008" in ctrl_map["SA-11"].pattern_refs


@pytest.mark.integration
def test_pattern_crosswalk_covers_all_eight_mcp_serve_patterns() -> None:
    lib = load_library(ROOT)
    crosswalk = build_pattern_crosswalk(lib)
    assert set(crosswalk.keys()) == {
        "MCP-001",
        "MCP-002",
        "MCP-003",
        "MCP-004",
        "MCP-005",
        "MCP-006",
        "MCP-007",
        "MCP-008",
    }


@pytest.mark.integration
def test_cli_summary_resolve_export_and_crosswalk(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli_main(["summary"]) == 0
    summary_json = json.loads(capsys.readouterr().out)
    assert summary_json["families"] == 20

    assert cli_main(["resolve", "--use-case", "UC-GEN", "--overlay-only"]) == 0
    resolved_json = json.loads(capsys.readouterr().out)
    assert resolved_json["effective_control_count"] == 6

    out_file = tmp_path / "uc-agent-multi.oscal.json"
    exit_code = cli_main(
        ["export-oscal", "--use-case", "UC-AGENT-MULTI", "--output", str(out_file)]
    )
    assert exit_code == 0
    capsys.readouterr()
    exported = json.loads(out_file.read_text(encoding="utf-8"))
    assert exported["profile"]["metadata"]["oscal-version"] == "1.1.2"

    assert cli_main(["crosswalk"]) == 0
    xwalk = json.loads(capsys.readouterr().out)
    assert "MCP-003" in xwalk


@pytest.mark.torture
def test_loader_rejects_fabricated_control_id_and_undeclared_parameter(tmp_path: Path) -> None:
    mirror = tmp_path / "repo"
    shutil.copytree(ROOT / "catalog", mirror / "catalog")

    # Inject a fabricated control reference into UC-GEN overlay
    uc_gen_path = mirror / "catalog" / "cosis" / "overlays" / "uc-gen-llm-assistant.json"
    doc = json.loads(uc_gen_path.read_text(encoding="utf-8"))
    original_cid = doc["tailored_controls"][0]["control_id"]
    doc["tailored_controls"][0]["control_id"] = "AC-999"
    uc_gen_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(CatalogIntegrityError, match="AC-999"):
        load_library(mirror)

    # Restore valid control_id, then inject an undeclared parameter_assignment key
    doc["tailored_controls"][0]["control_id"] = original_cid
    doc["tailored_controls"][0]["parameter_assignments"]["bogus_odp.99"] = "invalid"
    uc_gen_path.write_text(json.dumps(doc), encoding="utf-8")

    with pytest.raises(CatalogIntegrityError, match="bogus_odp.99"):
        load_library(mirror)
