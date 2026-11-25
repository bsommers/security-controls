"""Deterministic NIST OSCAL 1.1.2 Profile JSON exporter & official schema validator."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from security_controls.models import ResolvedProfile

# Deterministic UUIDv5 namespace so identical inputs produce byte-identical OSCAL JSON
COSIS_OSCAL_NAMESPACE = uuid.UUID("9c8b4f12-4c79-4d8c-9e42-7f55a6078053")
OSCAL_VERSION = "1.1.2"
DETERMINISTIC_LAST_MODIFIED = "2026-11-21T00:00:00Z"
UPSTREAM_SP800_53_OSCAL_HREF = (
    "https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/"
    "nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
)

# NIST Metaschema emits ECMA-262 Unicode property escapes (\p{L}, \p{N}, \p{Z}, \P{C})
# inside oscal_profile_schema.json pattern strings; translate them in-memory for Python `re`
# so schema/oscal_profile_schema.json stays byte-for-byte identical to NIST's v1.1.2 release.
_ECMA_UNICODE_MAP: tuple[tuple[str, str], ...] = (
    (r"\p{L}", r"A-Za-z\u00C0-\u024F"),
    (r"\p{Nl}", r"\u2160-\u2188"),
    (r"\p{N}", r"0-9"),
    (r"\p{Nd}", r"0-9"),
    (r"\p{Mc}", r"\u0300-\u036F"),
    (r"\p{Me}", r"\u20DD-\u20E0"),
    (r"\p{Mn}", r"\u0300-\u036F"),
    (r"\p{Pc}", r"_"),
    (r"\p{Cf}", r"\u200B-\u200F"),
    (r"\p{Cs}", r"\uD800-\uDFFF"),
    (r"\p{C}", r"\x00-\x1F\x7F"),
    (r"\P{C}", r"^\x00-\x1F\x7F"),
    (r"\p{Z}", r" \t\u00A0"),
    (r"\P{Z}", r"\S"),
)


def _translate_ecma_pattern(pat: str) -> str:
    # Handle character-class vs standalone escapes cleanly
    out = pat
    for src, repl in _ECMA_UNICODE_MAP:
        if src in {r"\P{Z}", r"\P{C}"}:
            continue
        wrapped = f"[{repl}]"

        def _wrap(_m: re.Match[str], w: str = wrapped) -> str:
            return w

        out = re.sub(r"(?<!\[)" + re.escape(src), _wrap, out)
        out = out.replace(src, repl)
    out = out.replace(r"\P{Z}", r"\S").replace(r"\P{C}", r"[^\x00-\x1F\x7F]")
    return out


def to_oscal_control_id(control_id: str) -> str:
    """Convert NIST prose ID ('AC-6(10)' or 'SI-7') to OSCAL canonical ID ('ac-6.10' or 'si-7')."""
    lowered = control_id.strip().lower()
    if "(" in lowered and lowered.endswith(")"):
        base, enh = lowered[:-1].split("(", 1)
        return f"{base}.{int(enh)}"
    return lowered


def build_oscal_profile(profile: ResolvedProfile) -> dict[str, Any]:
    """Emit a deterministic NIST OSCAL 1.1.2 Profile JSON dictionary conforming to NIST schema."""
    profile_key = f"nist-cosis:{profile.baseline}:{'+'.join(profile.use_case_ids)}"
    deterministic_uuid = str(uuid.uuid5(COSIS_OSCAL_NAMESPACE, profile_key))

    with_ids = [to_oscal_control_id(ec.control.id) for ec in profile.controls]
    param_values: dict[str, str] = {}
    alters: list[dict[str, Any]] = []

    for ec in profile.controls:
        oscal_cid = to_oscal_control_id(ec.control.id)
        for param_id, val in sorted(ec.parameter_assignments.items()):
            param_values[param_id] = val
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

    set_parameters = [
        {"param-id": pid, "values": [val]} for pid, val in sorted(param_values.items())
    ]

    return {
        "profile": {
            "uuid": deterministic_uuid,
            "metadata": {
                "title": (
                    f"NIST SP 800-53r5 Update 1 COSIS Profile "
                    f"({', '.join(profile.use_case_ids)} @ {profile.baseline})"
                ),
                "last-modified": DETERMINISTIC_LAST_MODIFIED,
                "version": "1.1.0",
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


def validate_oscal_profile_schema(
    oscal_doc: dict[str, Any],
    schema_path: Path,
) -> list[str]:
    """Validate an emitted OSCAL 1.1.2 Profile JSON document against NIST's official JSON Schema."""
    try:
        from jsonschema import Draft7Validator, ValidationError, validators
    except ImportError:
        return []

    def _ecma_pattern(
        _validator: Any, patrn: str, instance: Any, _schema: Any
    ) -> Any:
        if isinstance(instance, str):
            py_pat = _translate_ecma_pattern(patrn)
            if not re.search(py_pat, instance):
                yield ValidationError(f"{instance!r} does not match {patrn!r}")

    oscal_validator_cls = validators.extend(  # type: ignore[no-untyped-call]
        Draft7Validator, {"pattern": _ecma_pattern}
    )
    schema_obj = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = oscal_validator_cls(schema_obj)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(oscal_doc), key=lambda e: list(e.absolute_path)):
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors
