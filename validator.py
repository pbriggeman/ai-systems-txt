#!/usr/bin/env python3
"""
ai-systems.txt validator — prototype v0.1

Validates an `ai-systems.txt` file (the "reverse robots.txt": a maker-published,
signed, expiring declaration of its AI systems and their measured capabilities)
and separates fact from rumor:

  * lints the file against the spec (required fields, explicit `Undisclosed`,
    evaluation blocks with version + evaluator + conditions + date),
  * checks freshness (Expires) and provenance (Canonical, Signature presence),
  * cross-checks declared systems against the Epoch AI models registry (CSV),
  * checks evidence URLs are reachable (when online),
  * runs a rumor sweep: names supplied by the user that are absent from the
    file are reported as UNDECLARED — the rumor tier,
  * diffs against a previous version of the file and reports exactly what
    claim changed.

Stdlib only. Usage:
  python3 validator.py <file-or-url> [--rumor "Example-10"] [--previous old.txt]
                         [--epoch-csv path-or-url] [--no-network]
                         [--format text|json|md] [--out report.json]
                         [--emit-json ai-systems.json]

Exit codes: 0 = valid, 1 = valid with warnings, 2 = errors or stale.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from difflib import SequenceMatcher

SPEC_VERSIONS = {"0.1"}
TIERS = {"ATTESTED", "MEASURED", "DECLARED"}
STATUSES = {"research", "preview", "general-availability", "deprecated", "retired"}
HEADER_REQUIRED = ["AISystems-Version", "Publisher", "Canonical", "Contact", "Expires", "Signature"]
SYSTEM_REQUIRED = ["System", "Version", "Status", "Released", "Modalities", "Access"]
MUST_BE_EXPLICIT = ["Parameters", "Training-Compute"]  # required, may be "Undisclosed"
EVAL_REQUIRED = ["Evaluator", "Score", "Measured", "Evidence", "Tier"]
EVAL_FIELDS = {"Evaluator", "Score", "Conditions", "Measured", "Evidence", "Attestation", "Tier"}


# --------------------------------------------------------------------------- IO

def fetch(source, timeout=30):
    """Return (text, fetched_from_url_or_None)."""
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "ai-systems-validator/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), source
    with open(source, "r", encoding="utf-8") as fh:
        return fh.read(), None


def url_reachable(url, timeout=10):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "ai-systems-validator/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):  # some servers refuse HEAD; try a ranged GET
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ai-systems-validator/0.1",
                                                           "Range": "bytes=0-0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return 200 <= resp.status < 400
            except Exception:
                return False
        return False
    except Exception:
        return False


# ------------------------------------------------------------------------ parse

def parse(text):
    """Parse ai-systems.txt into {header: {}, systems: [ {fields, evaluations[]} ]}."""
    header, systems = {}, []
    current = None          # current system stanza (dict)
    current_eval = None     # current evaluation block (dict)

    def flush_eval():
        nonlocal current_eval
        if current is not None and current_eval is not None:
            current["evaluations"].append(current_eval)
        current_eval = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            (current if current is not None else header).setdefault("_malformed", []).append(raw)
            continue
        field, value = line.split(":", 1)
        field, value = field.strip(), value.strip()

        if field == "System":
            flush_eval()
            current = {"evaluations": [], "_fields": {}}
            systems.append(current)
            current["System"] = value
            current["_fields"]["System"] = value
            continue

        if current is None:
            header[field] = value
            continue

        if field == "Evaluation":
            flush_eval()
            current_eval = {"Benchmark": value}
            continue

        if current_eval is not None and field in EVAL_FIELDS:
            current_eval[field] = value
            continue

        flush_eval()
        if field == "Registry-ID":
            current.setdefault("Registry-ID", []).append(value)
        else:
            current[field] = value
        current["_fields"][field] = value

    flush_eval()
    return {"header": header, "systems": systems,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


# --------------------------------------------------------------------- helpers

def norm(name):
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def parse_number(s):
    """Parse '405B', '7.5e24', '1,000,000', '2.3e25 FLOP' -> float or None."""
    if s is None or s.strip().lower() == "undisclosed":
        return None
    m = re.search(r"([\d][\d,\.]*)\s*([eE]([+-]?\d+))?\s*([KMBT])?", s.replace(" ", ""))
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    if m.group(2):
        val *= 10 ** int(m.group(3))
    suffix = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    if m.group(4):
        val *= suffix[m.group(4).upper()]
    return val


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


# -------------------------------------------------------------------- validate

class Report:
    def __init__(self):
        self.errors, self.warnings, self.info = [], [], []
        self.claims = []          # per-evaluation verdicts
        self.systems = []         # per-system registry verdicts
        self.rumors = []          # undeclared names
        self.diff = None

    def verdict(self):
        if self.errors:
            return "INVALID"
        if self.warnings:
            return "VALID-WITH-WARNINGS"
        return "VALID"


def validate(doc, source_url=None, online=True, epoch_rows=None, rumors=()):
    r = Report()
    h = doc["header"]

    # Header lint
    for f in HEADER_REQUIRED:
        if f not in h:
            r.errors.append(f"header: missing required field '{f}'")
    if "_malformed" in h:
        r.errors.append(f"header: {len(h['_malformed'])} malformed line(s) without 'Field:' syntax")
    if h.get("AISystems-Version") and h["AISystems-Version"] not in SPEC_VERSIONS:
        r.warnings.append(f"header: AISystems-Version '{h['AISystems-Version']}' not recognised "
                          f"(known: {', '.join(sorted(SPEC_VERSIONS))})")

    # Freshness
    stale = False
    if h.get("Expires"):
        try:
            exp = datetime.fromisoformat(h["Expires"].replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if exp < now:
                stale = True
                r.errors.append(f"header: file EXPIRED on {h['Expires']} — treat all claims as STALE")
            elif (exp - now).days > 366:
                r.warnings.append("header: Expires is more than a year out (spec recommends <= 1 year, 90 days for frontier labs)")
            else:
                r.info.append(f"header: expires in {(exp - now).days} days ({h['Expires']})")
        except ValueError:
            r.errors.append(f"header: Expires '{h['Expires']}' is not a valid RFC 3339 timestamp")

    # Provenance
    if source_url and h.get("Canonical"):
        if norm(h["Canonical"]) != norm(source_url):
            r.errors.append(f"header: Canonical '{h['Canonical']}' does not match the URL it was fetched from ('{source_url}') — do not trust")
        else:
            r.info.append("header: Canonical matches fetch URL")
    if h.get("Signature"):
        if online and h["Signature"].startswith("http"):
            if url_reachable(h["Signature"]):
                r.info.append("header: signature file reachable (prototype: presence checked, cryptographic verification NOT performed)")
            else:
                r.warnings.append("header: Signature URL is not reachable")
        else:
            r.warnings.append("header: signature present but not verified by this prototype")
    r.info.append(f"file sha256: {doc['sha256']}")

    # Systems lint
    seen = set()
    for s in doc["systems"]:
        name = s.get("System", "<unnamed>")
        if norm(name) in seen:
            r.errors.append(f"system '{name}': duplicate stanza")
        seen.add(norm(name))
        for f in SYSTEM_REQUIRED:
            if f not in s:
                r.errors.append(f"system '{name}': missing required field '{f}'")
        for f in MUST_BE_EXPLICIT:
            if f not in s:
                r.errors.append(f"system '{name}': '{f}' is absent — spec requires an explicit value or 'Undisclosed' (silence is not data)")
        if s.get("Status") and s["Status"] not in STATUSES:
            r.errors.append(f"system '{name}': Status '{s['Status']}' not in {sorted(STATUSES)}")
        if s.get("Released") and not parse_date(s["Released"]):
            r.errors.append(f"system '{name}': Released '{s['Released']}' is not a parseable date")

        # Evaluations
        for ev in s["evaluations"]:
            claim = {"system": name, "benchmark": ev.get("Benchmark", "?"),
                     "tier": ev.get("Tier"), "score": ev.get("Score"), "status": "DECLARED"}
            for f in EVAL_REQUIRED:
                if f not in ev:
                    r.errors.append(f"system '{name}' / '{claim['benchmark']}': evaluation missing '{f}' — a claim without evaluator, conditions, date and evidence is malformed")
            if ev.get("Tier") and ev["Tier"] not in TIERS:
                r.errors.append(f"system '{name}' / '{claim['benchmark']}': Tier '{ev['Tier']}' not in {sorted(TIERS)}")
            if ev.get("Tier") == "ATTESTED" and "Attestation" not in ev:
                r.errors.append(f"system '{name}' / '{claim['benchmark']}': Tier is ATTESTED but no Attestation hash is given")
            if ev.get("Tier") in ("MEASURED", "ATTESTED") and "independent" not in (ev.get("Evaluator") or "").lower():
                r.warnings.append(f"system '{name}' / '{claim['benchmark']}': Tier {ev['Tier']} but Evaluator does not state '(independent)'")
            if "Conditions" not in ev:
                r.warnings.append(f"system '{name}' / '{claim['benchmark']}': no Conditions stated — scores without conditions are not comparable")
            if online and ev.get("Evidence", "").startswith("http"):
                if url_reachable(ev["Evidence"]):
                    claim["status"] = ev.get("Tier", "DECLARED")
                else:
                    claim["status"] = "EVIDENCE-UNREACHABLE"
                    r.warnings.append(f"system '{name}' / '{claim['benchmark']}': Evidence URL not reachable: {ev['Evidence']}")
            else:
                claim["status"] = ev.get("Tier", "DECLARED")
            if stale:
                claim["status"] = "STALE"
            r.claims.append(claim)

        # Registry cross-check (Epoch)
        sysrep = {"system": name, "registry": "NOT-CHECKED"}
        if epoch_rows is not None:
            match = None
            for row in epoch_rows:
                if norm(row.get("Model")) == norm(name):
                    match = row
                    break
            if match is None:  # prefix / close match (e.g. version suffixes)
                cands = [row for row in epoch_rows
                         if norm(row.get("Model")).startswith(norm(name)) or norm(name).startswith(norm(row.get("Model")))]
                if len(cands) == 1:
                    match = cands[0]
            if match is None:
                sysrep["registry"] = "NOT-IN-REGISTRY"
                r.warnings.append(f"system '{name}': not found in the Epoch AI registry — unverified as a released system")
            else:
                sysrep["registry"] = "IN-REGISTRY"
                sysrep["epoch_model"] = match.get("Model")
                ed, rd = parse_date(match.get("Publication date")), parse_date(s.get("Released"))
                if ed and rd and abs((ed - rd).days) > 31:
                    r.warnings.append(f"system '{name}': Released {s.get('Released')} differs from Epoch publication date {match.get('Publication date')} by >31 days")
                ep, dp = parse_number(match.get("Parameters")), parse_number(s.get("Parameters"))
                if ep and dp and (dp / ep > 2 or ep / dp > 2):
                    sysrep["registry"] = "CONTRADICTED"
                    r.errors.append(f"system '{name}': declared Parameters '{s.get('Parameters')}' contradict Epoch's value '{match.get('Parameters')}' by >2x")
                ec, dc = parse_number(match.get("Training compute (FLOP)")), parse_number(s.get("Training-Compute"))
                if ec and dc and (dc / ec > 3 or ec / dc > 3):
                    sysrep["registry"] = "CONTRADICTED"
                    r.errors.append(f"system '{name}': declared Training-Compute '{s.get('Training-Compute')}' contradicts Epoch's estimate '{match.get('Training compute (FLOP)')}' by >3x")
        r.systems.append(sysrep)

    # Rumor sweep
    declared = {norm(s.get("System")) for s in doc["systems"]}
    for rumor in rumors:
        if norm(rumor) not in declared:
            r.rumors.append({"name": rumor, "status": "UNDECLARED — rumor tier"})
        else:
            r.info.append(f"rumor check: '{rumor}' IS declared in the file")
    return r


# ------------------------------------------------------------------------ diff

def diff_docs(old, new):
    out = {"added_systems": [], "removed_systems": [], "changed": []}
    oldmap = {norm(s.get("System")): s for s in old["systems"]}
    newmap = {norm(s.get("System")): s for s in new["systems"]}
    for k in newmap:
        if k not in oldmap:
            out["added_systems"].append(newmap[k].get("System"))
    for k in oldmap:
        if k not in newmap:
            out["removed_systems"].append(oldmap[k].get("System"))
    for k in oldmap.keys() & newmap.keys():
        o, n = oldmap[k], newmap[k]
        for f in sorted(set(o["_fields"]) | set(n["_fields"])):
            if o["_fields"].get(f) != n["_fields"].get(f):
                out["changed"].append({"system": n.get("System"), "field": f,
                                       "old": o["_fields"].get(f), "new": n["_fields"].get(f)})
        oe = {e["Benchmark"]: e for e in o["evaluations"]}
        ne = {e["Benchmark"]: e for e in n["evaluations"]}
        for b in ne:
            if b not in oe:
                out["changed"].append({"system": n.get("System"), "field": f"Evaluation added: {b}",
                                       "old": None, "new": ne[b].get("Score")})
            elif oe[b].get("Score") != ne[b].get("Score"):
                out["changed"].append({"system": n.get("System"), "field": f"Evaluation score: {b}",
                                       "old": oe[b].get("Score"), "new": ne[b].get("Score")})
    return out


# ---------------------------------------------------------------------- output

def to_dict(doc, report, source):
    return {
        "source": source,
        "file_sha256": doc["sha256"],
        "publisher": doc["header"].get("Publisher"),
        "expires": doc["header"].get("Expires"),
        "verdict": report.verdict(),
        "errors": report.errors,
        "warnings": report.warnings,
        "info": report.info,
        "systems": report.systems,
        "claims": report.claims,
        "rumors_undeclared": report.rumors,
        "diff": report.diff,
    }


def render_text(d):
    lines = []
    lines.append(f"ai-systems.txt validation — {d['source']}")
    lines.append(f"Publisher: {d['publisher']}   Expires: {d['expires']}   Verdict: {d['verdict']}")
    lines.append(f"File sha256: {d['file_sha256']}")
    for s in d["systems"]:
        lines.append(f"\nSYSTEM {s['system']}: registry = {s['registry']}"
                     + (f" (Epoch: {s['epoch_model']})" if s.get("epoch_model") else ""))
    if d["claims"]:
        lines.append("\nCLAIMS (fact tiers):")
        for c in d["claims"]:
            lines.append(f"  [{c['status']}] {c['system']} — {c['benchmark']}: {c['score']} (file tier: {c['tier']})")
    if d["rumors_undeclared"]:
        lines.append("\nRUMOR SWEEP — not in the file, therefore UNDECLARED:")
        for rum in d["rumors_undeclared"]:
            lines.append(f"  - {rum['name']}")
    if d["diff"]:
        lines.append("\nDIFF vs previous version:")
        for x in d["diff"]["added_systems"]:
            lines.append(f"  + system added: {x}")
        for x in d["diff"]["removed_systems"]:
            lines.append(f"  - system removed: {x}")
        for ch in d["diff"]["changed"]:
            lines.append(f"  ~ {ch['system']} / {ch['field']}: {ch['old']!r} -> {ch['new']!r}")
    if d["warnings"]:
        lines.append("\nWARNINGS:")
        lines += [f"  ! {w}" for w in d["warnings"]]
    if d["errors"]:
        lines.append("\nERRORS:")
        lines += [f"  X {e}" for e in d["errors"]]
    if d["info"]:
        lines.append("\nINFO:")
        lines += [f"  i {i}" for i in d["info"]]
    return "\n".join(lines) + "\n"


def render_md(d):
    return "# ai-systems.txt validation report\n\n```text\n" + render_text(d) + "```\n"


def emit_json_mirror(doc):
    out = {"ai_systems_version": doc["header"].get("AISystems-Version"),
           "header": doc["header"], "systems": []}
    for s in doc["systems"]:
        entry = {k: v for k, v in s.items() if k != "_fields"}
        out["systems"].append(entry)
    return out


# ------------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate an ai-systems.txt file — separate fact from rumor.")
    ap.add_argument("source", help="Path or URL of the ai-systems.txt file")
    ap.add_argument("--rumor", action="append", default=[], help="A rumored system name to check (repeatable)")
    ap.add_argument("--rumors-file", help="File with one rumored system name per line")
    ap.add_argument("--previous", help="Path or URL of a previous version, to diff against")
    ap.add_argument("--epoch-csv", help="Path or URL of Epoch AI all_ai_models.csv (defaults to the live Epoch URL when online)")
    ap.add_argument("--no-network", action="store_true", help="Offline mode: no URL, evidence, or registry fetches")
    ap.add_argument("--format", choices=["text", "json", "md"], default="text")
    ap.add_argument("--out", help="Write the report to this file instead of stdout")
    ap.add_argument("--emit-json", help="Also write a JSON mirror of the parsed file to this path")
    args = ap.parse_args(argv)

    online = not args.no_network
    try:
        text, fetched_from = fetch(args.source) if (online or args.source.startswith("http") is False) else (None, None)
    except Exception as e:
        print(f"error: could not read source: {e}", file=sys.stderr)
        return 2
    if text is None:
        print("error: --no-network cannot fetch a URL source", file=sys.stderr)
        return 2

    doc = parse(text)

    rumors = list(args.rumor)
    if args.rumors_file:
        with open(args.rumors_file, encoding="utf-8") as fh:
            rumors += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    epoch_rows = None
    if online or args.epoch_csv:
        src = args.epoch_csv or "https://epoch.ai/data/all_ai_models.csv"
        try:
            etext, _ = fetch(src)
            epoch_rows = list(csv.DictReader(io.StringIO(etext)))
        except Exception as e:
            print(f"warning: Epoch registry unavailable ({e}); registry cross-check skipped", file=sys.stderr)

    report = validate(doc, source_url=fetched_from, online=online, epoch_rows=epoch_rows, rumors=rumors)

    if args.previous:
        ptext, _ = fetch(args.previous)
        report.diff = diff_docs(parse(ptext), doc)

    d = to_dict(doc, report, args.source)
    rendered = {"text": render_text, "md": render_md,
                "json": lambda x: json.dumps(x, indent=2) + "\n"}[args.format](d)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(rendered)
    else:
        sys.stdout.write(rendered)

    if args.emit_json:
        with open(args.emit_json, "w", encoding="utf-8") as fh:
            json.dump(emit_json_mirror(doc), fh, indent=2)

    if report.errors:
        return 2
    if report.warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
