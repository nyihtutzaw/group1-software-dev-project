# Pilot data — maker-checker transcription

How the 1–2 real pilot projects get into production for the Week 11 board demo and the Week 14
buyer review (charter §5.3 "manual maker-checker data transcription workflow for pilot projects",
WBS 11.2.3, FR-10).

The charter calls this workflow **manual**: no extra software. The app already enforces the
checker steps: an independent verifier works through the checklist, and registry staff approve.
Nobody can approve their own submission. This page sets the rules people follow around it.

## Roles — four different people

| Step | Who | Account |
|---|---|---|
| Maker — types the paper records into CRVR | Transcriber (business analyst) | A `developer` account **in the transcriber's own name**, organisation = the pilot developer. Never a shared account, so the ledger names who typed each entry |
| Checker 1 — compares every entry with the source | Independent verifier | `verifier` account, assigned to the project by staff |
| Checker 2 — approves the verified project | Registry staff member | `registry_staff` account |
| Issues credits after approval | A registry staff member other than the maker | `registry_staff` account |

One person must not hold two of these roles for the same project. The app blocks the approver
from being the maker or the verifier. Keeping the transcriber out of staff and verifier roles in
production is up to whoever runs the accounts: an admin creates them at `/admin/users`.

## Steps

1. **Collect the source pack** from the pilot developer: land title, survey, GPS/shapefile
   boundary, geo-tagged photos, additionality reasoning and proof, baseline. Keep the originals;
   they are what the checker compares against.
2. **Maker enters the project** at `/projects/new`, copying field values exactly as written in the
   source documents, and uploads each source file as evidence. Files are sealed on upload; a
   wrong file cannot be replaced, only followed by the correct one, and both stay in the record.
3. **Maker uploads the boundary** file at `/boundary` (do not redraw it by hand) and submits once
   the overlap check passes.
4. **Staff assign the verifier** at `/verify`.
5. **Checker 1 compares field by field** against the source pack: project details, crediting
   period, area against the computed boundary area, baseline, additionality, and each evidence
   file's SHA-256 against the original. Any mismatch → *Request changes* with the field named; the
   maker corrects and resubmits. Otherwise sign off with a risk rating.
6. **Checker 2 approves or rejects** with a rationale. Then a staff member who is not the maker
   issues the credits.
7. **Spot-check the ledger** (`/ledger`, registry staff): every step above appears with its actor,
   and the page reports the hash chain intact.

## Rules

- Real pilot data goes **only into production**, never into the repository, local databases,
  test fixtures or screenshots in pull requests (AGENTS.md rule 7). Local work uses synthetic data.
- Do this after E2E testing and the production deployment (WBS order: 11.3.1 then 11.2.3).
- Personal data in sealed evidence cannot be removed afterwards (see #45), so redact anything the
  sponsor does not need before upload.
