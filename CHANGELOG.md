# Changelog

All notable changes to the **Security Controls Library (`security-controls`)** are documented here.

## [1.0.0] - 2026-11-19

### Added
- **NIST SP 800-53 Rev. 5 (Update 1) Catalog (`catalog/sp800-53-r5-upd1/`)**:
  - All 20 official control families (`AC`, `AT`, `AU`, `CA`, `CM`, `CP`, `IA`, `IR`, `MA`, `MP`, `PE`, `PL`, `PM`, `PS`, `PT`, `RA`, `SA`, `SC`, `SI`, `SR`) grounded in `https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final`.
  - Curated core catalog of 40 SP 800-53r5 Update 1 controls and control enhancements spanning every family with SP 800-53B (`low`, `moderate`, `high`, `privacy`) baseline tags and parameter definitions.
- **NIST COSIS Use-Case Overlays (`catalog/cosis/`)**:
  - Grounded in `https://csrc.nist.gov/projects/cosis/use-cases` (*SP 800-53 Control Overlays for Super Intelligence Systems*, formerly *COSAiS*):
    1. `UC-GEN`: Adapting and Using Generative SI – Assistant / Large Language Model (LLM)
    2. `UC-PRED`: Using and Fine-Tuning Predictive SI
    3. `UC-AGENT-SINGLE`: Using SI Agent Systems (SI Agents) – Single Agent
    4. `UC-AGENT-MULTI`: Using SI Agent Systems (SI Agents) – Multi-Agent
    5. `UC-DEV`: Security Controls for SI Developers (aligned with NIST SP 800-218 / SP 800-218A SSDF)
- **Deterministic Resolver, OSCAL 1.1.2 Profile Exporter & CLI (`src/security_controls/`)**:
  - Multi-overlay composition (`resolve_effective_controls`), OSCAL 1.1.2 Profile JSON emitter (`export_oscal_profile`), and bidirectional crosswalks to [`bsommers/secure-design-patterns`](https://github.com/bsommers/secure-design-patterns) (`MCP-001`–`MCP-008`).
- **Milestone M1 Research Spike Plan (`docs/ROADMAP.md`, `docs/plans/01-research-spike-oscal-cosis-automated-overlay-compilation.md`)**:
  - Scoped next-milestone research spike on full `usnistgov/oscal-content` ingestion, automated SP 800-53A assessment rule execution, and live MCP server SSP attestation.
