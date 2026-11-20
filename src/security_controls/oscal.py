"""Deterministic NIST OSCAL 1.1.2 Profile JSON exporter for resolved COSIS control profiles."""

from __future__ import annotations

import uuid
from typing import Any

from security_controls.models import ResolvedProfile

# Deterministic UUIDv5 namespace so identical inputs produce byte-identical OSCAL JSON
COSIS_OSCAL_NAMESPACE = uuid.UUID("9c8b4f12-4c79-4d8c-9e42-7f55a6078053")
OSCAL_VERSION = "1.1.2"
UPSTREAM_SP800_53_OSCAL_HREF = (
    "https://raw.githubusercontent.com/usnistgov/oscal-content/main/"
    "nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
)


def to_oscal_control_id(control_id: str) -> str:
    """Convert NIST prose ID ('AC-6(10)' or 'SI-7') to OSCAL canonical ID ('ac-6.10' or 'si-7')."""
    lowered = control_id.strip().lower()
    if "(" in lowered and lowered.endswith(")"):
        base, enh = lowered[:-1].split("(", 1)
        return f"{base}.{int(enh)}"
    return lowered


def build_oscal_profile(profile: ResolvedProfile) -> dict[str, Any]:
    """Emit a deterministic NIST OSCAL 1.1.2 Profile JSON dictionary."""
    profile_key = f"nist-cosis:{profile.baseline}:{'+'.join(profile.use_case_ids)}"
    deterministic_uuid = str(uuid.uuid5(COSIS_OSCAL_NAMESPACE, profile_key))

    with_ids = [to_oscal_control_id(ec.control.id) for ec in profile.controls]
    set_parameters: list[dict[str, Any]] = []
    alters: list[dict[str, Any]] = []

    for ec in profile.controls:
        oscal_cid = to_oscal_control_id(ec.control.id)
        for param_id, val in sorted(ec.parameter_assignments.items()):
            set_parameters.append(
                {
                    "param-id": param_id,
                    "values": [val],
                }
            )
        if ec.tailoring_guidance:
            parts: list[dict[str, Any]] = [
                {
                    "name": "guidance",
                    "ns": "https://csrc.nist.gov/ns/cosis",
                    "prose": "\n".join(ec.tailoring_guidance),
                }
            ]
            if ec.pattern_refs:
                parts.append(
                    {
                        "name": "secure-design-patterns",
                        "ns": "https://github.com/bsommers/secure-design-patterns",
                        "prose": ", ".join(ec.pattern_refs),
                    }
                )
            alters.append(
                {
                    "control-id": oscal_cid,
                    "adds": [{"position": "ending", "parts": parts}],
                }
            )

    return {
        "profile": {
            "uuid": deterministic_uuid,
            "metadata": {
                "title": (
                    f"NIST SP 800-53r5 Update 1 COSIS Profile "
                    f"({', '.join(profile.use_case_ids)} @ {profile.baseline})"
                ),
                "version": "1.0.0",
                "oscal-version": OSCAL_VERSION,
                "props": [
                    {
                        "name": "source-catalog",
                        "value": "https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final",
                    },
                    {
                        "name": "cosis-use-cases-source",
                        "value": "https://csrc.nist.gov/projects/cosis/use-cases",
                    },
                    {
                        "name": "baseline",
                        "value": profile.baseline,
                    },
                ],
            },
            "imports": [
                {
                    "href": UPSTREAM_SP800_53_OSCAL_HREF,
                    "include-controls": [{"with-ids": with_ids}],
                }
            ],
            "merge": {"as-is": True},
            "modify": {
                "set-parameters": set_parameters,
                "alters": alters,
            },
        }
    }
