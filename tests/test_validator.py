#!/usr/bin/env python3
"""Plain-assert tests for the ai-systems.txt validator prototype. No pytest needed:
   python3 tests/test_validator.py"""
import csv, io, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import validator as v

ROOT = os.path.join(os.path.dirname(__file__), "..")

def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as fh:
        return fh.read()

def epoch_rows():
    with open(os.path.join(ROOT, "tests", "epoch_fixture.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

# 1. Example file parses: 1 system, 3 evaluations
doc = v.parse(load("examples/example-ai-systems.txt"))
assert doc["header"]["Publisher"] == "Example AI, Inc."
assert len(doc["systems"]) == 1
s = doc["systems"][0]
assert s["System"] == "Example-9" and len(s["evaluations"]) == 3
assert s["Registry-ID"] == ["epoch:example-9", "openrouter:example-ai/example-9", "api-model:example-9-20260930"]
print("ok 1: parse")

# 2. Example file validates offline against fixture: IN-REGISTRY, ATTESTED claim kept.
#    (Parameters/Training-Compute are 'Undisclosed' in the example, so no contradiction.)
r = v.validate(doc, online=False, epoch_rows=epoch_rows(), rumors=["Example-10", "Example-9"])
assert not r.errors, r.errors
assert r.systems[0]["registry"] == "IN-REGISTRY", r.systems
tiers = {c["benchmark"]: c["status"] for c in r.claims}
assert tiers["METR Time Horizon 1.1 (50% horizon)"] == "ATTESTED"
assert tiers["SWE-bench Verified (2026-01 release)"] == "DECLARED"
assert [x["name"] for x in r.rumors] == ["Example-10"]
print("ok 2: validate example + rumor sweep")

# 3. Broken file: expired, missing Contact/Signature, bad status/date/tier, missing eval fields
doc2 = v.parse(load("examples/broken-ai-systems.txt"))
r2 = v.validate(doc2, online=False, epoch_rows=epoch_rows())
assert r2.verdict() == "INVALID"
joined = "\n".join(r2.errors)
for needle in ["EXPIRED", "Contact", "Signature", "Parameters", "Training-Compute",
               "Status", "Released", "Evaluator", "SUPER-VERIFIED"]:
    assert needle in joined, f"missing expected error about {needle}:\n{joined}"
# expired file => all claims STALE
assert all(c["status"] == "STALE" for c in r2.claims)
print("ok 3: broken file rejected, claims stale")

# 4. Contradiction: declared parameters >2x off the registry value
text = load("examples/example-ai-systems.txt").replace("Parameters: Undisclosed",
                                                       "Parameters: 900B")
doc3 = v.parse(text)
r3 = v.validate(doc3, online=False, epoch_rows=epoch_rows())
assert r3.systems[0]["registry"] == "CONTRADICTED", r3.systems
assert any("contradict" in e for e in r3.errors)
print("ok 4: registry contradiction caught")

# 5. Diff: version bump + score change are reported exactly
old = v.parse(load("examples/example-ai-systems.txt"))
new_text = load("examples/example-ai-systems.txt").replace("Version: 9.2 (build 2026-09-28)",
                                                           "Version: 9.3 (build 2026-10-30)").replace(
                                                           "Score: 74.2%", "Score: 76.0%")
d = v.diff_docs(old, v.parse(new_text))
fields = {(c["field"]) for c in d["changed"]}
assert "Version" in fields and any("SWE-bench" in f for f in fields), d
print("ok 5: diff")

# 6. Number parsing
assert v.parse_number("405B") == 4.05e11
assert v.parse_number("2.0e25") == 2.0e25
assert v.parse_number("Undisclosed") is None
print("ok 6: number parsing")

print("\nALL TESTS PASSED")
