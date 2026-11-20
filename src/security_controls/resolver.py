"""Deterministic SP 800-53B baseline + NIST COSIS multi-overlay resolver and pattern crosswalk."""

from __future__ import annotations

import re

from security_controls.loader import VALID_BASELINES, ControlLibrary
from security_controls.models import (
    EffectiveControl,
    ResolvedProfile,
    TailoredControlRule,
)


def _control_sort_key(control_id: str) -> tuple[str, int, int]:
    match = re.match(r"^([A-Z]{2})-(\d+)(?:\((\d+)\))?$", control_id)
    if not match:
        return (control_id, 0, 0)
    fam, num, enh = match.group(1), int(match.group(2)), int(match.group(3) or 0)
    return (fam, num, enh)


def resolve_effective_profile(
    library: ControlLibrary,
    *,
    use_case_ids: list[str] | tuple[str, ...],
    baseline: str | None = None,
    overlay_only: bool = False,
) -> ResolvedProfile:
    """Resolve an effective SP 800-53r5 control set for a baseline + 1..N COSIS overlays."""
    if not use_case_ids:
        raise ValueError("At least one COSIS use_case_id is required.")

    normalized_ucs: list[str] = []
    for uc_id in use_case_ids:
        if uc_id not in library.overlays:
            raise ValueError(
                f"Unknown COSIS use_case_id '{uc_id}'. Valid IDs: {sorted(library.overlays)}"
            )
        if uc_id not in normalized_ucs:
            normalized_ucs.append(uc_id)

    effective_baseline = baseline or library.overlays[normalized_ucs[0]].default_baseline
    if effective_baseline not in VALID_BASELINES and effective_baseline != "none":
        raise ValueError(f"Invalid baseline '{effective_baseline}'.")

    rules_by_control: dict[str, list[tuple[str, TailoredControlRule]]] = {}
    for uc_id in normalized_ucs:
        overlay = library.overlays[uc_id]
        for rule in overlay.tailored_controls:
            rules_by_control.setdefault(rule.control_id, []).append((uc_id, rule))

    resolved_controls: list[EffectiveControl] = []
    for cid in sorted(library.controls, key=_control_sort_key):
        ctrl = library.controls[cid]
        in_baseline = (
            False
            if overlay_only or effective_baseline == "none"
            else effective_baseline in ctrl.baselines
        )
        matched_rules = rules_by_control.get(cid, [])
        if not in_baseline and not matched_rules:
            continue

        merged_params: dict[str, str] = {}
        guidance_items: list[str] = []
        checks: list[str] = []
        pat_refs: list[str] = []
        overlay_ids: list[str] = []
        best_priority = "P2" if in_baseline else "P2"

        for uc_id, rule in matched_rules:
            overlay_ids.append(uc_id)
            if rule.overlay_priority == "P1":
                best_priority = "P1"
            for pk, pv in rule.parameter_assignments.items():
                if pk in merged_params and merged_params[pk] != pv:
                    merged_params[pk] = f"{merged_params[pk]} | [{uc_id}] {pv}"
                else:
                    merged_params[pk] = pv
            guidance_items.append(f"[{uc_id}] {rule.ai_tailoring_guidance}")
            checks.append(f"[{uc_id}] {rule.assessment_check}")
            for pr in rule.pattern_refs:
                if pr not in pat_refs:
                    pat_refs.append(pr)

        resolved_controls.append(
            EffectiveControl(
                control=ctrl,
                selected_by_baseline=in_baseline,
                selected_by_overlays=tuple(overlay_ids),
                priority=best_priority,
                parameter_assignments=merged_params,
                tailoring_guidance=tuple(guidance_items),
                assessment_checks=tuple(checks),
                pattern_refs=tuple(sorted(pat_refs)),
            )
        )

    return ResolvedProfile(
        baseline=effective_baseline,
        use_case_ids=tuple(normalized_ucs),
        controls=tuple(resolved_controls),
    )


def build_pattern_crosswalk(
    library: ControlLibrary,
) -> dict[str, list[dict[str, str]]]:
    """Return a deterministic mapping from MCP-001..008 pattern IDs to NIST SP 800-53r5 controls."""
    crosswalk: dict[str, list[dict[str, str]]] = {}
    for uc_id, overlay in library.overlays.items():
        for rule in overlay.tailored_controls:
            ctrl = library.controls[rule.control_id]
            for pat_id in rule.pattern_refs:
                crosswalk.setdefault(pat_id, []).append(
                    {
                        "control_id": ctrl.id,
                        "control_title": ctrl.title,
                        "use_case_id": uc_id,
                        "priority": rule.overlay_priority,
                    }
                )

    for pat_id in crosswalk:
        crosswalk[pat_id].sort(
            key=lambda item: (_control_sort_key(item["control_id"]), item["use_case_id"])
        )
    return dict(sorted(crosswalk.items()))
