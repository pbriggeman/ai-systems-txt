# ai-systems.txt — A Reverse robots.txt for AI System Capabilities

**Specification Draft v0.2 — 2026-10-31**
Authors: Peter Briggeman (originator) and Jevex (editor)
Status: Public draft for discussion. This is not an IETF document and has no formal standing. It is published in the hope of being adopted, adapted, or superseded by a proper standards process.
License: CC BY 4.0 (specification text); MIT (reference validator code).

---

## 0. Abstract

This document defines `ai-systems.txt`, a plain-text file that an organisation that builds or deploys artificial intelligence systems publishes at a well-known location on its own domain. The file declares, in a machine-readable and human-readable form: which AI systems the organisation has released, what their measured capabilities are, who measured them, under what conditions, and where the evidence lives.

robots.txt tells machines what they may *take* from a publisher. `ai-systems.txt` is the reverse: it tells anyone — researchers, journalists, buyers, regulators, other machines, and capability monitors — what a maker *has built*, in a form designed from the first line to be checked rather than believed.

The design goal is a single sentence: **separate fact from rumor at the source.** Today, capability information reaches the public as launch marketing, cropped benchmark screenshots, leaks, and social-media claims, and independent parties (Epoch AI, METR, Artificial Analysis, the Stanford AI Index) must reconstruct the truth after the fact. This file gives makers a way to state the truth on the record — signed, timestamped, expiring, and falsifiable — and gives everyone else a deterministic procedure for grading what they hear.

## 1. Introduction

### 1.1 Problem statement

1. There is no canonical, maker-maintained record of what AI systems exist. The closest registry (Epoch AI's models database) is a third-party reconstruction, however excellent.
2. Capability claims are routinely published without the conditions that make them comparable (benchmark version, agent scaffold, reasoning effort, tool access, date).
3. Models are silently updated, renamed, and retired; yesterday's claim attaches to today's different system.
4. Rumor fills every gap. A rumored system or score cannot be confirmed *or denied* against any authoritative artefact, so rumor and fact circulate with equal weight.

### 1.2 What this file is

* A **declaration**: the maker's own signed statement, attributable and timestamped.
* A **claim index**: every capability claim carries its provenance tier (Section 7), so a reader can grade it without further research.
* A **feed**: monitors can fetch, hash, and diff the file on a schedule and report precisely what changed.

### 1.3 What this file is not

* It is **not** a trust mechanism by itself. A declaration can be wrong or dishonest; the format's defence is falsifiability (Section 14), not faith.
* It is **not** a content-permissions file. Training consent, crawling rules, and AI usage preferences for a publisher's *content* are the subject of `robots.txt`, the IETF `aipref` work, and the existing `ai.txt` proposals. This file governs claims about a maker's *systems*. (The name was chosen to avoid colliding with those proposals.)
* It is **not** a model card or system card. Those remain the right place for long-form discussion; this file *links* to them.
* It is **not** an agent interface description. A2A agent cards and MCP server cards describe how to *call* an agent; this file describes what a *system is and can do*, including systems with no public interface.

### 1.4 Conventions

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as described in RFC 2119. Grammar is given in ABNF (RFC 5234) in Section 4.3.

## 2. Provenance tiers — the core of the design

Every statement about a system falls into exactly one of four tiers. The file expresses the first three; the fourth is what a validator concludes about everything else.

| Tier | Meaning | Requirement |
|---|---|---|
| **ATTESTED** | An independent evaluator measured the claim and stands behind it in a checkable way. | Evaluation block with a named independent evaluator, an evidence URL, and an `Attestation` value: the SHA-256 hash of the evaluator's report, or the evaluator's countersignature reference. |
| **MEASURED** | A named evaluator measured and published the claim, with method and date. The evaluator may be independent or the maker, and the block MUST say which. | Evaluation block with evaluator (including the word `independent` if so), benchmark version, conditions, measured date, evidence URL. |
| **DECLARED** | The maker asserts the claim; no independent measurement is linked. | Any field or evaluation block not meeting the tiers above. Believable, citable, unverified. |
| **UNDECLARED** | The system or capability does not appear in a valid, unexpired file at all. | — (concluded by validators). This is the **rumor tier**: by definition, nothing here has been stated on the record by the maker. |

Two derived verdicts complete the vocabulary:

* **CONTRADICTED** — a claim in the file conflicts with the named evaluator's own published data or with the registry (beyond the tolerances in Section 12.3). A validator MUST surface both values.
* **STALE** — the claim appeared in a file whose `Expires` has passed. Stale claims revert to unverified until the file is renewed.

## 3. Location and discovery

1. The file MUST be served over HTTPS at `https://<domain>/.well-known/ai-systems.txt` (well-known URIs per RFC 8615).
2. A JSON mirror with identical content SHOULD be served at `https://<domain>/.well-known/ai-systems.json` (Section 11).
3. For compatibility, a maker MAY also serve the file at `/ai-systems.txt`; the well-known location takes precedence on any conflict.
4. A detached signature SHOULD be served at the file URL + `.sig` (Section 10).
5. Discovery hints (optional, any one suffices):
   * an HTTP response header: `Link: </.well-known/ai-systems.txt>; rel="ai-systems"; type="text/plain"`
   * a comment line in the maker's `robots.txt`: `# AI-Systems: https://<domain>/.well-known/ai-systems.txt`
6. The file applies to the domain it is served from. A maker with several domains serves one file per domain, or identical files whose `Canonical` lists each domain's URL.
7. Media type: `text/plain; charset=utf-8` (JSON mirror: `application/json`).

## 4. Format

### 4.1 General rules

* UTF-8 plain text. Lines are `Field-Name: value`. Field names are case-insensitive ASCII; values are case-sensitive unless a field definition says otherwise.
* Lines beginning with `#` are comments. Blank lines are ignored. Parsers MUST ignore fields they do not recognise (forward compatibility) and MUST NOT fail on them.
* The file has two parts: one **header block** (fields before the first `System` line), then one **stanza per system**. A stanza continues until the next `System` line or end of file.
* An **evaluation block** begins with an `Evaluation:` line inside a stanza; the evaluation-scoped fields that follow (`Evaluator`, `Score`, `Conditions`, `Measured`, `Evidence`, `Attestation`, `Tier`) belong to it until the next `Evaluation:` line or a non-evaluation field.
* Repeatable fields MAY appear multiple times; order of `Contact` and `Registry-ID` lines denotes preference/canonical-first.

### 4.2 Dates and numbers

* Dates are `YYYY-MM-DD`. Timestamps (`Expires`) are RFC 3339.
* Quantities SHOULD be given in plain scientific or decimal notation parseable by machines (e.g. `4.05e11`, `2.0e25`). Human suffixes (`405B`) are permitted in the text file but the JSON mirror MUST use plain numbers.

### 4.3 ABNF (informative summary)

```abnf
file        = header *( stanza )
header      = *( field-line / comment / blank )
stanza      = system-line *( field-line / eval-block / comment / blank )
system-line = "System:" SP value CRLF
eval-block  = eval-line *( eval-field )
eval-line   = "Evaluation:" SP value CRLF
eval-field  = ("Evaluator" / "Score" / "Conditions" / "Measured" /
               "Evidence" / "Attestation" / "Tier") ":" SP value CRLF
field-line  = field-name ":" SP value CRLF
comment     = "#" *( VCHAR ) CRLF
```

## 5. Header fields

| Field | Cards | Description |
|---|---|---|
| `AISystems-Version` | exactly 1, REQUIRED | Version of this specification the file conforms to. This draft: `0.1` files remain valid under 0.2 tooling; this document describes `0.2`. |
| `Publisher` | exactly 1, REQUIRED | The organisation making the declaration. |
| `Canonical` | 1+, REQUIRED | The URL(s) of this file. A validator MUST warn/distrust if the fetched URL is not listed (mirrors RFC 9116 practice). |
| `Contact` | 1+, REQUIRED | URI (mailto/https) for corrections and disputes about this file. Order = preference. |
| `Expires` | exactly 1, REQUIRED | RFC 3339 timestamp after which the contents MUST be treated as stale. MUST be less than one year after publication; 90 days is RECOMMENDED for frontier developers. |
| `Signature` | exactly 1, REQUIRED | URL of the detached signature for this exact file (Section 10). |
| `Systems-Index` | 0–1 | URL of the JSON mirror. |
| `Policy` | 0–1 | URL of the publisher's disclosure/transparency policy. |
| `Previous-Version` | 0–1 | URL of the immediately preceding version of this file, to make diffs discoverable. |

## 6. System stanza fields

| Field | Cards | Description |
|---|---|---|
| `System` | exactly 1, REQUIRED | Canonical name of the system. Unique within the file. |
| `Version` | exactly 1, REQUIRED | Version/build identifier. Any change to a served system that could alter capabilities MUST produce a new `Version` value in an updated file. |
| `Status` | exactly 1, REQUIRED | One of `research`, `preview`, `general-availability`, `deprecated`, `retired`. |
| `Released` | exactly 1, REQUIRED | Date the system first became available to anyone outside the publisher (including paid/closed previews; say so in a comment). |
| `Predecessor` | 0–1 | Name of the previous system in the line. |
| `Modalities` | exactly 1, REQUIRED | Comma list, e.g. `text-in, image-in, text-out, tool-use, code-execution`. |
| `Access` | exactly 1, REQUIRED | One or more of `api`, `open-weights`, `open-source`, `internal-only`; for open weights, include the licence in parentheses. |
| `Registry-ID` | 0+ | External identities, prefixed: `epoch:`, `openrouter:`, `huggingface:`, `api-model:`, or another registry prefix registered per Section 16. |
| `Endpoint` / `Repository` | 0+ | Where the system can actually be reached. |
| `Context-Window` | 0–1 | Maximum context, in tokens, **as served** — not as designed or announced. |
| `Parameters` | exactly 1, REQUIRED* | Parameter count, or `Undisclosed`. (*Required-or-explicitly-undisclosed*, Section 8.) |
| `Training-Compute` | exactly 1, REQUIRED* | Total training compute in FLOP with basis in parentheses where estimated, or `Undisclosed`. |
| `Training-Data-Cutoff` | 0–1 | Date, or `Undisclosed`. |
| `System-Card` | 0–1 | URL of the system/model card. |
| `Known-Limitations` | 0–1 | URL or short plain-text summary. |
| `Autonomy-Horizon-50` | 0–1 | Shorthand for the system's 50% long-horizon figure; if present, it MUST also appear as a full Evaluation block with evaluator and conditions. |
| `Safety-Evaluation` | 0+ | One line per external safety evaluation: evaluator, scope, date, report URL. |

## 7. Evaluation blocks

Each block describes **one measured claim**:

| Field | Cards | Description |
|---|---|---|
| `Evaluation` | block start, REQUIRED | Benchmark name **and version/release** (e.g. `SWE-bench Verified (2026-01 release)`, `METR Time Horizon 1.1`). |
| `Evaluator` | REQUIRED | Who ran it. MUST include the word `independent` in parentheses if the evaluator is organisationally independent of the publisher. |
| `Score` | REQUIRED | The result, with units (e.g. `74.2%`, `11.5 hours`, `ECI 158`). |
| `Conditions` | REQUIRED for MEASURED/ATTESTED | Material conditions: agent scaffold/harness, reasoning effort, tool access, attempt limits — whatever a competent replicator would need. A score without conditions is not comparable and validators MUST flag it. |
| `Measured` | REQUIRED | Date the measurement was completed. |
| `Evidence` | REQUIRED | URL of the report, dashboard entry, or results file. |
| `Attestation` | REQUIRED for ATTESTED | `sha256:<hex>` of the evaluator's report, or a reference to the evaluator's countersignature. |
| `Tier` | REQUIRED | `ATTESTED`, `MEASURED`, or `DECLARED`. Validators recompute the tier from the block's contents and MUST downgrade a block whose stated tier its contents do not support (e.g. `ATTESTED` with no `Attestation`). |

## 8. The `Undisclosed` rule

For `Parameters` and `Training-Compute` (and by extension any field a future version makes required*), a publisher MUST either give a value or write `Undisclosed`. Omitting the field makes the file invalid. Rationale: silence is ambiguous (forgot? hiding? not applicable?); an explicit `Undisclosed` is a countable, comparable fact — it is what transparency indexes currently have to excavate by hand.

## 9. Freshness, versioning, and change

* A file is **current** until its `Expires`; after that, validators MUST label every claim in it STALE.
* Publishers SHOULD update the file in the same release process as the system itself; a system that is served but absent from a current file is, for consumers of this spec, UNDECLARED.
* Each published version SHOULD remain fetchable (via `Previous-Version` chains or dated URLs) so diffs are auditable. A monitor's diff of two versions — systems added/removed, scores changed, fields edited — is the authoritative answer to "what changed and when," ending the "quietly updated model" class of rumor.

## 10. Signing

* The file MUST name a detached signature (`Signature` header) covering the exact bytes of the file as served. OpenPGP (as in RFC 9116 practice) or JWS are both acceptable; the signature file's format is self-describing.
* Validators MUST report one of: `signature-verified`, `signature-present-unverified`, `signature-missing`, `signature-invalid`. Only `signature-verified` supports treating the file as authentically the publisher's.
* Canonicalisation note: signatures cover the served bytes; publishers MUST NOT rely on whitespace-insensitive verification.

## 11. JSON mirror

The JSON mirror carries identical content for machine consumers. Field names are lower-snake-case; quantities are numbers; dates are strings as in Section 4.2. A JSON Schema (draft 2020-12) for the mirror is given in Appendix A. On any conflict between the text file and the mirror, the **signed text file wins**.

## 12. Validator behaviour (normative)

A conforming validator, given a file (path or URL), MUST be able to:

1. **Authenticate**: fetch over HTTPS; check `Canonical` against the fetch URL; check the signature state (Section 10).
2. **Check freshness**: parse `Expires`; label the file current or STALE.
3. **Lint**: required header/stanza fields present; required* fields explicitly valued or `Undisclosed`; `Status` in vocabulary; dates parse; every evaluation block complete for its stated tier; tiers recomputed and downgraded where unsupported.
4. **Cross-check**: for each system, look up the registry (Epoch AI models dataset is the reference registry for this draft) — report `IN-REGISTRY`, `NOT-IN-REGISTRY`, or `CONTRADICTED`. For each MEASURED/ATTESTED claim, compare against the evaluator's published data where a machine-readable source exists, and verify the `Evidence` URL resolves.
5. **Rumor sweep**: given a list of names circulating publicly, report each as declared, or as `UNDECLARED — rumor tier` if absent. Validators MUST NOT import rumored systems into the declared set.
6. **Diff**: given a previous version, report added/removed systems and every changed field and score.
7. **Report**: emit a machine-readable report (JSON) containing, per system and per claim, its tier/verdict, all errors and warnings, and the file's SHA-256. Human-readable renderings (text/markdown) SHOULD be offered. Verdict vocabulary: `VALID`, `VALID-WITH-WARNINGS`, `INVALID`, plus per-claim `ATTESTED / MEASURED / DECLARED / CONTRADICTED / STALE / EVIDENCE-UNREACHABLE` and per-system registry verdicts as in step 4.

### 12.3 Comparison tolerances (for CONTRADICTED)

Exact string/value equality is too strict for reconstructed registries. Reference tolerances: release dates differing by ≤31 days are a warning, not a contradiction; parameter counts differing by >2×, and training compute differing by >3× (registries estimate compute), are contradictions. Evaluators' own republication of a score supersedes the file's transcription.

## 13. Conformance levels

**Publisher levels**
* **Level 1 — Declared**: valid file, all required fields, signature named. (An afternoon's work.)
* **Level 2 — Measured**: at least one MEASURED evaluation per generally-available system, JSON mirror published, `Registry-ID`s cross-linked.
* **Level 3 — Attested**: ATTESTED evaluations from ≥1 independent evaluator for frontier systems, `Previous-Version` chain maintained, expiry ≤90 days.

**Validator conformance**: implements all of Section 12 and publishes its test results against the reference test suite (valid, expired, broken, contradicted, and rumor cases).

## 14. Security considerations

* **Dishonest declarations.** The format cannot prevent lying. It converts lies from deniable rumors into signed, timestamped, hashed statements that independent evaluators can contradict on the record — permanently attributable. That is the same bargain that makes security.txt and financial filings useful.
* **Spoofed files.** Files on lookalike domains are not the publisher's. `Canonical` + signature verification (Sections 10, 12.1) is the defence; consumers MUST NOT trust an unsigned or canonical-mismatched file.
* **Stale mirrors and caches.** `Expires` bounds the damage; validators MUST surface staleness rather than silently serving old claims.
* **Benchmark gaming.** Mandatory `Conditions` and versioned benchmarks make selective reporting visible: a publisher that reports only flattering benchmarks will show conspicuously fewer evaluation blocks than its peers — itself a signal.
* **Signature stripping / downgrade.** A mirror that drops the signature reduces every claim to at most DECLARED; validators MUST reflect that.
* **Denial by omission.** A publisher can omit a secret system. The file makes that omission *visible as a state* (UNDECLARED) once the system is rumored, rather than leaving the rumor unanswerable either way.

## 15. Privacy considerations

The file contains only public, organisational information. Personal data SHOULD NOT appear beyond role-based contacts (as in RFC 9116 practice). Nothing in this specification requires disclosing trade secrets: the `Undisclosed` rule exists precisely so a publisher can be complete about the *shape* of its disclosure without revealing protected values.

## 16. Registry considerations (for a future standards home)

* Registration of the well-known URI suffix `ai-systems.txt` (and `ai-systems.json`) in the IANA Well-Known URIs registry.
* A field-name registry (name, cardinality, status, reference) modelled on RFC 9116's registry, so new fields (e.g. energy-use, incident contacts) can be added without breaking parsers — parsers already MUST ignore unknown fields.
* A registry-prefix registry for `Registry-ID` values.

## 17. Adoption playbook

1. **Makers** publish Level 1 files (cost: one static file in the release checklist).
2. **Evaluators** (METR, Epoch, Artificial Analysis, national AISI's) publish their results in linkable, hashable reports so blocks can be ATTESTED, and may countersign.
3. **Registries and monitors** (Epoch, AI Index, capability trackers) ingest files as a Tier-0 source — above reconstruction, below independent measurement for scoring, exactly as Section 2 orders it.
4. **Buyers and journalists** cite tiers, not screenshots: "DECLARED by the maker, not yet MEASURED independently" is a complete, honest sentence that is impossible to write today.

## 18. Relationship to existing work

* `robots.txt` (RFC 9309) — the directional opposite and the adoption template: voluntary, trivial, publisher-served.
* `security.txt` (RFC 9116) — the structural template: well-known location, `Field: value` lines, required `Contact`/`Expires`, signed files, an IANA field registry.
* `ai.txt` proposals (Spawning AI; IETF draft-car-ai-txt-wellknown-00; Witchborn Web AI.0) — content permissions for publishers; complementary, and the reason for this file's distinct name.
* `llms.txt` — a content index for agents; unrelated purpose.
* Model cards / system cards — long-form companions; linked, not replaced.
* A2A agent cards, MCP server cards — runtime interface descriptions; complementary layer.
* Epoch AI, METR, Artificial Analysis, Stanford AI Index — the independent reconstruction layer this file feeds and is checked against; adoption of this spec makes their work faster, not obsolete.

## 19. Worked example

See `examples/example-ai-systems.txt` in the reference implementation: a fictional maker declaring one system with one MEASURED, one ATTESTED, and one DECLARED evaluation — and a rumored successor ("Example-10") that appears nowhere in the file and is therefore, to any validator, UNDECLARED.

## 20. Reference implementation

A prototype validator implementing Section 12 accompanies this draft (`validator.py`, stdlib-only Python, with a test suite covering valid, broken/expired, contradicted, diff, and rumor-sweep cases). At publication time its checks confirmed: no frontier maker yet serves a file at the canonical location (OpenAI: 404; Anthropic and DeepMind: redirects, no file) — the gap this specification exists to close.

## 21. Open questions for reviewers

1. Should ATTESTED require the evaluator's *countersignature*, or is a report hash sufficient for v1?
2. Should `Expires` for frontier developers be a MUST at ≤90 days rather than a recommendation?
3. Is a separate `Incident-Contact`-style field needed, or does `Contact` suffice?
4. Should energy/water use per training run be a required* field in v1, or deferred to the field registry?
5. Who should host the field registry and test suite — an IETF path (as security.txt took), or a community registry first?

---

## Appendix A — JSON Schema for the JSON mirror (abridged)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ai-systems.json",
  "type": "object",
  "required": ["ai_systems_version", "header", "systems"],
  "properties": {
    "ai_systems_version": {"type": "string"},
    "header": {
      "type": "object",
      "required": ["Publisher", "Canonical", "Contact", "Expires", "Signature"],
      "properties": {
        "Publisher": {"type": "string"},
        "Canonical": {"type": "string", "format": "uri"},
        "Contact": {"type": "string"},
        "Expires": {"type": "string", "format": "date-time"},
        "Signature": {"type": "string", "format": "uri"}
      }
    },
    "systems": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["System", "Version", "Status", "Released", "Modalities", "Access",
                     "Parameters", "Training-Compute", "evaluations"],
        "properties": {
          "System": {"type": "string"},
          "Version": {"type": "string"},
          "Status": {"enum": ["research", "preview", "general-availability", "deprecated", "retired"]},
          "Released": {"type": "string", "format": "date"},
          "Parameters": {"type": ["number", "string"], "description": "number, or the string 'Undisclosed'"},
          "Training-Compute": {"type": ["number", "string"], "description": "FLOP, or 'Undisclosed'"},
          "evaluations": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["Benchmark", "Evaluator", "Score", "Measured", "Evidence", "Tier"],
              "properties": {
                "Tier": {"enum": ["ATTESTED", "MEASURED", "DECLARED"]}
              }
            }
          }
        }
      }
    }
  }
}
```

## Appendix B — Document history

* v0.1 (2026-10-31): initial draft — concept, tiers, fields, validator sketch.
* v0.2 (2026-10-31): first public draft — full field tables, ABNF, JSON schema, validator normative behaviour and tolerances, conformance levels, security/privacy/registry sections, adoption playbook, open questions. Reference validator prototype built and tested before publication, per the originator's instruction.
