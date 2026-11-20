# NIST COSIS Use Cases & SP 800-53 Rev. 5 (Update 1) Overlays

[← Back to Project README](../README.md) · [Pattern Crosswalk](CROSSWALK_MCP_PATTERNS.md) · [M1 Research Spike](plans/01-research-spike-oscal-cosis-automated-overlay-compilation.md)

## 1. Authoritative Foundation

- **Base Control Catalog:** [NIST SP 800-53 Rev. 5, Update 1 (Final)](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) — *Security and Privacy Controls for Information Systems and Organizations* (20 outcome-based security & privacy control families).
- **AI / Super Intelligence Overlay Initiative:** [NIST COSIS Use Cases](https://csrc.nist.gov/projects/cosis/use-cases) — *SP 800-53 Control Overlays for Super Intelligence Systems* (formerly *Control Overlays for Securing AI Systems / COSAiS*).

Instead of inventing a disconnected AI compliance checklist, NIST COSIS tailors SP 800-53 Rev. 5 baselines (`Low`, `Moderate`, `High`, `Privacy`) through **parameter assignments (`set-parameters`)**, **supplemental implementation guidance (`alters`)**, and **use-case-specific control selections**.

---

## 2. The Five Official NIST COSIS Use Cases

| Use Case ID | Official NIST COSIS Use Case | Default Baseline | Primary Threat Focus | Tailored SP 800-53r5 Controls in Library |
|-------------|------------------------------|:----------------:|----------------------|------------------------------------------|
| **`UC-GEN`** | **Adapting and Using Generative SI – Assistant / Large Language Model (LLM)** | `moderate` | Prompt injection, RAG cross-tenant leakage, PII exposure in context, unbounded payload/token exhaustion | `AC-4`, `AU-3`, `CA-7`, `PT-2`, `SC-5`, `SI-10` |
| **`UC-PRED`** | **Using and Fine-Tuning Predictive SI** | `moderate` | Training/fine-tuning data poisoning, model inversion, feature/concept drift, unverified checkpoint provenance | `CA-7`, `MP-2`, `PT-2`, `SI-7`, `SI-10`, `SR-4` |
| **`UC-AGENT-SINGLE`** | **Using SI Agent Systems (SI Agents) – Single Agent** | `moderate` | Excessive agency, destructive tool calls, confused-deputy token passthrough, host sandbox escape | `AC-6`, `AC-6(10)`, `CM-7`, `IR-4`, `SC-5`, `SC-7`, `SC-39` |
| **`UC-AGENT-MULTI`** | **Using SI Agent Systems (SI Agents) – Multi-Agent** | `high` | Inter-agent lateral movement, worker reward-hacking of shared test gates, cross-agent state bleed, cascade loops | `AC-4`, `AC-6(1)`, `AU-6`, `IA-9`, `SC-5`, `SI-7(1)` |
| **`UC-DEV`** | **Security Controls for SI Developers** *(SP 800-218A SSDF Aligned)* | `moderate` | Unpinned CI supply chain, `$ref` build-time SSRF, template drift, LLM self-grading compliance gates | `CA-2`, `CM-2`, `CM-5`, `SA-8`, `SA-11`, `SA-15`, `SR-3` |

---

## 3. Composing Multiple COSIS Overlays

Real production systems frequently span **multiple COSIS use cases simultaneously**. For example, **MCP Server Forge (`bsommers/forge`)** combines:
- `UC-DEV` (building and verifying AI tool servers in CI),
- `UC-AGENT-SINGLE` (forged FastMCP servers invoked by an autonomous agent), and
- `UC-AGENT-MULTI` (multi-shard / multi-agent synthesis and orchestration).

`security-controls` resolves composite profiles deterministically:

```bash
PYTHONPATH=src python3 -m security_controls.cli resolve \
  --use-case UC-AGENT-SINGLE \
  --use-case UC-AGENT-MULTI \
  --use-case UC-DEV \
  --baseline high
```
