# Upstream Source Data (`input/`)

This directory holds read-only upstream NIST OSCAL artifacts fetched during local ingestion or Milestone **M1 Research Spike** experiments (git-ignored except for this `README.md`).

## Authoritative Upstream Sources

1. **NIST SP 800-53 Rev. 5, Update 1 (Final)**
   - **Publication Page:** `https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final`
   - **Official Machine-Readable OSCAL Repository:** `https://github.com/usnistgov/oscal-content`
   - **Catalog Path in Upstream Repo:** `nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json`
   - **SP 800-53B Baselines:** `nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_{LOW,MODERATE,HIGH,PRIVACY}-baseline_profile.json`
2. **NIST COSIS (Control Overlays for Super Intelligence Systems — formerly COSAiS)**
   - **Project & Use Cases Page:** `https://csrc.nist.gov/projects/cosis/use-cases`

## Fetching Upstream OSCAL JSON (Optional Local Refresh)

```bash
curl -fsSL \
  https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json \
  -o input/NIST_SP-800-53_rev5_catalog.json
```
