# AGENTS.md — NIST SP 800-53 Rev. 5 (Update 1) & COSIS Security Controls Library

## 1. What This Repository Is
A deterministic, zero-fabrication **Security Controls & Overlay Library** anchored to two authoritative NIST sources:
1. **NIST SP 800-53 Rev. 5, Update 1 (Final)** — *Security and Privacy Controls for Information Systems and Organizations* (`https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final`) and its machine-readable OSCAL catalog (`usnistgov/oscal-content`).
2. **NIST COSIS Use Cases** — *SP 800-53 Control Overlays for Super Intelligence Systems* (formerly *COSAiS*, `https://csrc.nist.gov/projects/cosis/use-cases`), covering Generative SI (`UC-GEN`), Predictive SI (`UC-PRED`), Single-Agent SI (`UC-AGENT-SINGLE`), Multi-Agent SI (`UC-AGENT-MULTI`), and SI Developers (`UC-DEV`).

It also provides bidirectional crosswalks to [`bsommers/secure-design-patterns`](https://github.com/bsommers/secure-design-patterns) (`MCP-001`..`MCP-008`) and [`bsommers/forge`](https://github.com/bsommers/forge).

## 2. Canonical Commands (Run from Repository Root)
- **Validate all catalogs, 20 families, 5 COSIS overlays, crosswalks & Markdown links:**
  ```bash
  python3 scripts/validate_controls.py
  ```
- **Resolve an effective control profile for a COSIS use case (CLI):**
  ```bash
  PYTHONPATH=src python3 -m security_controls.cli resolve --use-case UC-AGENT-SINGLE --baseline moderate
  ```
- **Export a NIST OSCAL 1.1.2 Profile JSON:**
  ```bash
  PYTHONPATH=src python3 -m security_controls.cli export-oscal --use-case UC-AGENT-MULTI --output output/uc-agent-multi.oscal-profile.json
  ```
- **Run full test suite, linter & strict typechecker:**
  ```bash
  pytest -v
  ruff check src scripts tests
  MYPYPATH=src mypy --strict -p security_controls -p scripts
  ```

## 3. Non-Negotiable Grounding Rules
1. **Zero Fabricated Control IDs or Titles:** Every control in `catalog/sp800-53-r5-upd1/core-controls.json` MUST match an authentic NIST SP 800-53 Rev. 5 (Update 1) family (`AC`..`SR`), identifier (e.g., `AC-6(10)`, `SC-39`, `SI-7(1)`), and official control title.
2. **Deterministic Compliance Decisions:** Control selection, baseline filtering (`low`, `moderate`, `high`), COSIS overlay parameterization, and OSCAL 1.1.2 profile generation MUST be 100% deterministic—same inputs produce byte-identical outputs.
3. **Explicit Provenance Markers:** Distinguish normative NIST SP 800-53 Rev. 5 Update 1 controls (`normative_sp800_53r5_upd1`) from COSIS use-case tailoring guidance (`nist_cosis_use_case_overlay`) and engineering pattern crosswalks (`engineering_pattern_mapping`).
