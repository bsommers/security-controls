# Plan 01 — Research Spike: Upstream NIST OSCAL Ingestion, COSIS Draft Schema Alignment & Automated SP 800-53A Assessment (`Milestone M1`)

- **Status:** `open` *(Next Active Milestone)*
- **Milestone:** `M1 (v1.1.0 — Research Spike)` in [`../ROADMAP.md`](../ROADMAP.md)
- **Timebox:** 3–5 focused engineering sessions
- **Authoritative Anchors:**
  - NIST SP 800-53 Rev. 5, Update 1: `https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final`
  - NIST COSIS Use Cases: `https://csrc.nist.gov/projects/cosis/use-cases`
  - NIST OSCAL Content Repository: `https://github.com/usnistgov/oscal-content`
- **Companion Repos:** [`bsommers/secure-design-patterns`](https://github.com/bsommers/secure-design-patterns) · [`bsommers/forge`](https://github.com/bsommers/forge)

[← Back to Roadmap](../ROADMAP.md) · [← Back to Project README](../../README.md)

---

## 1. Spike Objective & Problem Statement

In **M0 (`v1.0.0`)**, `security-controls` establishes a curated, deterministic 45-control catalog spanning all 20 NIST SP 800-53 Rev. 5 (Update 1) families, overlays for all 5 official **NIST COSIS** (*Control Overlays for Super Intelligence Systems*) use cases, and an OSCAL 1.1.2 Profile exporter.

Before scaling to **M2 (`v1.2.0`)** full-catalog compliance automation, four empirical unknowns require a disciplined **Research Spike** rather than speculative engineering:

1. **Upstream OSCAL Scale & Parameter Syntax (`usnistgov/oscal-content`):** The complete NIST SP 800-53r5 Update 1 OSCAL JSON (`~10+ MiB`, `1,189` base controls + control enhancements, nested `{{ insert: param, ... }}` prose substitutions, and `withdrawn` enhancements) is heavy and uses complex nested `parts`/`props`. Can we ingest and index the full upstream OSCAL JSON offline in `< 150 ms` using Python stdlib alone without bloating repo clones?
2. **NIST COSIS Draft Publication Evolution:** NIST's COSIS project (renamed from *COSAiS*) publishes evolving per-use-case draft overlays (`UC-GEN`, `UC-PRED`, `UC-AGENT-SINGLE`, `UC-AGENT-MULTI`, `UC-DEV`). What intermediate schema cleanly separates **verbatim NIST-published COSIS overlay parameters** from **organization-specific engineering overlays** (like `MCP-001..008`) with zero provenance ambiguity?
3. **OSCAL Profile Resolution Compatibility:** Do downstream compliance engines (`oscal-cli`, `compliance-trestle`) accept our emitted OSCAL 1.1.2 `profile` JSON (`imports`, `set-parameters`, `alters`) without schema warnings?
4. **Automated SP 800-53A Evidence Mapping (`forge` Integration):** Which SP 800-53r5 controls in `UC-AGENT-SINGLE`, `UC-AGENT-MULTI`, and `UC-DEV` can be **100% machine-attested** from deterministic build/runtime artifacts (e.g., `forge-release-artifacts.json` + `validate_mcp.py` 5-gate logs), versus controls requiring human/organizational attestation (`AT-3`, `PS-6`, `PE-3`, `PM-9`)?

---

## 2. Falsifiable Hypotheses & Spike Experiments

| Spike ID | Hypothesis | Experiment / Prototype | Quantitative Pass Criterion |
|----------|------------|------------------------|-----------------------------|
| **RS-1** | **Compact Upstream OSCAL Indexing:** We can deterministically compile `NIST_SP-800-53_rev5_catalog.json` + Low/Mod/High/Privacy profile JSONs from `input/` into a compact normalized index (`< 600 KiB`) that loads in `< 100 ms` with zero external runtime dependencies. | Write `scripts/spike_ingest_oscal.py` parsing upstream OSCAL `groups -> controls -> controls (enhancements)`, resolving `{{ insert: param, ... }}` placeholders, and skipping `status=withdrawn` controls. | Parses all 20 groups & `>= 1,000` active controls/enhancements in `< 150 ms`; 100% match against `core-controls.json` IDs & titles. |
| **RS-2** | **Two-Layer Provenance Separation:** Splitting overlay rules into `upstream_cosis_source` (citing exact NIST COSIS section/draft ID or `[PENDING_NIST_FINAL_PUBLICATION]`) vs. `organization_tailoring` prevents LLM/human compliance drift. | Prototype v2 `cosis-overlay.schema.json` provenance block and run `grounding-ai-outputs` audit checklist across all 5 overlays. | `0` unattributed assertions; every parameter assignment carries an explicit source tier (`nist_sp800_53b`, `nist_cosis_draft`, or `org_pattern_tailoring`). |
| **RS-3** | **External OSCAL Schema Interoperability:** Profiles emitted by `security_controls.oscal.build_oscal_profile()` validate cleanly against the official NIST OSCAL `1.1.2` JSON Schema (`oscal_profile_schema.json`). | Fetch official NIST `oscal_profile_schema.json` into `input/` and validate all 5 exported COSIS profiles (`output/*.oscal-profile.json`) against it. | `5 / 5` exported profiles pass official NIST OSCAL 1.1.2 JSON Schema validation with `0` schema errors. |
| **RS-4** | **Deterministic SP 800-53A Automated Attestation Boundary:** At least `70%` of technical `P1` controls in `UC-AGENT-SINGLE` + `UC-DEV` (`AC-6`, `AC-6(10)`, `CM-2`, `CM-5`, `CM-7`, `SA-8`, `SA-11`, `SC-5`, `SC-7`, `SC-39`, `SI-7(1)`, `SI-10`, `SR-3`) can be automatically evaluated to `satisfied` / `other-than-satisfied` from `bsommers/forge` Stage 4–5 artifacts, while non-technical controls (`AT-3`, `PE-3`, `PM-9`, `PS-6`) are explicitly marked `human_attestation_required`. | Prototype `spike_assess_forge_bundle.py` consuming `forge-manifest.json` + `forge-release-artifacts.json` and emitting a candidate OSCAL `assessment-results` summary. | Deterministic evaluator classifies technical vs. human-attested controls with `100%` repeatability and zero LLM-in-the-loop grading. |

---

## 3. Non-Negotiable Grounding Guardrails During Spike

1. **No LLM Compliance Arbiters:** Per `grounding-ai-outputs`, an LLM may assist in drafting prose summaries offline, **never** in computing `satisfied` / `not-satisfied` control status at runtime.
2. **Explicit `[UNKNOWN]` / `[NIST-DRAFT]` Tags:** Wherever a NIST COSIS use-case overlay (`UC-PRED`, `UC-AGENT-MULTI`, etc.) is still in draft public-comment status at NIST CSRC, tag the provenance metadata explicitly rather than presenting draft tailoring as finalized federal mandate.
3. **Keep Upstream Bulk Files in `input/`:** Never commit multi-megabyte raw `usnistgov/oscal-content` clones into git; record exact upstream URL + SHA-256 hash in `input/README.md` and commit only deterministic compiled indexes and schemas.

---

## 4. Spike Deliverables & Go / No-Go Exit Gate

At the conclusion of **M1 (`v1.1.0`)**, produce:
1. **`docs/adr/0001-oscal-ingestion-and-attestation-boundary.md`** — Recording empirical timings (`RS-1`), official OSCAL schema validation results (`RS-3`), and the exact partition between machine-attested technical controls vs. human-attested organizational controls (`RS-4`).
2. **Validated OSCAL 1.1.2 Profile Schema Gate** wired into CI.
3. **Go / No-Go Decision for `M2` (`v1.2.0`):** Proceed to build `security_controls.assessor` and the `forge` Stage 5 OSCAL SSP emitter only if `RS-1`, `RS-3`, and `RS-4` meet all quantitative pass criteria above.
