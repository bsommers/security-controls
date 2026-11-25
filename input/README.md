# Upstream Source Data (`input/`)

This directory holds read-only upstream NIST OSCAL bulk source files fetched during local index refreshes (git-ignored except for this `README.md`; compiled output is checked into [`../catalog/sp800-53-r5-upd1/full-index.json`](../catalog/sp800-53-r5-upd1/full-index.json) at `298.91 KiB`).

## Pinned Upstream Artifacts & SHA-256 Digests (`usnistgov/oscal-content@v1.1.0` — SP 800-53 Rev. 5.1.1)

| File | Bytes | SHA-256 Digest | Pinned Upstream URL |
|------|------:|----------------|---------------------|
| `NIST_SP-800-53_rev5_catalog.json` | `9,361,316` | `6c39acc31c7d492a80acd6dd2af0ebc19bf8084974fd38ac9ed684a56beef3ac` | `https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json` |
| `NIST_SP-800-53_rev5_LOW-baseline_profile.json` | `6,007` | `9e2eb97a5fc6e4f709179d62f29334c487bf035ff19467f1d874392ac910dc3a` | `https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_LOW-baseline_profile.json` |
| `NIST_SP-800-53_rev5_MODERATE-baseline_profile.json` | `9,271` | `9c0941360d5219b2f56c1ddf76b891aa7eb8024ea04b59db9c57cdcdee05e4d7` | `https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_MODERATE-baseline_profile.json` |
| `NIST_SP-800-53_rev5_HIGH-baseline_profile.json` | `11,265` | `fec6b69185af95d78243b48235a1036bb8b13ece3df48435db4f7de1e65348e5` | `https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_HIGH-baseline_profile.json` |
| `NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json` | `4,837` | `11380a0fc5b69acbdfcccc0fce3efd20650849080b90a654ea67937e706c023f` | `https://raw.githubusercontent.com/usnistgov/oscal-content/v1.1.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_PRIVACY-baseline_profile.json` |
| `oscal_profile_schema.json` *(also committed in `../schema/`)* | `53,876` | `c910ea1a852e9d4ccfb7f6a8d0898b0cd4f137e48f88886412a083c8d87d540a` | `https://github.com/usnistgov/OSCAL/releases/download/v1.1.2/oscal_profile_schema.json` |

## Refreshing & Recompiling Locally

```bash
uv run python scripts/spike_ingest_oscal.py
```
