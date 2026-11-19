# 0009 — Evidence goes to Cloud Storage through the API, not a mounted bucket

**Date:** 2026-11-19 · **Status:** Accepted · **Amends:** [0008](0008-cloud-run-class-demo.md)

## Context

ADR 0008 put production evidence in a private Cloud Storage bucket **mounted at `/data/evidence`**
with gcsfuse, and noted this needed "no code change to F1". That was true, and it got the demo
running, but it makes the write-once guarantee (FR-02, WBS 4.2.2) weaker than it looks:

- F1 relies on `open(path, "xb")` to refuse a write when the key already exists. Over gcsfuse that
  is a client-side check against a cache, not an atomic condition at the bucket.
- `chmod 0444` has no meaning on an object store. The read-only bit that development relies on
  silently does nothing in production.
- A rejected upload (empty or over the size limit) was deleted after it had already been partly
  written. Once the bucket's retention policy is locked that delete **fails**, so the rejected
  bytes would stay in the bucket forever with no row pointing at them.
- The bucket had no retention policy at all, so nothing enforced the seven-year period the team
  agreed in F5.

## Decision

- **F1 talks to the bucket through the Cloud Storage API**, behind a small backend interface
  (`backend/app/features/registration/storage.py`). `EVIDENCE_BACKEND=local` keeps the Docker
  volume for development and the tests; `EVIDENCE_BACKEND=gcs` with `EVIDENCE_BUCKET` is what
  Cloud Run runs. The gcsfuse mount is removed.
- **The interface has `seal`, `open` and `exists` — no update and no delete.** Write-once is a
  property of the interface rather than a rule each caller has to remember, so a future feature
  cannot reach for a delete that is not there.
- **An upload is weighed before any backend sees it.** The bytes are hashed and measured into a
  spooled temporary file; only an upload that passes the size checks is sealed. A rejected upload
  therefore leaves nothing to clean up, which is the only approach that works on a locked bucket.
- **The bucket write uses `if_generation_match=0`**, the API's version of `open("xb")`: the write
  fails if an object already exists at that key, so a retried request can never overwrite sealed
  evidence.
- **The bucket has a seven-year retention period** (`infra/gcp/bootstrap.sh`). Setting it is
  automatic; **locking** it is a separate, deliberate step (`LOCK_RETENTION=true`) because locking
  cannot be undone and the bucket cannot be deleted while objects are retained — not something to
  run by accident against a class project.

## Consequences

- Production evidence can no longer be deleted or overwritten by anyone, including a project owner
  with console access, until the retention period passes. That is the point, and it is also what
  makes change request #45 (removing personal data from sealed evidence) a design problem rather
  than a delete call — see [0010](0010-crypto-erasure-for-sealed-evidence.md).
- The backend now depends on `google-cloud-storage`. It is imported only when the bucket backend is
  actually selected, so development and the test suite never load it.
- Downloads stream through the application for both backends instead of being served from a path.
  One code path, and the bucket stays private — no signed URLs to leak.
- Someone has to run `LOCK_RETENTION=true` once against the real bucket. Until then the retention
  period is set but removable, and the write-once guarantee in production rests on the code alone.
