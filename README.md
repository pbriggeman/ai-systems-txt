# ai-systems.txt — a reverse robots.txt for AI capabilities

**Draft specification v0.2 + prototype validator. Published 2026-10-31 for discussion.**

robots.txt tells machines what they may *take* from a publisher. `ai-systems.txt` is the reverse: a file an AI maker publishes at `/.well-known/ai-systems.txt` declaring **which systems it has released, what their measured capabilities are, who measured them, under what conditions, and where the evidence is** — signed, timestamped, and expiring.

Every capability claim lives in exactly one tier:

- **ATTESTED** — independently measured and countersigned (evidence + report hash)
- **MEASURED** — measured by a named evaluator, with version, conditions, and date
- **DECLARED** — asserted by the maker, not independently measured
- **UNDECLARED** — not in a valid file at all: the *rumor tier*, by definition

## Contents

- [`SPEC.md`](SPEC.md) — the full specification (CC BY 4.0)
- [`validator.py`](validator.py) — prototype validator, stdlib-only Python 3 (MIT)
- [`examples/`](examples/) — a valid example file, a deliberately broken one, a rumor list
- [`tests/`](tests/) — test suite (plain asserts, no pytest needed)

## Run the validator

```bash
# Validate the example against a local Epoch-registry fixture, offline:
python3 validator.py examples/example-ai-systems.txt \
  --no-network --epoch-csv tests/epoch_fixture.csv \
  --rumor "Example-10" --format text

# Validate a maker's live file, with diffing against last week's copy:
python3 validator.py https://example-ai.com/.well-known/ai-systems.txt \
  --previous last-week.txt --rumors-file rumors.txt \
  --format json --out report.json

# Run the tests:
python3 tests/test_validator.py
```

Exit codes: `0` valid · `1` valid with warnings · `2` errors or stale.

The validator authenticates the file (canonical + signature presence), checks expiry, lints every claim, cross-checks systems against the **Epoch AI models registry**, verifies evidence URLs, runs the **rumor sweep**, and diffs versions so "quietly changed" claims become impossible.

## Why

Today, what an AI system is and can do reaches the public as marketing, screenshots, leaks, and rumor — and independent parties reconstruct the truth afterward. This file lets makers state the truth on the record, in a form built to be *checked rather than believed*, and gives journalists, buyers, researchers, and capability monitors a deterministic way to grade what they hear: **fact, or rumor.**

## Status & feedback

v0.2 is a public draft, deliberately published before any formal process. Open questions for reviewers are listed in SPEC.md §21. Corrections and disputes: open an issue, or adapt the draft — the licence invites it.
