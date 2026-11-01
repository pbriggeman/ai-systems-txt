# IETF / IANA Submission Checklist — draft-briggeman-ai-systems-00
Prepared 2026-10-31. Files in this folder:
- `draft-briggeman-ai-systems-00.xml` — the Internet-Draft source (RFC XML v3, submissionType=independent, ipr=trust200902)
- `draft-briggeman-ai-systems-00.txt` — rendered text (xml2rfc 3.35.0, zero warnings; expires 10 May 2027)
- `iana-registration-request.txt` — ready-to-send provisional registration email for ai-systems.txt + ai-systems.json

## Steps only Peter can do (identity-bound)
1. **Create a Datatracker account** at https://datatracker.ietf.org (free; use pbriggeman@gmail.com so it matches the draft's author block).
2. **Submit the draft**: Datatracker → Submit an Internet-Draft → upload the .xml (it renders and checks automatically). Expected checks: author email confirmation email — click it, or the submission stalls in manual review.
3. **Announce** (short posts, drafts on request):
   - `wellknown-uri-review@ietf.org` — attach the IANA request below; one message covers both the registry request and expert eyeballs.
   - `art@ietf.org` (Applications and Real-Time general discussion) and/or request a DISPATCH slot at the next IETF meeting cycle if pursuing WG adoption later.
4. **Send the IANA email** (`iana-registration-request.txt`) from pbriggeman@gmail.com to wellknown-uri-review@ietf.org.
5. **Keep the draft alive**: an unrevised I-D expires after 185 days. Cadence: revise at least twice a year (bump to -01 with reviewer feedback incorporated).

## After posting (Jevex can drive)
- Track reviewer feedback (Datatracker + list archives); fold into -01.
- When the text stabilises: request Independent Submissions Editor review at rfc-editor.org (submissionType is already set to "independent" in the XML; category Informational).
- IANA provisional → permanent follows either a Standards Track outcome or demonstrated broad implementation + stable spec; revisit after first maker adoptions.

## Known review-bait (expected comments, prepared answers in SPEC §21)
- ATTESTED: countersignature vs report hash (draft currently allows both).
- Expires ≤90 days: SHOULD vs MUST for frontier developers.
- Field registry hosting: IETF vs community-first.
- Licence note: the RFC text will sit under the IETF Trust licence (BCP 78); the CC BY 4.0 community edition in this repo continues in parallel.
