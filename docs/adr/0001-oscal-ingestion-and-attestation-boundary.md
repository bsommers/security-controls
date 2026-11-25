# ADR-0001 — Upstream NIST OSCAL 5.1.1 Full-Catalog Indexing, Metaschema Validation & Deterministic SP 800-53A Boundary

- **Status:** Accepted (`Milestone M1 — v1.1.0`)
- **Date:** 2026-11-21
- **Spike Plan:** [`../plans/01-research-spike-oscal-cosis-automated-overlay-compilation.md`](../plans/01-research-spike-oscal-cosis-automated-overlay-compilation.md)

---

## 1. Context & Empirical Questions

Before promoting `security-controls` beyond its curated 45-control `M0 (v1.0.0)` core catalog, Milestone **M1 (`v1.1.0`)** executed four falsifiable experiments (`RS-1`–`RS-4`) against upstream NIST repositories (`usnistgov/oscal-content` and `usnistgov/OSCAL`).

---

## 2. Empirical Results

| Spike ID | Target Criterion | Measured Result (Apple Silicon M-series, CPython) | Verdict |
|----------|------------------|---------------------------------------------------|:-------:|
| **RS-1** | Parse all 20 groups & `>= 1,000` active controls in `< 150 ms`; compact index `< 600 KiB`; `< 100 ms` cold load; `0` mismatches vs. `core-controls.json` | **`1,189` total controls & enhancements** (`322` base + `867` enhancements = `1,007` active + `182` withdrawn across `20` groups) from `usnistgov/oscal-content@v1.1.0` (`Rev. 5.1.1`). Compile median: **`33.55 ms`**; compiled `full-index.json`: **`298.91 KiB`** (`306,083` B); cold load median: **`2.26 ms`**; mismatches: **`0 / 45`**. | **PASS** |
| **RS-2** | Separate upstream `[NIST-DRAFT]` COSIS overlays from org-specific `MCP-001..008` engineering tailoring (`0` unattributed assertions) | Added `source_provenance` (`upstream_cosis_source` tagged `[NIST-DRAFT]` + `organization_tailoring` anchored to `bsommers/secure-design-patterns@MCP-2026-07-28`) and per-rule `source_tier` across all `5` COSIS overlays; `Draft202012Validator` errors: **`0`**. | **PASS** |
| **RS-3** | `5 / 5` exported COSIS profiles validate against official NIST `oscal_profile_schema.json` (`v1.1.2`) with `0` errors | Added required `metadata.last-modified` (`2026-11-21T00:00:00Z`), deduplicated `set-parameters`, and added an in-memory ECMA-262 `\p{...}` Unicode property regex adapter so verbatim NIST `oscal_profile_schema.json` (`53,876` B, SHA-256 `c910ea1a...`) validates **`5 / 5` single profiles + composite profiles with `0` errors**. | **PASS** |
| **RS-4** | Deterministically evaluate `>= 70%` of technical `P1` controls in `UC-AGENT-SINGLE` + `UC-DEV` while prohibiting LLM self-attestation on human controls | `security_controls.assessor.assess_forge_bundle()` deterministically evaluates **`100%` of technical `P1` controls** from Forge Stage 4–5 artifacts while quarantining `AT-3`, `PE-3`, `PM-9`, and `PS-6` as `human-attestation-required`. | **PASS** |

---

## 3. Key Technical Findings & Decisions

1. **Upstream `usnistgov/oscal-content` Version Drift Across Git Refs:**
   - `usnistgov/oscal-content@v1.1.0` corresponds to exact **SP 800-53 Rev. 5 Update 1 (`version: 5.1.1`)** with **`1,189`** controls & enhancements (`322` base + `867` enhancements; `1,007` active, `182` withdrawn).
   - Newer upstream tags (`v1.2.0` -> `5.1.1+u2` with `1,193` controls; `main` -> `5.2.0` with `1,196` controls) add SP 800-53r5 Patch 1 controls (such as `SA-15(13)`). Pinning `v1.1.0` by exact URL + SHA-256 in [`input/README.md`](../../input/README.md) guarantees reproducible builds while keeping `compile_upstream_oscal_catalog()` compatible with `5.2.0` upgrades.
2. **NIST Metaschema ECMA-262 Regex Compatibility in Python:**
   - Official NIST OSCAL `1.1.2` JSON Schemas emit ECMA-262 Unicode property escapes (`\p{L}`, `\p{N}`, `\p{Z}`, `\P{C}`) inside `"pattern"` keywords, which raise `re.PatternError: bad escape \p` in Python's stdlib `re` engine.
   - **Decision:** Keep `schema/oscal_profile_schema.json` 100% byte-identical to NIST's published `v1.1.2` release (`c910ea1a852e9d4ccfb7f6a8d0898b0cd4f137e48f88886412a083c8d87d540a`) and translate ECMA-262 Unicode classes in memory inside `validate_oscal_profile_schema()` via `jsonschema.validators.extend`.
3. **Strict Machine vs. Human Attestation Partition (`CA-2`):**
   - Automated gates (`validate_mcp.py`, `assess_forge_bundle`) are authoritative only for deterministic technical controls (`AC-6`, `AC-6(1)`, `AC-6(10)`, `CM-2`, `CM-5`, `CM-7`, `SA-8`, `SA-11`, `SC-5`, `SC-7`, `SC-39`, `SI-7(1)`, `SI-10`, `SR-3`).
   - Organizational and personnel controls (`AT-3`, `PE-3`, `PM-9`, `PS-6`) MUST emit `assessor_type = "human-attestation-required"` and `state = "other-than-satisfied"` until signed off by a named Authorizing Official.

---

## 4. Go / No-Go Decision

**GO for M2 (`v1.2.0`) & Production Integration:** All four spike gates (`RS-1`–`RS-4`) and `hypothesis` monotonicity fuzzing passed quantitatively. Both `security_controls.full_index` (`1,189` controls) and `security_controls.assessor` are promoted directly into the `src/security_controls/` library and wired into CI.
