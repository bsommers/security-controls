"""Milestone M1 Research Spike verification suite (RS-1..RS-4 + Hypothesis fuzzing)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from jsonschema import Draft202012Validator

from scripts.validate_controls import ROOT
from security_controls.assessor import HUMAN_ATTESTATION_CONTROLS, assess_forge_bundle
from security_controls.full_index import (
    load_full_index,
    verify_core_controls_against_full_index,
)
from security_controls.loader import EXPECTED_COSIS_USE_CASES, load_library
from security_controls.oscal import build_oscal_profile, validate_oscal_profile_schema
from security_controls.resolver import resolve_effective_profile


@pytest.mark.unit
def test_rs1_full_1189_control_index_loads_under_150ms_and_matches_core_controls() -> None:
    idx_path = ROOT / "catalog" / "sp800-53-r5-upd1" / "full-index.json"
    assert idx_path.is_file()
    assert idx_path.stat().st_size < 600 * 1024

    full_idx = load_full_index(ROOT)
    assert full_idx.version == "5.1.1"
    assert full_idx.total_controls_and_enhancements == 1189
    assert full_idx.base_control_count == 322
    assert full_idx.enhancement_count == 867
    assert full_idx.active_count == 1007
    assert full_idx.withdrawn_count == 182
    assert full_idx.load_ms < 150.0

    # Verify ODP prose substitution resolved '{{ insert: param, ... }}' cleanly
    ac2 = full_idx.controls["AC-2"]
    assert "{{ insert:" not in ac2.summary
    assert "low" in ac2.baselines and "moderate" in ac2.baselines and "high" in ac2.baselines

    lib = load_library(ROOT)
    assert verify_core_controls_against_full_index(lib, full_idx) == []


@pytest.mark.unit
def test_rs2_two_layer_provenance_schema_zero_unattributed_assertions() -> None:
    schema_obj = json.loads((ROOT / "schema" / "cosis-overlay.schema.json").read_text("utf-8"))
    validator = Draft202012Validator(schema_obj)

    lib = load_library(ROOT)
    for uc_id, uc in lib.use_cases.items():
        ov_path = ROOT / "catalog" / "cosis" / uc.overlay_file
        ov_doc = json.loads(ov_path.read_text(encoding="utf-8"))
        errs = list(validator.iter_errors(ov_doc))
        assert errs == [], f"{uc_id} failed cosis-overlay.schema.json: {errs}"
        assert (
            ov_doc["source_provenance"]["upstream_cosis_source"]["publication_status"]
            == "[NIST-DRAFT]"
        )


@pytest.mark.integration
def test_rs3_all_five_cosis_profiles_pass_official_nist_oscal_1_1_2_schema(
    tmp_path: Path,
) -> None:
    schema_path = ROOT / "schema" / "oscal_profile_schema.json"
    assert schema_path.is_file()

    lib = load_library(ROOT)
    for uc_id in EXPECTED_COSIS_USE_CASES:
        prof = resolve_effective_profile(lib, use_case_ids=[uc_id])
        oscal_doc = build_oscal_profile(prof)
        out_path = tmp_path / f"{uc_id.lower()}.oscal-profile.json"
        out_path.write_text(json.dumps(oscal_doc, indent=2), encoding="utf-8")
        assert validate_oscal_profile_schema(oscal_doc, schema_path) == []

    # Composite multi-overlay profile also validates cleanly with zero schema errors
    combo_prof = resolve_effective_profile(
        lib, use_case_ids=["UC-AGENT-SINGLE", "UC-AGENT-MULTI", "UC-DEV"], baseline="high"
    )
    combo_oscal = build_oscal_profile(combo_prof)
    assert validate_oscal_profile_schema(combo_oscal, schema_path) == []


@pytest.mark.integration
def test_rs4_deterministic_sp800_53a_forge_assessor_and_human_boundary() -> None:
    lib = load_library(ROOT)
    sample_manifest = {
        "protocol_revision": "2026-07-28",
        "server_name": "acme-incidents",
        "upstream": {"timeout_seconds": 15.0, "max_response_bytes": 32768},
        "auth": {"type": "bearer", "token_env": "ACME_API_TOKEN"},
        "tools": [
            {"name": "get_incident", "annotations": {"readOnlyHint": True}},
            {
                "name": "delete_incident",
                "annotations": {"readOnlyHint": False, "destructiveHint": True},
            },
        ],
    }
    sample_release = {
        "container_image": "ghcr.io/bsommers/forged-mcp-acme-incidents:2.0.0",
        "governance": {"requires_appsec_destructive_signoff": True},
        "oscal_assurance": {"open_poam_items": 0},
    }

    findings = assess_forge_bundle(lib, sample_manifest, sample_release)
    by_id = {f.control_id: f for f in findings}

    # Human controls MUST NEVER be machine self-attested
    for h_cid in HUMAN_ATTESTATION_CONTROLS:
        assert by_id[h_cid].assessor_type == "human-attestation-required"
        assert by_id[h_cid].state == "other-than-satisfied"

    p1_tech = [
        f
        for f in findings
        if f.priority == "P1" and f.assessor_type == "automated-deterministic-gate"
    ]
    p1_satisfied = [f for f in p1_tech if f.state == "satisfied"]
    assert len(p1_tech) >= 10
    assert len(p1_satisfied) / len(p1_tech) >= 0.70

    # Dishonest destructive tool without AppSec signoff flips AC-6(10) to other-than-satisfied
    bad_release = {
        **sample_release,
        "governance": {"requires_appsec_destructive_signoff": False},
    }
    bad_findings = {f.control_id: f for f in assess_forge_bundle(lib, sample_manifest, bad_release)}
    assert bad_findings["AC-6(10)"].state == "other-than-satisfied"


@pytest.mark.torture
@given(
    uc_subset=st.lists(
        st.sampled_from(list(EXPECTED_COSIS_USE_CASES)), min_size=1, max_size=5, unique=True
    ),
    extra_uc=st.sampled_from(list(EXPECTED_COSIS_USE_CASES)),
    baseline=st.sampled_from(["low", "moderate", "high"]),
)
def test_hypothesis_overlay_resolution_monotonicity(
    uc_subset: list[str], extra_uc: str, baseline: str
) -> None:
    """Monotonicity invariant: adding an overlay never drops selected controls or weakens P1."""
    lib = load_library(ROOT)
    base_prof = resolve_effective_profile(lib, use_case_ids=uc_subset, baseline=baseline)
    superset_ucs = list(dict.fromkeys([*uc_subset, extra_uc]))
    super_prof = resolve_effective_profile(lib, use_case_ids=superset_ucs, baseline=baseline)

    base_ids = {ec.control.id for ec in base_prof.controls}
    super_ids = {ec.control.id for ec in super_prof.controls}
    assert base_ids.issubset(super_ids)

    super_prio = {ec.control.id: ec.priority for ec in super_prof.controls}
    for ec in base_prof.controls:
        if ec.priority == "P1":
            assert super_prio[ec.control.id] == "P1"
