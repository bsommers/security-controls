# Generated Artifacts (`output/`)

This directory holds reproducible OSCAL 1.1.2 Profile JSON documents and resolved control matrices emitted by `security-controls` (git-ignored except for this `README.md`).

## Regenerating Outputs

```bash
PYTHONPATH=src python3 -m security_controls.cli export-oscal \
  --use-case UC-AGENT-SINGLE \
  --output output/uc-agent-single.oscal-profile.json

PYTHONPATH=src python3 -m security_controls.cli export-oscal \
  --use-case UC-AGENT-MULTI \
  --output output/uc-agent-multi.oscal-profile.json
```
