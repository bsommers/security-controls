#!/usr/bin/env python3
"""Deterministic repository validator for NIST SP 800-53r5 Update 1 & COSIS controls."""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from security_controls.loader import CatalogIntegrityError, load_library  # noqa: E402
from security_controls.oscal import build_oscal_profile  # noqa: E402
from security_controls.resolver import resolve_effective_profile  # noqa: E402

MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(((?:[^()]|\([^()]*\))+)\)")


def _strip_fenced_code(md_text: str) -> str:
    return re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)


def validate_all(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        lib = load_library(root)
    except CatalogIntegrityError as exc:
        return [str(exc)]

    # Verify every COSIS overlay resolves cleanly and produces valid OSCAL 1.1.2 JSON
    for uc_id in lib.use_cases:
        prof = resolve_effective_profile(lib, use_case_ids=[uc_id])
        oscal = build_oscal_profile(prof)
        if oscal["profile"]["metadata"]["oscal-version"] != "1.1.2":
            errors.append(f"{uc_id}: invalid oscal-version")
        if not oscal["profile"]["modify"]["set-parameters"]:
            errors.append(f"{uc_id}: expected non-empty OSCAL set-parameters")

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
    print(
        f"[PASS] Validated {len(lib.families)} NIST SP 800-53r5 Update 1 families, "
        f"{len(lib.controls)} core controls, and {len(lib.overlays)} COSIS use-case overlays."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
