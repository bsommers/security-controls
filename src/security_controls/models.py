"""Typed data models for NIST SP 800-53 Rev. 5 (Update 1) controls and COSIS overlays."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlFamily:
    """One of the 20 official NIST SP 800-53 Rev. 5 control families."""

    code: str
    title: str


@dataclass(frozen=True)
class ControlParameter:
    """Organization-defined parameter (ODP) slot on an SP 800-53r5 control."""

    param_id: str
    label: str


@dataclass(frozen=True)
class ControlRecord:
    """Grounded NIST SP 800-53 Rev. 5 (Update 1) control or control enhancement."""

    id: str
    family: str
    title: str
    baselines: tuple[str, ...]
    outcome_summary: str
    parameters: tuple[ControlParameter, ...]
    base_control_id: str | None = None


@dataclass(frozen=True)
class CosisUseCase:
    """Official NIST COSIS project use-case metadata."""

    id: str
    slug: str
    official_name: str
    overlay_file: str
    summary: str


@dataclass(frozen=True)
class TailoredControlRule:
    """COSIS use-case tailoring rule parameterizing an SP 800-53r5 control."""

    control_id: str
    overlay_priority: str
    ai_tailoring_guidance: str
    parameter_assignments: dict[str, str]
    assessment_check: str
    pattern_refs: tuple[str, ...]


@dataclass(frozen=True)
class CosisOverlay:
    """Complete NIST COSIS use-case control overlay."""

    overlay_id: str
    use_case_id: str
    title: str
    source_url: str
    provenance_tier: str
    default_baseline: str
    cia_focus: tuple[str, ...]
    primary_risks: tuple[str, ...]
    tailored_controls: tuple[TailoredControlRule, ...]


@dataclass(frozen=True)
class EffectiveControl:
    """Resolved SP 800-53r5 control combining baseline selection and COSIS tailoring."""

    control: ControlRecord
    selected_by_baseline: bool
    selected_by_overlays: tuple[str, ...]
    priority: str
    parameter_assignments: dict[str, str]
    tailoring_guidance: tuple[str, ...]
    assessment_checks: tuple[str, ...]
    pattern_refs: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedProfile:
    """Deterministic result of resolving a baseline + one or more COSIS use-case overlays."""

    baseline: str
    use_case_ids: tuple[str, ...]
    controls: tuple[EffectiveControl, ...]
